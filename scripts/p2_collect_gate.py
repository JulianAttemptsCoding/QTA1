"""Collect P2 real-model gate JSON files into docs/G2_REPORT.md."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FAMILY_BY_MODEL = {
    "Qwen/Qwen2.5-1.5B-Instruct": "qwen2_5",
    "Qwen/Qwen2.5-3B-Instruct": "qwen2_5",
    "microsoft/Phi-3.5-mini-instruct": "phi3_5",
    "HuggingFaceTB/SmolLM2-1.7B-Instruct": "smollm2",
}


def load_rows(input_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(path.read_text()) for path in sorted(input_dir.glob("*.json"))]


def surviving_models(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        if row.get("passes_valid_json") and row.get("passes_contamination"):
            out.append(row)
    return out


def gate_status(rows: list[dict[str, Any]]) -> tuple[str, str]:
    survivors = surviving_models(rows)
    families = {FAMILY_BY_MODEL.get(row["model_id"], row["model_id"]) for row in survivors}
    if len(families) < 2:
        return "FAIL", f"Only {len(families)} surviving model families; G2 requires at least 2."
    return "PASS", f"{len(survivors)} models across {len(families)} families survived G2."


def render_report(rows: list[dict[str, Any]]) -> str:
    status, detail = gate_status(rows)
    lines = [
        "# G2 Real-Model Gate Report",
        "",
        f"- Overall: **{status}**",
        f"- Gate detail: {detail}",
        "- Measurement location: Vertex AI custom jobs on n1-standard-8 + 1x NVIDIA_TESLA_T4.",
        "- Model weights source: GCS cache populated by Vertex model-cache jobs; no local weight downloads or inference.",
        "- Snapshot source: `gs://project-82d97cf9-5889-43a4-850-agorasim/agorasim/snapshots/g1/manifest.json`.",
        "",
        "| Model | Family | Smoke prompts | Valid JSON | Max probe non-UNKNOWN | Survives |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in sorted(rows, key=lambda r: r["model_id"]):
        family = FAMILY_BY_MODEL.get(row["model_id"], row["model_id"])
        valid = float(row["smoke"]["valid_json_rate"])
        recall = float(row["contamination"]["max_non_unknown_rate"])
        survives = row.get("passes_valid_json") and row.get("passes_contamination")
        lines.append(
            f"| {row['model_id']} | {family} | {int(row['smoke']['n_prompts'])} | "
            f"{valid:.3f} | {recall:.3f} | {survives} |"
        )
    lines += [
        "",
        "## Smoke Path Summary",
        "",
        "| Model | Days | First price | Last price | Mean abs imbalance |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in sorted(rows, key=lambda r: r["model_id"]):
        path = row["smoke"].get("path") or []
        first = float(path[0]["auction_price"]) if path else 0.0
        last = float(path[-1]["auction_price"]) if path else 0.0
        mean_abs = sum(abs(float(day["flow_imbalance"])) for day in path) / len(path) if path else 0.0
        lines.append(f"| {row['model_id']} | {len(path)} | {first:.2f} | {last:.2f} | {mean_abs:.3f} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("docs/G2_REPORT.md"))
    args = parser.parse_args()
    rows = load_rows(args.input_dir)
    report = render_report(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report)
    status, detail = gate_status(rows)
    print(f"{status}: {detail}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
