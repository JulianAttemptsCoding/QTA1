"""Evaluate the P4 G4 budget checkpoint from archived worker summaries."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def load_summaries(input_dir: Path) -> list[dict[str, Any]]:
    summaries = []
    for path in sorted(input_dir.rglob("worker_summary.json")):
        summary = json.loads(path.read_text(encoding="utf-8"))
        summary["_path"] = str(path)
        summaries.append(summary)
    if not summaries:
        raise FileNotFoundError(f"No worker_summary.json files found under {input_dir}")
    return summaries


def evaluate_g4(
    summaries: Iterable[dict[str, Any]],
    *,
    hourly_rate: float = 0.30,
    g0_decisions_per_hour: float = 4747.0,
    threshold: float = 0.30,
) -> dict[str, Any]:
    rows = list(summaries)
    requests = sum(int(row["n_requests"]) for row in rows)
    outputs = sum(int(row["n_outputs"]) for row in rows)
    elapsed_seconds = sum(float(row["elapsed_seconds"]) for row in rows)
    if requests <= 0 or elapsed_seconds <= 0:
        raise ValueError("G4 requires positive requests and elapsed time")
    baseline_cost_per_decision = hourly_rate / g0_decisions_per_hour
    observed_cost = elapsed_seconds / 3600.0 * hourly_rate
    observed_cost_per_decision = observed_cost / requests
    overrun_fraction = observed_cost_per_decision / baseline_cost_per_decision - 1.0
    complete = outputs == requests
    pause = overrun_fraction > threshold
    return {
        "jobs": len(rows),
        "requests": requests,
        "outputs": outputs,
        "complete": complete,
        "elapsed_hours": elapsed_seconds / 3600.0,
        "hourly_rate_usd": hourly_rate,
        "estimated_cost_usd": observed_cost,
        "g0_decisions_per_hour": g0_decisions_per_hour,
        "baseline_cost_per_decision_usd": baseline_cost_per_decision,
        "observed_cost_per_decision_usd": observed_cost_per_decision,
        "overrun_fraction": overrun_fraction,
        "threshold": threshold,
        "decision": "PAUSE_REPLAN" if pause else "PASS",
    }


def render_report(result: dict[str, Any]) -> str:
    return "\n".join([
        "# G4 P4 Budget Checkpoint",
        "",
        f"- Decision: **{result['decision']}**",
        f"- Completed outputs: `{result['outputs']:,}` / `{result['requests']:,}`.",
        f"- Aggregate worker time: `{result['elapsed_hours']:.3f}` hours.",
        f"- Estimated checkpoint spend: `${result['estimated_cost_usd']:.2f}`.",
        f"- G0 baseline cost/decision: `${result['baseline_cost_per_decision_usd']:.8f}`.",
        f"- P4 observed cost/decision: `${result['observed_cost_per_decision_usd']:.8f}`.",
        f"- Relative overrun: `{result['overrun_fraction'] * 100:.1f}%` "
        f"(pause threshold `{result['threshold'] * 100:.0f}%`).",
        "",
        "The remaining P4 main jobs may proceed only when the decision is `PASS`; "
        "a `PAUSE_REPLAN` result must be documented before additional inference.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("runs/p4/g4"))
    parser.add_argument("--output", type=Path, default=Path("docs/G4_REPORT.md"))
    parser.add_argument("--hourly-rate", type=float, default=0.30)
    parser.add_argument("--g0-decisions-per-hour", type=float, default=4747.0)
    parser.add_argument("--threshold", type=float, default=0.30)
    args = parser.parse_args()

    result = evaluate_g4(
        load_summaries(args.input_dir),
        hourly_rate=args.hourly_rate,
        g0_decisions_per_hour=args.g0_decisions_per_hour,
        threshold=args.threshold,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(result), encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 2 if result["decision"] == "PAUSE_REPLAN" else 0


if __name__ == "__main__":
    raise SystemExit(main())
