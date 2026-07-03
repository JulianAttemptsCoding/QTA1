"""P3 calibration worker.

Runs inside Vertex only. Given one CALIB ticker and one arm (named or alias), it
downloads G1 snapshots and cached model weights from GCS, renders production
agent prompts, runs guided JSON inference, and writes raw outputs plus daily
simulation artifacts back to GCS.
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import math
import os
import re
import time
from pathlib import Path
import sys
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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


def parse_gs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"Expected gs:// URI, got {uri}")
    bucket, _, prefix = uri[5:].partition("/")
    return bucket, prefix.strip("/")


def storage_client() -> storage.Client:
    return storage.Client()


def download_json(gcs_uri: str) -> dict[str, Any]:
    bucket_name, prefix = parse_gs_uri(gcs_uri)
    return json.loads(storage_client().bucket(bucket_name).blob(prefix).download_as_text())


def read_gcs_text(gcs_uri: str) -> str:
    bucket_name, prefix = parse_gs_uri(gcs_uri)
    return storage_client().bucket(bucket_name).blob(prefix).download_as_text()


def read_gcs_text_if_exists(gcs_uri: str) -> str:
    bucket_name, prefix = parse_gs_uri(gcs_uri)
    blob = storage_client().bucket(bucket_name).blob(prefix)
    return blob.download_as_text() if blob.exists() else ""


def upload_text(gcs_uri: str, text: str, content_type: str = "text/plain") -> None:
    bucket_name, prefix = parse_gs_uri(gcs_uri)
    storage_client().bucket(bucket_name).blob(prefix).upload_from_string(text, content_type=content_type)


def upload_json(gcs_uri: str, payload: dict[str, Any]) -> None:
    upload_text(gcs_uri, json.dumps(payload, indent=2, sort_keys=True), "application/json")


def iter_jsonl_text(text: str) -> Iterable[dict[str, Any]]:
    for line in text.splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def read_jsonl_gcs(gcs_uri: str) -> list[dict[str, Any]]:
    return list(iter_jsonl_text(read_gcs_text(gcs_uri)))


def safe_model_id(model_id: str) -> str:
    return model_id.replace("/", "__")


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


def snapshot_uri(manifest: dict[str, Any], kind: str, ticker: str, name: str) -> str:
    suffix = f"/{kind}/{ticker}/{name}"
    for row in manifest["files"]:
        if row["path"].replace("\\", "/").endswith(suffix):
            return row["gcs_uri"]
    raise KeyError(f"Snapshot file not found for {kind}/{ticker}/{name}")


def date_key(value: str) -> str:
    return value[:10]


def bar_line(row: dict[str, Any]) -> str:
    return f"{row['t'][:10]}, {float(row['o']):.2f}, {float(row['h']):.2f}, {float(row['l']):.2f}, {float(row['c']):.2f}, {int(row.get('v', 0))}"


def prompt_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def alias_symbol(ticker: str, run_salt: str) -> str:
    return "X" + hashlib.sha256(f"{ticker}:{run_salt}".encode("utf-8")).hexdigest()[:3].upper()


def scrub_alias_text(text: str, ticker: str, alias: str, alias_name: str) -> str:
    out = text
    replacements = [
        (rf"\b{re.escape(ticker)}\b", alias),
        (rf"\b{re.escape(ticker)}\s+Holdings\b", alias_name),
        (r"\bNASDAQ\b|\bNYSE\b|\bAMEX\b|\bARCA\b", "EXCHANGE"),
    ]
    for pattern, repl in replacements:
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    return out


def select_days(bars: list[dict[str, Any]], start: str, end: str) -> list[str]:
    days = sorted({date_key(row["t"]) for row in bars})
    return [day for day in days if start <= day <= end]


def build_requests(
    *,
    manifest: dict[str, Any],
    run_id: str,
    ticker: str,
    arm: str,
    n_agents: int,
    persona_seed: int,
    start: str,
    end: str,
    model_ids: list[str],
    temperatures: list[float],
    run_salt: str,
) -> list[dict[str, Any]]:
    bars_all = read_jsonl_gcs(snapshot_uri(manifest, "calib", ticker, "bars_1d.jsonl"))
    news_all = read_jsonl_gcs(snapshot_uri(manifest, "calib", ticker, "news.jsonl"))
    days = select_days(bars_all, start, end)
    personas = PersonaBank(n_agents, seed=persona_seed).personas
    combos = [(model_id, temperature) for model_id in model_ids for temperature in temperatures]
    sys_t = load_template("agent_system.j2")
    user_t = load_template("decision_user.j2")
    alias = alias_symbol(ticker, run_salt)
    stock_name = f"{ticker} Holdings" if arm == "named" else f"{alias} Holdings"
    requests: list[dict[str, Any]] = []
    for day_idx, asof in enumerate(days):
        bars = [row for row in bars_all if date_key(row["t"]) <= asof][-30:]
        news = [
            row for row in news_all
            if (row.get("created_at") or row.get("updated_at"))
            and date_key(str(row.get("created_at") or row.get("updated_at"))) <= asof
        ][-5:]
        bars_block = "\n".join(bar_line(row) for row in bars)
        news_lines = [
            f"{row.get('created_at') or row.get('updated_at')}: {str(row.get('headline') or row.get('summary') or '')[:180]}"
            for row in news
        ]
        news_block = "\n".join(news_lines)
        if arm == "alias":
            bars_block = scrub_alias_text(bars_block, ticker, alias, stock_name)
            news_block = scrub_alias_text(news_block, ticker, alias, stock_name)
        for agent_idx, persona in enumerate(personas):
            model_id, temperature = combos[agent_idx % len(combos)]
            prompt = render(sys_t, persona=persona.render()) + "\n\n" + render(
                user_t,
                asof_date=asof,
                name_or_alias=stock_name,
                bars_block=bars_block,
                news_block=news_block,
                shares=str(persona.shares),
                avg_cost=f"{bars[-1]['c']:.2f}" if bars else "1.00",
                cash=f"{persona.cash:.2f}",
            )
            requests.append({
                "request_id": f"{run_id}:{ticker}:{arm}:{asof}:a{agent_idx:03d}",
                "run_id": run_id,
                "ticker": ticker,
                "arm": arm,
                "day": asof,
                "agent_idx": agent_idx,
                "persona_id": persona.persona_id,
                "model_id": model_id,
                "sampling": {
                    "temperature": temperature,
                    "seed": persona_seed * 1_000_003 + day_idx * 10_000 + agent_idx,
                },
                "last_price": float(bars[-1]["c"]) if bars else 1.0,
                "prompt_sha256": prompt_sha(prompt),
                "prompt": prompt,
            })
    return requests


def load_robintrack_daily(manifest: dict[str, Any], ticker: str) -> dict[str, dict[str, float]]:
    text = read_gcs_text(snapshot_uri(manifest, "calib", ticker, "robintrack.csv"))
    latest_by_day: dict[str, tuple[str, int]] = {}
    for row in csv.DictReader(text.splitlines()):
        ts = str(row["timestamp"])
        day = date_key(ts)
        users = int(float(row["users_holding"]))
        if day not in latest_by_day or ts > latest_by_day[day][0]:
            latest_by_day[day] = (ts, users)
    out: dict[str, dict[str, float]] = {}
    prev: int | None = None
    for day in sorted(latest_by_day):
        users = latest_by_day[day][1]
        out[day] = {
            "users_holding": float(users),
            "d_holders": float("nan") if prev is None else float(users - prev),
        }
        prev = users
    return out


def decision_entropy(decisions: list[AgentDecision]) -> float:
    if not decisions:
        return 0.0
    counts = {action: 0 for action in ("buy", "sell", "hold")}
    for decision in decisions:
        counts[decision.action] += 1
    entropy = 0.0
    for count in counts.values():
        if count:
            p = count / len(decisions)
            entropy -= p * math.log2(p)
    return entropy


def summarize_simulation(
    requests: list[dict[str, Any]],
    output_rows: list[dict[str, Any]],
    robintrack: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    req_by_id = {row["request_id"]: row for row in requests}
    decisions_by_day: dict[str, list[AgentDecision]] = {}
    request_count_by_day: dict[str, int] = {}
    last_price_by_day: dict[str, float] = {}
    for req in requests:
        request_count_by_day[req["day"]] = request_count_by_day.get(req["day"], 0) + 1
        last_price_by_day[req["day"]] = float(req["last_price"])
    for row in output_rows:
        req = req_by_id.get(row["request_id"])
        if not req or not row.get("decision"):
            continue
        decision = AgentDecision(**row["decision"])
        decisions_by_day.setdefault(req["day"], []).append(decision)
    sim_rows: list[dict[str, Any]] = []
    auction_price: float | None = None
    for day in sorted(request_count_by_day):
        auction_price = last_price_by_day[day] if auction_price is None else auction_price
        decisions = decisions_by_day.get(day, [])
        auction = call_auction(decisions, auction_price)
        auction_price = auction.price
        counts = {action: 0 for action in ("buy", "sell", "hold")}
        for decision in decisions:
            counts[decision.action] += 1
        rt = robintrack.get(day, {})
        d_holders = rt.get("d_holders")
        sample_req = next(req for req in requests if req["day"] == day)
        sim_rows.append({
            "run_id": sample_req["run_id"],
            "ticker": sample_req["ticker"],
            "arm": sample_req["arm"],
            "day": day,
            "n_requests": request_count_by_day[day],
            "n_valid": len(decisions),
            "valid_json_rate": len(decisions) / request_count_by_day[day] if request_count_by_day[day] else 0.0,
            "flow_imbalance": flow_imbalance(decisions),
            "flow_imbalance_unweighted": flow_imbalance(decisions, confidence_weighted=False),
            "decision_entropy": decision_entropy(decisions),
            "buy_count": counts["buy"],
            "sell_count": counts["sell"],
            "hold_count": counts["hold"],
            "auction_price": auction.price,
            "auction_volume": auction.volume,
            "real_close": last_price_by_day[day],
            "robintrack_users_holding": rt.get("users_holding"),
            "robintrack_d_holders": None if d_holders is None or math.isnan(float(d_holders)) else d_holders,
        })
    return sim_rows


def encode_jsonl(rows: Iterable[dict[str, Any]]) -> str:
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)


def run_model(
    *,
    model_id: str,
    requests: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
    gcs_model_root: str,
    gcs_outputs_uri: str,
    max_new_tokens: int,
    chunk_size: int,
    gpu_memory_utilization: float,
    enforce_eager: bool,
) -> list[dict[str, Any]]:
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import GuidedDecodingParams

    answered = {row["request_id"] for row in existing_rows}
    todo = [row for row in requests if row["model_id"] == model_id and row["request_id"] not in answered]
    if not todo:
        return existing_rows

    model_gcs_uri = manifest_model_uri(gcs_model_root, model_id)
    local_model = Path("/tmp/agorasim-models") / safe_model_id(model_id)
    if not (local_model / "config.json").exists():
        downloaded = download_prefix(model_gcs_uri, local_model)
        if not (local_model / "config.json").exists():
            raise FileNotFoundError(f"Downloaded {downloaded} files from {model_gcs_uri}, but config.json is missing")

    llm = LLM(
        model=str(local_model),
        dtype="float16",
        gpu_memory_utilization=gpu_memory_utilization,
        max_model_len=4096,
        enforce_eager=enforce_eager,
    )
    guided = GuidedDecodingParams.from_optional(json=DECISION_JSON_SCHEMA, backend="lm-format-enforcer")
    output_rows = existing_rows
    for idx in range(0, len(todo), chunk_size):
        batch = todo[idx:idx + chunk_size]
        params = [
            SamplingParams(
                temperature=float(req["sampling"]["temperature"]),
                seed=int(req["sampling"]["seed"]),
                max_tokens=max_new_tokens,
                guided_decoding=guided,
            )
            for req in batch
        ]
        generated = llm.generate([req["prompt"] for req in batch], params)
        for req, result in zip(batch, generated):
            raw_text = result.outputs[0].text
            decision = parse_decision(raw_text)
            row = {
                "request_id": req["request_id"],
                "model_id": model_id,
                "raw_text": raw_text,
                "parsed": decision is not None,
                "decision": decision.model_dump() if decision is not None else None,
            }
            output_rows.append(row)
        upload_text(gcs_outputs_uri, encode_jsonl(output_rows), "application/jsonl")
    del llm
    gc.collect()
    try:
        import torch

        torch.cuda.empty_cache()
    except Exception:
        pass
    return output_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--arm", choices=["named", "alias"], required=True)
    parser.add_argument("--gcs-output-dir", required=True)
    parser.add_argument("--gcs-model-root", required=True)
    parser.add_argument("--gcs-snapshot-manifest", required=True)
    parser.add_argument("--model-id", action="append", required=True)
    parser.add_argument("--temperature", action="append", type=float, required=True)
    parser.add_argument("--n-agents", type=int, default=100)
    parser.add_argument("--persona-seed", type=int, default=1337)
    parser.add_argument("--start", default="2019-07-01")
    parser.add_argument("--end", default="2019-12-31")
    parser.add_argument("--run-salt", default="calib-2019-v1")
    parser.add_argument("--max-new-tokens", type=int, default=160)
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    parser.add_argument("--enforce-eager", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("VLLM_TARGET_DEVICE", "cuda")
    started = time.time()
    gcs_dir = args.gcs_output_dir.rstrip("/")
    requests_uri = f"{gcs_dir}/requests.jsonl"
    outputs_uri = f"{gcs_dir}/outputs.jsonl"
    sim_uri = f"{gcs_dir}/sim.jsonl"
    summary_uri = f"{gcs_dir}/worker_summary.json"

    manifest = download_json(args.gcs_snapshot_manifest)
    requests = build_requests(
        manifest=manifest,
        run_id=args.run_id,
        ticker=args.ticker,
        arm=args.arm,
        n_agents=args.n_agents,
        persona_seed=args.persona_seed,
        start=args.start,
        end=args.end,
        model_ids=args.model_id,
        temperatures=args.temperature,
        run_salt=args.run_salt,
    )
    upload_text(requests_uri, encode_jsonl(requests), "application/jsonl")

    existing_text = read_gcs_text_if_exists(outputs_uri)
    output_rows = list(iter_jsonl_text(existing_text))
    for model_id in args.model_id:
        output_rows = run_model(
            model_id=model_id,
            requests=requests,
            existing_rows=output_rows,
            gcs_model_root=args.gcs_model_root,
            gcs_outputs_uri=outputs_uri,
            max_new_tokens=args.max_new_tokens,
            chunk_size=args.chunk_size,
            gpu_memory_utilization=args.gpu_memory_utilization,
            enforce_eager=args.enforce_eager,
        )

    robintrack = load_robintrack_daily(manifest, args.ticker)
    sim_rows = summarize_simulation(requests, output_rows, robintrack)
    upload_text(sim_uri, encode_jsonl(sim_rows), "application/jsonl")
    valid = sum(1 for row in output_rows if row.get("parsed"))
    summary = {
        "run_id": args.run_id,
        "ticker": args.ticker,
        "arm": args.arm,
        "model_ids": args.model_id,
        "temperatures": args.temperature,
        "n_agents": args.n_agents,
        "n_requests": len(requests),
        "n_outputs": len(output_rows),
        "valid_json_rate": valid / len(requests) if requests else 0.0,
        "days": len(sim_rows),
        "elapsed_seconds": time.time() - started,
        "gcs_requests_uri": requests_uri,
        "gcs_outputs_uri": outputs_uri,
        "gcs_sim_uri": sim_uri,
    }
    upload_json(summary_uri, summary)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
