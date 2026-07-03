"""Aggregate Vertex throughput JSON outputs into docs/G0_THROUGHPUT.md."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_results(input_dir: Path) -> list[dict[str, Any]]:
    return sorted(
        (json.loads(path.read_text()) for path in input_dir.glob("*.json")),
        key=lambda row: row["model_id"],
    )


def gate_status(rows: list[dict[str, Any]]) -> tuple[str, str]:
    if not rows:
        return "FAIL", "No throughput result JSON files were found."
    best = max(float(row.get("decisions_per_hour", 0.0)) for row in rows)
    min_valid = min(float(row.get("valid_json_rate", 0.0)) for row in rows)
    if best < 2000:
        return "FAIL", f"Best measured throughput {best:.0f}/hour is below 2,000/hour."
    if min_valid < 0.90:
        return "FAIL", f"Lowest valid-JSON rate {min_valid:.3f} is below 0.900."
    return "PASS", f"Best measured throughput {best:.0f}/hour; lowest valid-JSON rate {min_valid:.3f}."


def render_report(rows: list[dict[str, Any]]) -> str:
    status, detail = gate_status(rows)
    lines = [
        "# G0 Throughput Gate Report",
        "",
        f"- Overall: **{status}**",
        f"- Gate detail: {detail}",
        "- Measurement location: Vertex AI custom jobs on n1-standard-8 + 1x NVIDIA_TESLA_T4.",
        "- Model weights source: GCS cache populated by the Vertex model-cache job; no local weight downloads or inference.",
        "",
        "| Model | Prompts | Elapsed seconds | Decisions/hour | Valid JSON rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['model_id']} | {int(row['n_prompts'])} | "
            f"{float(row['elapsed_seconds']):.2f} | {float(row['decisions_per_hour']):.0f} | "
            f"{float(row['valid_json_rate']):.3f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="runs/g0-throughput")
    parser.add_argument("--out", default="docs/G0_THROUGHPUT.md")
    args = parser.parse_args()
    rows = load_results(Path(args.input_dir))
    Path(args.out).write_text(render_report(rows))
    status, detail = gate_status(rows)
    print(f"{status}: {detail}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
