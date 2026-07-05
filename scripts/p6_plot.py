"""P6 figure: crowd prediction vs actual, for a completed OOS run.

Three panels:
  A) pooled scatter of the crowd's daily flow-imbalance signal vs the realized 5-day forward
     real return, with the OLS fit and the information coefficient (the core RQ3 picture);
  B) one representative ticker's actual close-price track with the daily crowd imbalance
     underlaid (prediction vs actual, over time);
  C) equity curves of following vs fading the crowd (sign(signal) * next-day return, averaged
     across the universe each day) vs equal-weight buy-and-hold.

Signals are pulled with the gcloud CLI; returns come from the local G1 snapshots.
Run: python scripts/p6_plot.py --run-id oos-main-v2 --example TLRY
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root -> import scripts.*

from agorasim.agents.sim_prompts import read_jsonl
from agorasim.evals.prediction import information_coefficient
from scripts.p5_stats import GCLOUD, BASE, block_bootstrap_ic, forward_returns, ticker_closes


def load_signals(run_id: str) -> list[dict]:
    tmp = Path(tempfile.mkdtemp())
    subprocess.run([GCLOUD, "storage", "cp", f"{BASE}/runs/{run_id}/signals.jsonl",
                    str(tmp / "s.jsonl")], check=True)
    return [r for r in read_jsonl(tmp / "s.jsonl") if not r.get("_summary")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--snapshots", default="data/snapshots/g1/oos")
    ap.add_argument("--example", default="TLRY")
    ap.add_argument("--out", default="docs/figures/rq3_prediction_vs_actual.png")
    args = ap.parse_args()

    signals = load_signals(args.run_id)
    closes = ticker_closes(Path(args.snapshots))
    fwd5 = {tk: forward_returns(c, 5) for tk, c in closes.items()}
    fwd1 = {tk: forward_returns(c, 1) for tk, c in closes.items()}

    # ---- pooled signal vs 5-day forward return ----
    sig, ret = [], []
    for r in signals:
        fr = fwd5.get(r["ticker"], {}).get(r["date"])
        if fr is not None:
            sig.append(r["imbalance_cw"]); ret.append(fr)
    sig, ret = np.array(sig), np.array(ret)
    ic = information_coefficient(sig, ret)

    fig, (axA, axB, axC) = plt.subplots(1, 3, figsize=(18, 5.2))

    # Panel A: scatter + OLS fit. Clip the y-axis to a robust window so the (rank-based) IC
    # relationship is visible -- a few sub-$1 microcaps have >1000% 5d moves that otherwise
    # crush the scale. IC is Spearman (outlier-robust), so clipping is display-only.
    retp = np.clip(ret * 100, -40, 40)
    axA.scatter(sig, retp, s=14, alpha=0.45, color="#2b6cb0", edgecolors="none")
    if len(sig) > 2 and np.std(sig) > 0:
        b, a = np.polyfit(sig, retp, 1)
        xs = np.linspace(sig.min(), sig.max(), 50)
        axA.plot(xs, a + b * xs, color="#c53030", lw=2, label=f"OLS slope {b:+.1f}%/unit")
    axA.axhline(0, color="gray", lw=0.7); axA.axvline(0, color="gray", lw=0.7)
    axA.set_ylim(-42, 42)
    axA.set_xlabel("crowd flow-imbalance (conf-weighted)")
    axA.set_ylabel("actual 5-day forward return (%, clipped ±40)")
    axA.set_title(f"A. Crowd signal vs actual 5d return\nSpearman IC = {ic:+.3f}  (n={len(sig)})")
    axA.legend(loc="upper right", fontsize=9)

    # Panel B: one ticker — actual price track + daily crowd imbalance
    tk = args.example
    rows = sorted((r for r in signals if r["ticker"] == tk), key=lambda r: r["date"])
    dates = [r["date"] for r in rows]
    imb = [r["imbalance_cw"] for r in rows]
    px = [dict(closes[tk]).get(d) for d in dates]
    x = np.arange(len(dates))
    axB.bar(x, imb, color=["#2f855a" if v >= 0 else "#c53030" for v in imb], alpha=0.5,
            width=0.8, label="crowd imbalance (L)")
    axB.axhline(0, color="gray", lw=0.7)
    axB.set_ylabel("crowd flow-imbalance"); axB.set_ylim(-1.05, 1.05)
    axBp = axB.twinx()
    axBp.plot(x, px, color="#1a202c", lw=1.8, marker="o", ms=2.5, label="actual close (R)")
    axBp.set_ylabel("actual close price ($)")
    step = max(1, len(dates) // 6)
    axB.set_xticks(x[::step]); axB.set_xticklabels([d[5:] for d in dates[::step]], fontsize=8)
    axB.set_title(f"B. {tk}: prediction (crowd) vs actual (price)")
    axB.set_xlabel("2026 date (MM-DD)")

    # Panel C: information coefficient by horizon, with 95% moving-block bootstrap CIs.
    # Rank-based -> outlier-robust; shows the whole finding at a glance (0 at 1d, negative &
    # CI-excludes-0 at 5d) without the microcap-magnitude distortion of an equity curve.
    combos = [("imbalance_cw", 1), ("imbalance_cw", 5), ("imbalance_uw", 1), ("imbalance_uw", 5)]
    fwd = {1: fwd1, 5: fwd5}
    labels, ics, los, his = [], [], [], []
    for key, h in combos:
        s, r = [], []
        for row in signals:
            fr = fwd[h].get(row["ticker"], {}).get(row["date"])
            if fr is not None:
                s.append(row[key]); r.append(fr)
        s, r = np.array(s), np.array(r)
        icv = information_coefficient(s, r)
        lo, hi = block_bootstrap_ic(s, r)
        labels.append(f"{'conf-wt' if 'cw' in key else 'unwt'}\n{h}d")
        ics.append(icv); los.append(icv - lo); his.append(hi - icv)
    xc = np.arange(len(combos))
    colors = ["#2b6cb0" if i >= 0 else "#c53030" for i in ics]
    axC.bar(xc, ics, color=colors, alpha=0.8, yerr=[los, his], capsize=5, ecolor="#1a202c")
    axC.axhline(0, color="gray", lw=0.9)
    axC.set_xticks(xc); axC.set_xticklabels(labels, fontsize=9)
    axC.set_ylabel("information coefficient (Spearman)")
    axC.set_title("C. IC by signal x horizon\n(95% block-bootstrap CI)")

    fig.suptitle(f"AgoraSim RQ3 — LLM retail crowd vs real small-cap returns ({args.run_id}, "
                 f"OOS-10, alias arm)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130)
    print(f"wrote {out}  (IC_5d={ic:+.3f}, n={len(sig)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
