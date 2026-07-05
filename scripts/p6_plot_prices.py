"""P6 figure: crowd-PREDICTED price vs ACTUAL price over the OOS window, on ONE plot.

The crowd emits a daily flow-imbalance signal, not a price. We read it as the crowd's own
directional view at a realistic magnitude: each day the predicted return is the net imbalance
scaled by that ticker's realized daily volatility (sign = the crowd's direction, so a net-long
crowd predicts up), and we FREE-RUN a price path from the first OOS close:
    pred[0]   = actual_close[0]
    pred[t+1] = pred[t] * (1 + imbalance_t * sigma_ticker)
Each ticker's actual and predicted paths are rebased to 100 at the OOS start and averaged
across the 10-name universe, giving one actual index and one predicted index on the same axes.
The gap that opens up is the crowd's price-forecast error: it stays optimistic (index rises)
while the real small-cap basket does what it did.

Run: python scripts/p6_plot_prices.py --run-id oos-main-v2
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p5_stats import ticker_closes
from scripts.p6_plot import load_signals

TICKERS = ["NVNI", "TLRY", "EDIT", "CHPT", "BLNK", "FRSX", "TPET", "OGI", "CCO", "ICCM"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--snapshots", default="data/snapshots/g1/oos")
    ap.add_argument("--out", default="docs/figures/rq3_predicted_vs_actual_price.png")
    args = ap.parse_args()

    signals = load_signals(args.run_id)
    closes = {tk: dict(v) for tk, v in ticker_closes(Path(args.snapshots)).items()}

    actual_idx, pred_idx = [], []          # per-ticker rebased-to-100 paths
    n_days = None
    for tk in TICKERS:
        rows = sorted((r for r in signals if r["ticker"] == tk), key=lambda r: r["date"])
        dates = [r["date"] for r in rows]
        imb = [r["imbalance_cw"] for r in rows]
        actual = np.array([closes[tk].get(d) for d in dates], dtype=float)
        rets = np.diff(actual) / actual[:-1]
        # median |daily return| as the per-ticker magnitude, capped so a single microcap spike
        # (ICCM 45x) can't make the predicted path compound to absurd levels.
        sigma = min(float(np.median(np.abs(rets))) if len(rets) else 0.02, 0.06)
        pred = [actual[0]]
        for t in range(len(dates) - 1):
            r_day = float(np.clip(imb[t] * sigma, -0.06, 0.06))   # follow-crowd, calibrated
            pred.append(pred[-1] * (1 + r_day))
        pred = np.array(pred)
        actual_idx.append(actual / actual[0] * 100.0)
        pred_idx.append(pred / pred[0] * 100.0)
        n_days = len(dates) if n_days is None else min(n_days, len(dates))

    # median across tickers -> a robust equal-weight index (one 45x microcap can't dominate).
    A = np.median(np.vstack([a[:n_days] for a in actual_idx]), axis=0)
    P = np.median(np.vstack([p[:n_days] for p in pred_idx]), axis=0)
    # representative date labels from the first ticker
    ref_dates = [r["date"] for r in sorted((r for r in signals if r["ticker"] == TICKERS[0]),
                                           key=lambda r: r["date"])][:n_days]
    x = np.arange(n_days)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    ax.plot(x, A, color="#1a202c", lw=2.4, marker="o", ms=3, label="ACTUAL price (real close)")
    ax.plot(x, P, color="#2b6cb0", lw=2.4, ls="--", marker="s", ms=3,
            label="crowd-PREDICTED price (imbalance-driven)")
    ax.axhline(100, color="gray", lw=0.8)
    ax.fill_between(x, A, P, where=(P >= A), color="#c53030", alpha=0.10)
    ax.fill_between(x, A, P, where=(P < A), color="#2f855a", alpha=0.10)
    step = max(1, n_days // 8)
    ax.set_xticks(x[::step]); ax.set_xticklabels([d[5:] for d in ref_dates[::step]])
    ax.set_xlabel("2026 OOS trading day (MM-DD)")
    ax.set_ylabel("price index (rebased 100 at OOS start)")
    ax.set_title(f"AgoraSim RQ3 — crowd-predicted vs actual price, OOS-10 universe average "
                 f"({args.run_id}, alias arm)\nPredicted free-runs on the crowd's imbalance; it "
                 f"stays optimistic while the real basket ends {A[-1]-100:+.1f}%.", fontsize=11)
    ax.legend(loc="best", fontsize=11)
    fig.tight_layout()
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130)
    print(f"wrote {out}  (actual_end={A[-1]:.1f}, pred_end={P[-1]:.1f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
