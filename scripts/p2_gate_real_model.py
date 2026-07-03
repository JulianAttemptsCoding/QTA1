"""GATE G2 real-model smoke and contamination probes.

Runs inside a Vertex GPU worker. It downloads one cached model and G1 snapshot
inputs from GCS, renders point-in-time prompts, measures valid JSON on a
20-agent x 10-day smoke slice, runs simple post-cutoff recall probes, and writes
one JSON result to GCS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from google.cloud import storage

from agorasim.agents import PersonaBank
from agorasim.agents.prompt_builder import load_template, render
from agorasim.market import call_auction, flow_imbalance
from agorasim.schemas import AgentDecision, parse_decision


DECISION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["buy", "sell", "hold"]},
        "order_type": {"type": "string", "enum": ["market", "limit"]},
        "qty": {"type": "integer", "minimum": 0, "maximum": 1_000_000},
        "limit_price": {"type": "number", "minimum": 0.01},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "horizon_days": {"type": "integer", "enum": list(range(1, 31))},
        "rationale": {"type": "string", "maxLength": 240},
    },
    "required": ["action", "order_type", "qty", "limit_price", "confidence", "horizon_days", "rationale"],
    "additionalProperties": False,
}

OOS_TICKERS = ["NVNI", "TLRY", "EDIT", "CHPT", "BLNK", "FRSX", "TPET", "OGI", "CCO", "ICCM"]
PROBE_QUESTIONS = [
    "What was this stock's closing price on 2026-06-30?",
    "Name one company-specific news event for this stock after 2025-01-02.",
    "What was this stock's highest daily close during calendar year 2025?",
]


def parse_gs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"Expected gs:// URI, got {uri}")
    bucket, _, prefix = uri[5:].partition("/")
    return bucket, prefix.strip("/")


def safe_model_id(model_id: str) -> str:
    return model_id.replace("/", "__")


def storage_client() -> storage.Client:
    return storage.Client()


def download_json(gcs_uri: str) -> dict[str, Any]:
    bucket_name, prefix = parse_gs_uri(gcs_uri)
    blob = storage_client().bucket(bucket_name).blob(prefix)
    return json.loads(blob.download_as_text())


def upload_json(payload: dict[str, Any], gcs_uri: str) -> None:
    bucket_name, prefix = parse_gs_uri(gcs_uri)
    storage_client().bucket(bucket_name).blob(prefix).upload_from_string(
        json.dumps(payload, indent=2, sort_keys=True),
        content_type="application/json",
    )


def relative_blob_path(blob_name: str, prefix: str) -> str:
    normalized = prefix.strip("/")
    if normalized:
        normalized = f"{normalized}/"
        if not blob_name.startswith(normalized):
            raise ValueError(f"Blob {blob_name!r} is outside prefix {prefix!r}")
        rel = blob_name[len(normalized):]
    else:
        rel = blob_name
    return rel.lstrip("/")


def download_prefix(gcs_uri: str, local_dir: Path) -> int:
    bucket_name, prefix = parse_gs_uri(gcs_uri.rstrip("/") + "/")
    list_prefix = f"{prefix.rstrip('/')}/" if prefix else ""
    client = storage_client()
    local_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    for blob in client.list_blobs(bucket_name, prefix=list_prefix):
        if blob.name.endswith("/"):
            continue
        rel = relative_blob_path(blob.name, list_prefix)
        dest = local_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(dest)
        downloaded += 1
    return downloaded


def manifest_model_uri(gcs_model_root: str, model_id: str) -> str:
    root = gcs_model_root.rstrip("/")
    manifest = download_json(f"{root}/_cache_manifest.json")
    entry = manifest.get(model_id) or {}
    if entry.get("status") == "OK" and entry.get("gcs"):
        return str(entry["gcs"])
    return f"{root}/{safe_model_id(model_id)}"


def read_gcs_text(gcs_uri: str) -> str:
    bucket_name, prefix = parse_gs_uri(gcs_uri)
    return storage_client().bucket(bucket_name).blob(prefix).download_as_text()


def read_jsonl_gcs(gcs_uri: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in read_gcs_text(gcs_uri).splitlines() if line.strip()]


def snapshot_uri(manifest: dict[str, Any], kind: str, ticker: str, name: str) -> str:
    suffix = f"/{kind}/{ticker}/{name}"
    for row in manifest["files"]:
        if row["path"].replace("\\", "/").endswith(suffix):
            return row["gcs_uri"]
    raise KeyError(f"Snapshot file not found for {kind}/{ticker}/{name}")


def parse_date(value: str) -> str:
    return value[:10]


def bar_line(row: dict[str, Any]) -> str:
    return f"{row['t'][:10]}, {float(row['o']):.2f}, {float(row['h']):.2f}, {float(row['l']):.2f}, {float(row['c']):.2f}, {int(row.get('v', 0))}"


def prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_smoke_prompts(manifest: dict[str, Any], ticker: str, n_agents: int, n_days: int) -> tuple[list[dict[str, Any]], list[str]]:
    bars_all = read_jsonl_gcs(snapshot_uri(manifest, "calib", ticker, "bars_1d.jsonl"))
    news_all = read_jsonl_gcs(snapshot_uri(manifest, "calib", ticker, "news.jsonl"))
    days = sorted({parse_date(row["t"]) for row in bars_all})[:n_days]
    personas = PersonaBank(n_agents, seed=20260703).personas
    sys_t = load_template("agent_system.j2")
    user_t = load_template("decision_user.j2")
    requests: list[dict[str, Any]] = []
    prompts: list[str] = []
    for day_idx, asof in enumerate(days):
        bars = [row for row in bars_all if parse_date(row["t"]) <= asof][-30:]
        news = [
            row for row in news_all
            if (row.get("created_at") or row.get("updated_at"))
            and parse_date(str(row.get("created_at") or row.get("updated_at"))) <= asof
        ][-5:]
        for agent_idx, persona in enumerate(personas):
            prompt = render(sys_t, persona=persona.render()) + "\n\n" + render(
                user_t,
                asof_date=asof,
                name_or_alias=f"{ticker} Holdings",
                bars_block="\n".join(bar_line(row) for row in bars),
                news_block="\n".join(
                    f"{row.get('created_at') or row.get('updated_at')}: {str(row.get('headline') or row.get('summary') or '')[:180]}"
                    for row in news
                ),
                shares=str(persona.shares),
                avg_cost=f"{bars[-1]['c']:.2f}" if bars else "1.00",
                cash=f"{persona.cash:.2f}",
            )
            requests.append({
                "request_id": f"{ticker}-{asof}-a{agent_idx:03d}",
                "day": asof,
                "agent_idx": agent_idx,
                "last_price": float(bars[-1]["c"]) if bars else 1.0,
                "prompt_sha256": prompt_hash(prompt),
            })
            prompts.append(prompt)
    return requests, prompts


def build_probe_prompts() -> tuple[list[dict[str, str]], list[str]]:
    template = load_template("contamination_probe.j2")
    rows: list[dict[str, str]] = []
    prompts: list[str] = []
    for ticker in OOS_TICKERS:
        for idx, question in enumerate(PROBE_QUESTIONS):
            prompt = render(template, name_or_alias=f"{ticker} Holdings", probe_question=question)
            rows.append({"ticker": ticker, "probe_idx": str(idx), "prompt_sha256": prompt_hash(prompt)})
            prompts.append(prompt)
    return rows, prompts


def summarize_smoke(requests: list[dict[str, Any]], raw: list[str]) -> dict[str, Any]:
    parsed: list[AgentDecision | None] = [parse_decision(text) for text in raw]
    valid = [decision for decision in parsed if decision is not None]
    by_day: dict[str, list[AgentDecision]] = {}
    last_price_by_day: dict[str, float] = {}
    for req, decision in zip(requests, parsed):
        last_price_by_day[req["day"]] = req["last_price"]
        if decision is not None:
            by_day.setdefault(req["day"], []).append(decision)
    path = []
    price = None
    for day in sorted(last_price_by_day):
        price = last_price_by_day[day] if price is None else price
        decisions = by_day.get(day, [])
        auction = call_auction(decisions, price)
        price = auction.price
        path.append({
            "day": day,
            "n_valid": len(decisions),
            "flow_imbalance": flow_imbalance(decisions),
            "auction_price": auction.price,
            "auction_volume": auction.volume,
        })
    return {
        "n_prompts": len(requests),
        "valid_json_rate": len(valid) / len(requests) if requests else 0.0,
        "invalid_examples": [text[:300] for text, decision in zip(raw, parsed) if decision is None][:3],
        "path": path,
    }


def summarize_probes(rows: list[dict[str, str]], raw: list[str]) -> dict[str, Any]:
    ticker_counts: dict[str, dict[str, int]] = {}
    for row, text in zip(rows, raw):
        answer = text.strip().strip('"').strip("'").upper().strip(" .!?:;")
        if answer.startswith("ANSWER:"):
            answer = answer.split(":", 1)[1].strip(" .!?:;")
        non_unknown = bool(answer) and not answer.startswith("UNKNOWN")
        counts = ticker_counts.setdefault(row["ticker"], {"n": 0, "non_unknown": 0})
        counts["n"] += 1
        counts["non_unknown"] += int(non_unknown)
    per_ticker = []
    for ticker, counts in sorted(ticker_counts.items()):
        rate = counts["non_unknown"] / counts["n"] if counts["n"] else 0.0
        per_ticker.append({"ticker": ticker, "n_probes": counts["n"], "non_unknown_rate": rate})
    max_rate = max((row["non_unknown_rate"] for row in per_ticker), default=0.0)
    return {
        "n_probes": len(rows),
        "max_non_unknown_rate": max_rate,
        "per_ticker": per_ticker,
        "examples": [text.strip()[:120] for text in raw[:5]],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--gcs-model-root", required=True)
    parser.add_argument("--gcs-snapshot-manifest", required=True)
    parser.add_argument("--gcs-output-uri", required=True)
    parser.add_argument("--ticker", default="IIPR")
    parser.add_argument("--n-agents", type=int, default=20)
    parser.add_argument("--n-days", type=int, default=10)
    parser.add_argument("--max-new-tokens", type=int, default=160)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    parser.add_argument("--enforce-eager", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("VLLM_TARGET_DEVICE", "cuda")
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import GuidedDecodingParams

    model_gcs_uri = manifest_model_uri(args.gcs_model_root, args.model_id)
    local_model = Path("/tmp/agorasim-models") / safe_model_id(args.model_id)
    downloaded = download_prefix(model_gcs_uri, local_model)
    if not (local_model / "config.json").exists():
        raise FileNotFoundError(f"Downloaded {downloaded} files from {model_gcs_uri}, but config.json is missing")

    manifest = download_json(args.gcs_snapshot_manifest)
    smoke_rows, smoke_prompts = build_smoke_prompts(manifest, args.ticker, args.n_agents, args.n_days)
    probe_rows, probe_prompts = build_probe_prompts()

    llm = LLM(
        model=str(local_model),
        dtype="float16",
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_model_len=4096,
        enforce_eager=args.enforce_eager,
    )
    guided = GuidedDecodingParams.from_optional(json=DECISION_JSON_SCHEMA, backend="lm-format-enforcer")
    decision_params = SamplingParams(temperature=0.0, max_tokens=args.max_new_tokens, guided_decoding=guided)
    probe_params = SamplingParams(temperature=0.0, max_tokens=64)

    started = time.perf_counter()
    smoke_outputs = llm.generate(smoke_prompts, decision_params)
    probe_outputs = llm.generate(probe_prompts, probe_params)
    elapsed = time.perf_counter() - started

    smoke_raw = [out.outputs[0].text for out in smoke_outputs]
    probe_raw = [out.outputs[0].text for out in probe_outputs]
    smoke = summarize_smoke(smoke_rows, smoke_raw)
    probes = summarize_probes(probe_rows, probe_raw)
    payload = {
        "model_id": args.model_id,
        "ticker": args.ticker,
        "n_agents": args.n_agents,
        "n_days": args.n_days,
        "elapsed_seconds": elapsed,
        "model_gcs_uri": model_gcs_uri,
        "smoke": smoke,
        "contamination": probes,
        "passes_valid_json": smoke["valid_json_rate"] >= 0.99,
        "passes_contamination": probes["max_non_unknown_rate"] <= 0.10,
    }
    upload_json(payload, args.gcs_output_uri)
    print(json.dumps(payload, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
