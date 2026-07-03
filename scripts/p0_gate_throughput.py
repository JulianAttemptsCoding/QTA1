"""GATE G0 (compute): run inside a Vertex T4 worker.

Loads one cached model under vLLM, runs representative decision prompts, measures
decisions/hour and valid-JSON rate, and writes JSON results to GCS. A local
orchestration step aggregates those JSON files into docs/G0_THROUGHPUT.md.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from pathlib import Path

from google.cloud import storage

from agorasim.agents import PersonaBank
from agorasim.agents.prompt_builder import load_template, render
from agorasim.schemas import parse_decision


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


def safe_model_id(model_id: str) -> str:
    return model_id.replace("/", "__")


def parse_gs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"Expected gs:// URI, got {uri}")
    bucket, _, prefix = uri[5:].partition("/")
    return bucket, prefix.strip("/")


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


def manifest_model_uri(manifest: dict, model_id: str) -> str | None:
    entry = manifest.get(model_id)
    if isinstance(entry, dict) and entry.get("status") == "OK" and entry.get("gcs"):
        return str(entry["gcs"])
    return None


def download_json(gcs_uri: str) -> dict:
    bucket_name, prefix = parse_gs_uri(gcs_uri)
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(prefix)
    return json.loads(blob.download_as_text())


def resolve_model_gcs_uri(gcs_model_root: str, model_id: str) -> str:
    root = gcs_model_root.rstrip("/")
    try:
        manifest = download_json(f"{root}/_cache_manifest.json")
    except Exception as exc:
        print(f"WARN could not read model cache manifest: {exc}", flush=True)
    else:
        manifest_uri = manifest_model_uri(manifest, model_id)
        if manifest_uri:
            return manifest_uri
    return f"{root}/{safe_model_id(model_id)}"


def download_prefix(gcs_uri: str, local_dir: Path) -> int:
    bucket_name, prefix = parse_gs_uri(gcs_uri.rstrip("/") + "/")
    list_prefix = f"{prefix.rstrip('/')}/" if prefix else ""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    local_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    for blob in client.list_blobs(bucket, prefix=list_prefix):
        if blob.name.endswith("/"):
            continue
        rel = relative_blob_path(blob.name, list_prefix)
        if not rel:
            continue
        dest = local_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(dest)
        downloaded += 1
    return downloaded


def upload_json(payload: dict, gcs_uri: str) -> None:
    bucket_name, prefix = parse_gs_uri(gcs_uri)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    bucket.blob(prefix).upload_from_string(json.dumps(payload, indent=2, sort_keys=True), content_type="application/json")


def representative_prompts(n: int, seed: int = 1337) -> list[str]:
    rng = random.Random(seed)
    personas = PersonaBank(n, seed=seed).personas
    sys_t = load_template("agent_system.j2")
    user_t = load_template("decision_user.j2")
    prompts: list[str] = []
    for i, persona in enumerate(personas):
        base_price = 8.0 + (i % 23) * 0.73
        bars = []
        for d in range(30):
            close = base_price * (1.0 + 0.002 * d + rng.uniform(-0.015, 0.015))
            bars.append(f"2025-03-{d + 1:02d}, {close*0.98:.2f}, {close*1.03:.2f}, {close*0.96:.2f}, {close:.2f}, {rng.randint(80_000, 3_000_000)}")
        news = [
            "2025-03-05T14:01:00Z: Company reports preliminary revenue above prior guidance.",
            "2025-03-11T20:30:00Z: Shares move after new product announcement.",
            "2025-03-18T13:15:00Z: Analyst notes elevated retail attention and volatility.",
        ]
        system = render(sys_t, persona=persona.render())
        user = render(
            user_t,
            asof_date="2025-04-01",
            name_or_alias="XABC Holdings",
            bars_block="\n".join(bars),
            news_block="\n".join(news),
            shares=str(persona.shares),
            avg_cost=f"{base_price:.2f}",
            cash=f"{persona.cash:.2f}",
        )
        prompts.append(f"{system}\n\n{user}")
    return prompts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--gcs-model-root", required=True)
    parser.add_argument("--gcs-output-uri", required=True)
    parser.add_argument("--n-prompts", type=int, default=512)
    parser.add_argument("--max-new-tokens", type=int, default=160)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    parser.add_argument("--enforce-eager", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("VLLM_TARGET_DEVICE", "cuda")
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import GuidedDecodingParams

    model_gcs_uri = resolve_model_gcs_uri(args.gcs_model_root, args.model_id)
    safe_id = safe_model_id(args.model_id)
    local_model = Path("/tmp/agorasim-models") / safe_id
    downloaded = download_prefix(model_gcs_uri, local_model)
    if not (local_model / "config.json").exists():
        raise FileNotFoundError(f"Downloaded {downloaded} files from {model_gcs_uri}, but {local_model / 'config.json'} is missing")
    prompts = representative_prompts(args.n_prompts)
    guided = GuidedDecodingParams.from_optional(json=DECISION_JSON_SCHEMA, backend="lm-format-enforcer")
    params = SamplingParams(temperature=0.0, max_tokens=args.max_new_tokens, guided_decoding=guided)

    started = time.perf_counter()
    llm = LLM(
        model=str(local_model),
        dtype="float16",
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_model_len=4096,
        enforce_eager=args.enforce_eager,
    )
    outputs = llm.generate(prompts, params)
    elapsed = time.perf_counter() - started
    raw = [out.outputs[0].text for out in outputs]
    valid = sum(1 for text in raw if parse_decision(text) is not None)
    invalid_examples = [text[:500] for text in raw if parse_decision(text) is None][:3]
    payload = {
        "model_id": args.model_id,
        "n_prompts": len(prompts),
        "elapsed_seconds": elapsed,
        "decisions_per_hour": len(prompts) / elapsed * 3600.0 if elapsed else 0.0,
        "valid_json_rate": valid / len(prompts) if prompts else 0.0,
        "max_new_tokens": args.max_new_tokens,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "enforce_eager": args.enforce_eager,
        "guided_decoding": True,
        "model_gcs_uri": model_gcs_uri,
        "invalid_examples": invalid_examples,
    }
    upload_json(payload, args.gcs_output_uri)
    print(json.dumps(payload, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
