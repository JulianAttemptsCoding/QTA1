"""P2 / GATE G2 worker: run ONE real model on a real OOS-snapshot slice and measure the
valid-JSON rate through the *production* inference path (agents/vllm_batch.run_offline).

Builds point-in-time decision prompts (L-01: only bars/news dated <= the decision day) for
`--n-agents` personas x `--days` trading days of one frozen OOS ticker, runs them under
guided JSON decoding, and reports valid_json_rate. This is the real-model counterpart to the
local stub smoke (scripts/p2_smoke_sim.py). Runs on the Vertex worker image (GPU).

Run (on Vertex):
  python scripts/p2_gate_real_model.py --base gs://BUCKET/agorasim \
    --model Qwen/Qwen2.5-1.5B-Instruct --ticker NVNI --n-agents 20 --days 10 --arm named
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from agorasim.agents.prompt_builder import load_template, prompt_hash
from agorasim.agents.sim_prompts import build_requests, read_jsonl
from agorasim.infra.gcs import download_prefix, upload_file
from agorasim.schemas import parse_decision


def sanitize(s: str) -> str:
    return s.replace("/", "__")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="gs://BUCKET/agorasim")
    ap.add_argument("--model", required=True)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--n-agents", type=int, default=20)
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--arm", choices=["named", "alias"], default="named")
    ap.add_argument("--universe", default="oos")
    args = ap.parse_args()

    from agorasim.agents.vllm_batch import run_offline  # heavy import (Vertex worker only)

    snap_dir = Path(f"/tmp/snap/{args.universe}/{args.ticker}")
    download_prefix(f"{args.base}/snapshots/g1/{args.universe}/{args.ticker}", str(snap_dir))
    requests = build_requests(args.ticker, snap_dir, args.n_agents, args.days, args.arm)

    work = Path(tempfile.mkdtemp())
    req_path, out_path = work / "requests.jsonl", work / "outputs.jsonl"
    req_path.write_text("\n".join(json.dumps(r) for r in requests) + "\n")
    run_offline(req_path, out_path, args.model)

    outputs = read_jsonl(out_path)
    valid = sum(1 for o in outputs if parse_decision(o["raw_text"]) is not None)
    rate = valid / len(outputs) if outputs else 0.0
    invalid_examples = [o["raw_text"] for o in outputs
                        if parse_decision(o["raw_text"]) is None][:3]
    rec = {"model": args.model, "ticker": args.ticker, "arm": args.arm,
           "universe": args.universe, "n_agents": args.n_agents, "days": args.days,
           "n": len(outputs), "valid_json_rate": round(rate, 4),
           "prompt_template_hash": prompt_hash(load_template("agent_system.j2")),
           "invalid_examples": invalid_examples}
    print("G2_REAL_RESULT", json.dumps(rec), flush=True)

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(rec, tf)
        tmp = tf.name
    upload_file(tmp, f"{args.base}/runs/g2_smoke/{sanitize(args.model)}__{args.ticker}_{args.arm}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
