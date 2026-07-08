"""P4 OOS worker.

Runs only inside Vertex. It reuses the validated P3 inference path against OOS
snapshots and adds next-day real-return targets plus per-model crowd flows.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import time
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agorasim.market import flow_imbalance
from agorasim.schemas import AgentDecision

from p3_calibration_worker import (
    build_requests,
    download_json,
    encode_jsonl,
    iter_jsonl_text,
    read_gcs_text_if_exists,
    run_model,
    summarize_simulation,
    upload_json,
    upload_text,
)


def add_prediction_targets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    closes = [float(row["real_close"]) for row in rows]
    for idx, row in enumerate(rows):
        row["next_day_return"] = (
            closes[idx + 1] / closes[idx] - 1.0
            if idx + 1 < len(closes) and closes[idx] != 0
            else None
        )
        for horizon in (1, 5, 20):
            row[f"momentum_{horizon}d"] = (
                closes[idx] / closes[idx - horizon] - 1.0
                if idx >= horizon and closes[idx - horizon] != 0
                else None
            )
    return rows


def add_model_flows(
    rows: list[dict[str, Any]],
    requests: list[dict[str, Any]],
    output_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    req_by_id = {row["request_id"]: row for row in requests}
    grouped: dict[str, dict[str, list[AgentDecision]]] = defaultdict(lambda: defaultdict(list))
    for output in output_rows:
        request = req_by_id.get(output["request_id"])
        if not request or not output.get("decision"):
            continue
        grouped[request["day"]][request["model_id"]].append(AgentDecision(**output["decision"]))
    for row in rows:
        by_model = grouped.get(row["day"], {})
        row["model_flow_imbalance"] = {
            model_id: flow_imbalance(decisions)
            for model_id, decisions in sorted(by_model.items())
        }
        row["model_flow_imbalance_unweighted"] = {
            model_id: flow_imbalance(decisions, confidence_weighted=False)
            for model_id, decisions in sorted(by_model.items())
        }
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--arm", choices=["named", "alias"], default="alias")
    parser.add_argument("--gcs-output-dir", required=True)
    parser.add_argument("--gcs-model-root", required=True)
    parser.add_argument("--gcs-snapshot-manifest", required=True)
    parser.add_argument("--model-id", action="append", required=True)
    parser.add_argument("--temperature", action="append", type=float, required=True)
    parser.add_argument("--n-agents", type=int, default=200)
    parser.add_argument("--persona-seed", type=int, default=1337)
    parser.add_argument("--start", default="2025-01-02")
    parser.add_argument("--end", default="2025-07-03")
    parser.add_argument("--run-salt", default="oos-2025-v1")
    parser.add_argument("--max-new-tokens", type=int, default=160)
    parser.add_argument("--chunk-size", type=int, default=128)
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
        snapshot_kind="oos",
    )
    upload_text(requests_uri, encode_jsonl(requests), "application/jsonl")

    output_rows = list(iter_jsonl_text(read_gcs_text_if_exists(outputs_uri)))
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

    sim_rows = summarize_simulation(requests, output_rows, {})
    add_model_flows(sim_rows, requests, output_rows)
    add_prediction_targets(sim_rows)
    upload_text(sim_uri, encode_jsonl(sim_rows), "application/jsonl")
    valid = sum(1 for row in output_rows if row.get("parsed"))
    summary = {
        "run_id": args.run_id,
        "phase": "P4",
        "experiment": "main",
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
    gc.collect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
