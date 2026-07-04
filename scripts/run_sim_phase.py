"""Sim-phase worker (P3/P4): run ONE model's sub-crowd over tickers x point-in-time days and
log raw decisions to GCS. One model per Vertex job (process isolation, T4=1 GPU); jobs run in
parallel and the collector (scripts/collect_sim_phase.py) pools every model's decisions per
(ticker, day) into the crowd signals. A run is invalid without its manifest (D-12).

Diversity (D-07): the crowd = union of per-model sub-crowds; each model job uses a distinct
persona seed so personas differ across families, and sim_prompts mixes temperature per agent.

Run (on Vertex):
  python scripts/run_sim_phase.py --base gs://BUCKET/agorasim --run-id oos-main-v1 \
    --model Qwen/Qwen2.5-1.5B-Instruct --arm alias --tickers NVNI,TLRY,... \
    --days 125 --n-agents 70 --persona-seed 1337
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from agorasim.agents.prompt_builder import load_template, prompt_hash
from agorasim.agents.sim_prompts import build_requests
from agorasim.infra.gcs import download_prefix, upload_file
from agorasim.infra.run_manifest import RunManifest


def sanitize(s: str) -> str:
    return s.replace("/", "__")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="gs://BUCKET/agorasim")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--arm", choices=["named", "alias"], default="alias")
    ap.add_argument("--tickers", required=True, help="comma-separated")
    ap.add_argument("--universe", default="oos")
    ap.add_argument("--days", type=int, default=125)
    ap.add_argument("--n-agents", type=int, default=70)
    ap.add_argument("--persona-seed", type=int, default=1337)
    args = ap.parse_args()

    from agorasim.agents.vllm_batch import run_offline  # Vertex worker only

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    requests: list[dict] = []
    for tk in tickers:
        snap = Path(f"/tmp/snap/{args.universe}/{tk}")
        download_prefix(f"{args.base}/snapshots/g1/{args.universe}/{tk}", str(snap))
        requests.extend(build_requests(tk, snap, args.n_agents, args.days, args.arm,
                                       persona_seed=args.persona_seed))

    work = Path(tempfile.mkdtemp())
    req_path, out_path = work / "requests.jsonl", work / "outputs.jsonl"
    req_path.write_text("\n".join(json.dumps(r) for r in requests) + "\n")
    run_offline(req_path, out_path, args.model)  # guided decoding, resume ledger

    # Ship raw decisions (request_id encodes ticker/arm/date/agent) + the model tag.
    raw_dst = f"{args.base}/runs/{args.run_id}/raw/{sanitize(args.model)}_{args.arm}.jsonl"
    tagged = work / "tagged.jsonl"
    with out_path.open() as fin, tagged.open("w") as fout:
        for line in fin:
            rec = json.loads(line)
            rec["model"] = args.model
            fout.write(json.dumps(rec) + "\n")
    upload_file(str(tagged), raw_dst)

    # Backup-first manifest (D-12): written next to the run outputs.
    man = RunManifest.create(
        run_id=f"{args.run_id}-{sanitize(args.model)}-{args.arm}", phase="P4",
        config_path=Path("configs/models.yaml"),
        persona_bank_hash=f"seed={args.persona_seed}:n={args.n_agents}",
        prompt_hashes={"agent_system.j2": prompt_hash(load_template("agent_system.j2")),
                       "decision_user.j2": prompt_hash(load_template("decision_user.j2"))},
        model_ids=[args.model], seed=args.persona_seed,
        data_snapshot_hashes={"universe": args.universe, "tickers": ",".join(tickers)},
        notes=f"arm={args.arm} days={args.days} n_agents={args.n_agents} raw={raw_dst}")
    man_path = man.write(work)
    upload_file(str(man_path), f"{args.base}/runs/{args.run_id}/manifests/{man_path.name}")

    print("SIM_PHASE_DONE", json.dumps({"model": args.model, "arm": args.arm,
          "n_requests": len(requests), "raw": raw_dst}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
