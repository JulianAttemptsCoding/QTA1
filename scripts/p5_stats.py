"""P5 stats (CPU, local): turn a P4 run's crowd signals into RQ3 prediction statistics.

Pairs each (ticker, day) flow-imbalance signal with the realized forward real return from the
frozen snapshot, then computes — pooled across ticker-days — the information coefficient
(Spearman), hit rate, a Diebold-Mariano test of the crowd signal vs a momentum baseline
(D-09), a block-bootstrap CI on IC, and the Deflated Sharpe of the sign(signal) strategy
against the registered trial count (docs/TRIALS.md, D-11). All estimators are the standard
ones in agorasim.evals.prediction (no novelty).

Signals are pulled with the gcloud CLI (the google-cloud-storage client uses local ADC that
lacks bucket access — see STATE.json collector_auth_note); returns come from the local G1
snapshots. Writes docs/P5_STATS.md.

Run:
  python scripts/p5_stats.py --run-id oos-main-v1 --n-trials 4
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

# On Windows the CLI is gcloud.cmd, which bare subprocess (shell=False) cannot resolve.
GCLOUD = shutil.which("gcloud") or shutil.which("gcloud.cmd") or "gcloud"

from agorasim.agents.sim_prompts import read_jsonl
from agorasim.evals.prediction import (
    deflated_sharpe, diebold_mariano, hit_rate, information_coefficient,
)

BASE = "gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim"


def ticker_closes(snapshots: Path) -> dict[str, list[tuple[str, float]]]:
    """ticker -> chronological [(date, close)] from the frozen snapshot bars."""
    out: dict[str, list[tuple[str, float]]] = {}
    for d in sorted(p for p in snapshots.iterdir() if p.is_dir()):
        rows = sorted(({"d": b["t"][:10], "c": float(b["c"])} for b in read_jsonl(d / "bars_1d.jsonl")),
                      key=lambda r: r["d"])
        out[d.name] = [(r["d"], r["c"]) for r in rows]
    return out


def forward_returns(closes: list[tuple[str, float]], h: int) -> dict[str, float]:
    """date -> h-trading-day forward return (close[i+h]/close[i] - 1)."""
    idx = {d: i for i, (d, _) in enumerate(closes)}
    fr = {}
    for d, i in idx.items():
        if i + h < len(closes) and closes[i][1] > 0:
            fr[d] = closes[i + h][1] / closes[i][1] - 1.0
    return fr


def momentum(closes: list[tuple[str, float]], k: int) -> dict[str, float]:
    """date -> trailing k-day return (the D-09 momentum baseline signal)."""
    idx = {d: i for i, (d, _) in enumerate(closes)}
    mom = {}
    for d, i in idx.items():
        if i - k >= 0 and closes[i - k][1] > 0:
            mom[d] = closes[i][1] / closes[i - k][1] - 1.0
    return mom


def pair(signals: list[dict], closes_by_tk: dict, sig_key: str, h: int,
         baseline_k: int | None = None):
    """Aligned (signal, fwd_return[, baseline]) arrays over ticker-days with data."""
    s, r, b = [], [], []
    for row in signals:
        if row.get("_summary"):
            continue
        tk, date = row["ticker"], row["date"]
        closes = closes_by_tk.get(tk)
        if not closes:
            continue
        fr = forward_returns(closes, h).get(date)
        if fr is None:
            continue
        if baseline_k is not None:
            mv = momentum(closes, baseline_k).get(date)
            if mv is None:
                continue
            b.append(mv)
        s.append(float(row[sig_key]))
        r.append(fr)
    return np.array(s), np.array(r), np.array(b)


def block_bootstrap_ic(signal: np.ndarray, fwd: np.ndarray, block: int = 5,
                       n: int = 2000, seed: int = 7) -> tuple[float, float]:
    """95% CI on IC via a circular moving-block bootstrap over the pooled series."""
    rng = np.random.default_rng(seed)
    T = len(signal)
    if T < block + 1:
        return 0.0, 0.0
    n_blocks = int(np.ceil(T / block))
    ics = []
    for _ in range(n):
        starts = rng.integers(0, T, n_blocks)
        idx = np.concatenate([(np.arange(st, st + block) % T) for st in starts])[:T]
        ics.append(information_coefficient(signal[idx], fwd[idx]))
    lo, hi = np.percentile(ics, [2.5, 97.5])
    return float(lo), float(hi)


def strategy_sharpe(signal: np.ndarray, fwd: np.ndarray) -> tuple[float, float, float, int]:
    """Annualized SR + skew/kurt of the daily sign(signal)*fwd_return strategy."""
    ret = np.sign(signal) * fwd
    ret = ret[np.isfinite(ret)]
    if len(ret) < 3 or ret.std() == 0:
        return 0.0, 0.0, 3.0, len(ret)
    mu, sd = ret.mean(), ret.std(ddof=1)
    sr = mu / sd * np.sqrt(252)
    m = ret - mu
    skew = float((m ** 3).mean() / sd ** 3)
    kurt = float((m ** 4).mean() / sd ** 4)
    return float(sr), skew, kurt, len(ret)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--snapshots", default="data/snapshots/g1/oos")
    ap.add_argument("--n-trials", type=int, default=4)
    ap.add_argument("--horizons", default="1,5")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp())
    subprocess.run([GCLOUD, "storage", "cp", f"{BASE}/runs/{args.run_id}/signals.jsonl",
                    str(tmp / "signals.jsonl")], check=True)
    signals = read_jsonl(tmp / "signals.jsonl")
    closes_by_tk = ticker_closes(Path(args.snapshots))
    horizons = [int(x) for x in args.horizons.split(",")]

    results = {}
    per_trial_sr = []
    for sig_key in ("imbalance_cw", "imbalance_uw"):
        for h in horizons:
            s, r, _ = pair(signals, closes_by_tk, sig_key, h)
            ic = information_coefficient(s, r)
            hr = hit_rate(s, r)
            lo, hi = block_bootstrap_ic(s, r)
            sr, skew, kurt, nobs = strategy_sharpe(s, r)
            per_trial_sr.append(sr)
            # momentum(5) baseline on the same days -> DM on directional (0/1-correct) loss
            sb, rb, mb = pair(signals, closes_by_tk, sig_key, h, baseline_k=5)
            loss_crowd = (np.sign(sb) != np.sign(rb)).astype(float)
            loss_base = (np.sign(mb) != np.sign(rb)).astype(float)
            dm, dmp = diebold_mariano(loss_crowd, loss_base, h=h)
            results[f"{sig_key}_h{h}"] = {
                "n_ticker_days": int(len(s)), "IC": round(ic, 4),
                "IC_ci95": [round(lo, 4), round(hi, 4)], "hit_rate": round(hr, 4),
                "strategy_SR": round(sr, 3),
                "DM_vs_mom5": round(dm, 3), "DM_p": round(dmp, 4)}

    sr_var = float(np.var(per_trial_sr)) if len(per_trial_sr) > 1 else 0.0
    for key, res in results.items():
        h = int(key.split("_h")[1])
        s, r, _ = pair(signals, closes_by_tk, key.rsplit("_h", 1)[0], h)
        sr, skew, kurt, nobs = strategy_sharpe(s, r)
        res["DSR"] = round(deflated_sharpe(sr, nobs, skew, kurt, args.n_trials, sr_var), 4)

    write_report(args.run_id, args.n_trials, results)
    print("P5_STATS", json.dumps(results, indent=2), flush=True)
    return 0


def write_report(run_id: str, n_trials: int, results: dict) -> None:
    lines = [
        f"# P5_STATS — RQ3 prediction statistics ({run_id})", "",
        "Generated (UTC): 2026-07-05", "",
        "Crowd flow-imbalance signal vs realized forward real returns on the G1-frozen OOS-10 "
        "universe (alias arm). Estimators: agorasim.evals.prediction. DSR uses the registered "
        f"trial count n_trials={n_trials} (docs/TRIALS.md, D-11).", "",
        "| signal × horizon | ticker-days | IC | IC 95% CI | hit rate | strat SR | DM vs mom5 (p) | DSR |",
        "|---|---:|---:|---|---:|---:|---:|---:|",
    ]
    for k, v in results.items():
        lines.append(f"| {k} | {v['n_ticker_days']} | {v['IC']} | "
                     f"[{v['IC_ci95'][0]}, {v['IC_ci95'][1]}] | {v['hit_rate']} | "
                     f"{v['strategy_SR']} | {v['DM_vs_mom5']} ({v['DM_p']}) | {v['DSR']} |")
    lines += ["", "IC = Spearman rank corr(signal_t, forward_return). hit rate on nonzero-signal "
              "days. DM > 0 favors the crowd over the 5-day momentum baseline (positive = lower "
              "directional loss); p is two-sided. DSR = P(true SR > 0) deflated for 4 trials.", "",
              "Interpretation is written after inspecting the numbers; a near-zero IC / DSR < 0.5 "
              "is the expected honest outcome for weak small models on hard-to-trade small caps "
              "(PLAN §1) and is reported as such, not buried."]
    Path("docs/P5_STATS.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
