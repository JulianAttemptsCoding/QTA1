"""Collector (CPU, local): pool every model sub-crowd's raw decisions for a run_id into the
per-(ticker, day) crowd signals — flow_imbalance (the RQ3 prediction signal) and the
call-auction realism path. Writes runs/<run_id>/signals.jsonl and a summary; uploads to GCS.

Run:
  python scripts/collect_sim_phase.py --base gs://BUCKET/agorasim --run-id oos-main-v1 \
    --snapshots data/snapshots/g1/oos
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from agorasim.agents.sim_prompts import read_jsonl
from agorasim.market import call_auction, flow_imbalance
from agorasim.schemas import parse_decision


def parse_request_id(rid: str) -> tuple[str, str, str]:
    """`TICKER-arm-YYYY-MM-DD-aN` -> (ticker, arm, asof). Tickers/arm have no hyphens."""
    p = rid.split("-")
    return p[0], p[1], "-".join(p[2:5])


def load_closes(snapshots: Path) -> dict[tuple[str, str], float]:
    """(ticker, date) -> close, from the frozen snapshot bars (auction reference price)."""
    closes: dict[tuple[str, str], float] = {}
    for tk_dir in sorted(p for p in snapshots.iterdir() if p.is_dir()):
        for b in read_jsonl(tk_dir / "bars_1d.jsonl"):
            closes[(tk_dir.name, b["t"][:10])] = float(b["c"])
    return closes


def aggregate(raw_records: list[dict], closes: dict[tuple[str, str], float]) -> list[dict]:
    by_day: dict[tuple[str, str, str], list] = defaultdict(list)
    n_valid = n_total = 0
    for rec in raw_records:
        ticker, arm, asof = parse_request_id(rec["request_id"])
        n_total += 1
        d = parse_decision(rec.get("raw_text", ""))
        if d is not None:
            n_valid += 1
            by_day[(ticker, arm, asof)].append(d)
    rows = []
    for (ticker, arm, asof), decisions in sorted(by_day.items()):
        last_price = closes.get((ticker, asof), 1.0)
        auc = call_auction(decisions, last_price=last_price)
        rows.append({
            "ticker": ticker, "arm": arm, "date": asof, "n_decisions": len(decisions),
            "imbalance_cw": round(flow_imbalance(decisions, confidence_weighted=True), 6),
            "imbalance_uw": round(flow_imbalance(decisions, confidence_weighted=False), 6),
            "auction_price": round(auc.price, 4), "auction_volume": auc.volume,
            "buy_qty": auc.buy_qty, "sell_qty": auc.sell_qty,
            "ref_close": round(last_price, 4) if last_price else None,
        })
    rows.append({"_summary": True, "n_decisions_total": n_total, "n_valid": n_valid,
                 "valid_rate": round(n_valid / n_total, 4) if n_total else 0.0,
                 "ticker_days": len(by_day)})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--snapshots", default="data/snapshots/g1/oos")
    args = ap.parse_args()

    # gcloud CLI (not the google-cloud-storage client) for GCS: locally the Python client
    # picks up ADC for an account without bucket access (403); the gcloud CLI uses the
    # authorized user. See STATE.json collector_auth_note.
    raw_dir = Path(tempfile.mkdtemp())
    subprocess.run(["gcloud", "storage", "cp", "--recursive",
                    f"{args.base}/runs/{args.run_id}/raw", str(raw_dir)], check=True)
    raw_records: list[dict] = []
    for f in sorted(raw_dir.rglob("*.jsonl")):
        raw_records.extend(read_jsonl(f))
    if not raw_records:
        raise RuntimeError(f"No raw decisions under {args.base}/runs/{args.run_id}/raw")

    rows = aggregate(raw_records, load_closes(Path(args.snapshots)))
    out = Path(tempfile.mkdtemp()) / "signals.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    subprocess.run(["gcloud", "storage", "cp", str(out),
                    f"{args.base}/runs/{args.run_id}/signals.jsonl"], check=True)

    summary = rows[-1]
    print("COLLECT_DONE", json.dumps(summary), flush=True)
    print(f"signals -> {args.base}/runs/{args.run_id}/signals.jsonl ({len(rows) - 1} ticker-days)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
