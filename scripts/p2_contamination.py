"""P2 / A-202 — contamination C-2 recall probes -> per (model, ticker) exclusion matrix.

For each OOS ticker, ask the model (from memory, NO data provided) for the closing price on
K post-cutoff dates, in BOTH the named arm (real ticker) and the alias arm (stable random
name). Recall = fraction of answers within `--tol` of the real snapshot close.

Signals:
- named_recall > `--max-recall` (default 0.10)  -> the model has memorized post-cutoff facts
  for this ticker (C-2 fail) -> EXCLUDE (model, ticker) from named claims; use the alias arm.
- gap = named_recall - alias_recall              -> memorization attributable to the ticker
  identity (a large positive gap is the Glasserman-Lin contamination fingerprint, C-3).

Runs on the Vertex worker image (GPU). Free-form generation (we WANT to see UNKNOWN vs a
recalled number), temperature 0 for deterministic recall.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from agorasim.agents.prompt_builder import load_template, render
from agorasim.agents.sim_prompts import read_jsonl, stable_alias
from agorasim.evals.contamination import ProbeResult, extract_price, is_recall, model_passes
from agorasim.infra.gcs import download_prefix, upload_file


def sanitize(s: str) -> str:
    return s.replace("/", "__")


def sample_date_closes(bars: list[dict], k: int) -> list[tuple[str, float]]:
    """K post-cutoff (date, close) pairs evenly spread across the snapshot window."""
    rows = sorted(({"d": b["t"][:10], "c": float(b["c"])} for b in bars), key=lambda r: r["d"])
    if not rows:
        return []
    if len(rows) <= k:
        return [(r["d"], r["c"]) for r in rows]
    step = len(rows) / k
    return [(rows[int(i * step)]["d"], rows[int(i * step)]["c"]) for i in range(k)]


def build_probes(ticker: str, bars: list[dict], k: int) -> list[dict]:
    tmpl = load_template("contamination_probe.j2")
    dates = sample_date_closes(bars, k)
    probes = []
    for arm, name in (("named", f"{ticker} (US-listed stock, ticker {ticker})"),
                      ("alias", stable_alias(ticker))):
        for date, close in dates:
            q = (f"What was the approximate closing share price in US dollars on {date}? "
                 f"Reply with just a number, or UNKNOWN.")
            probes.append({"arm": arm, "ticker": ticker, "date": date, "actual": close,
                           "prompt": render(tmpl, name_or_alias=name, probe_question=q)})
    return probes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--tickers", required=True, help="comma-separated OOS tickers")
    ap.add_argument("--universe", default="oos")
    ap.add_argument("--n-dates", type=int, default=10)
    ap.add_argument("--tol", type=float, default=0.15)
    ap.add_argument("--max-recall", type=float, default=0.10)
    args = ap.parse_args()

    from vllm import LLM, SamplingParams  # Vertex worker only

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    all_probes: list[dict] = []
    for tk in tickers:
        snap = Path(f"/tmp/snap/{args.universe}/{tk}")
        download_prefix(f"{args.base}/snapshots/g1/{args.universe}/{tk}", str(snap))
        bars = read_jsonl(snap / "bars_1d.jsonl")
        all_probes.extend(build_probes(tk, bars, args.n_dates))

    llm = LLM(model=args.model, dtype="half", gpu_memory_utilization=0.90,
              max_model_len=4096, enforce_eager=True)
    sp = SamplingParams(temperature=0.0, max_tokens=48)
    outs = llm.generate([p["prompt"] for p in all_probes], sp)
    for p, o in zip(all_probes, outs):
        ans = o.outputs[0].text
        p["answer"] = ans[:120]
        p["recalled"] = is_recall(extract_price(ans), p["actual"], args.tol)

    matrix = {}
    for tk in tickers:
        row = {}
        for arm in ("named", "alias"):
            sel = [p for p in all_probes if p["ticker"] == tk and p["arm"] == arm]
            n_correct = sum(1 for p in sel if p["recalled"])
            row[arm] = ProbeResult(args.model, tk, len(sel), n_correct).recall_rate
        excluded = not model_passes(ProbeResult(args.model, tk, args.n_dates,
                                                round(row["named"] * args.n_dates)), args.max_recall)
        matrix[tk] = {"named_recall": round(row["named"], 4),
                      "alias_recall": round(row["alias"], 4),
                      "gap": round(row["named"] - row["alias"], 4),
                      "excluded_named": excluded}

    rec = {"model": args.model, "universe": args.universe, "n_dates": args.n_dates,
           "tol": args.tol, "max_recall": args.max_recall, "matrix": matrix,
           "any_excluded": any(v["excluded_named"] for v in matrix.values())}
    print("CONTAMINATION_RESULT", json.dumps(rec), flush=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(rec, tf)
        tmp = tf.name
    upload_file(tmp, f"{args.base}/runs/g2_contamination/{sanitize(args.model)}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
