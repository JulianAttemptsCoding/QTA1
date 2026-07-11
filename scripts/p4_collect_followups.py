"""Collect P4 scaling and ablation follow-up artifacts."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from p4_collect_oos import metric_values, table


RUN_RE = re.compile(
    r"^oos-2025-g1-(?P<kind>scaling|news_off|personas_off)-"
    r"(?P<ticker>[a-z]+)-(?P<arm>[a-z]+)-n(?P<n_agents>\d+)-v(?P<version>\d+)$"
)
EXPECTED_DAYS = 60
EXPECTED_SCALING = (50, 100, 300, 1000)
EXPECTED_TICKERS = ("NVNI", "TLRY")
CANCELLED_PARTIAL_OUTPUTS = {
    ("scaling", "NVNI", 1000): 10752,
    ("scaling", "TLRY", 1000): 1408,
}
SIGNALS = {
    "weighted": "flow_imbalance",
    "unweighted": "flow_imbalance_unweighted",
}


@dataclass(frozen=True)
class RunRecord:
    path: Path
    kind: str
    ticker: str
    n_agents: int
    status: str
    expected_outputs: int
    outputs: int
    requests: int
    sim_days: int

    @property
    def config(self) -> str:
        if self.kind == "scaling":
            return f"scaling_n{self.n_agents}"
        return f"{self.kind}_n{self.n_agents}"


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def discover_runs(input_dir: Path) -> list[RunRecord]:
    records: list[RunRecord] = []
    for path in sorted(input_dir.rglob("sim.jsonl")):
        run_dir = path.parent
        match = RUN_RE.match(run_dir.name)
        if not match:
            continue
        n_agents = int(match.group("n_agents"))
        expected = n_agents * EXPECTED_DAYS
        outputs = line_count(run_dir / "outputs.jsonl")
        requests = line_count(run_dir / "requests.jsonl")
        sim_days = line_count(run_dir / "sim.jsonl")
        status = "complete" if (
            outputs == expected and requests == expected and sim_days == EXPECTED_DAYS
        ) else "partial"
        records.append(RunRecord(
            path=run_dir,
            kind=match.group("kind"),
            ticker=match.group("ticker").upper(),
            n_agents=n_agents,
            status=status,
            expected_outputs=expected,
            outputs=outputs,
            requests=requests,
            sim_days=sim_days,
        ))
    return records


def missing_rows(records: list[RunRecord]) -> list[dict[str, Any]]:
    present = {(record.kind, record.ticker, record.n_agents) for record in records}
    rows: list[dict[str, Any]] = []
    for ticker in EXPECTED_TICKERS:
        for n_agents in EXPECTED_SCALING:
            if ("scaling", ticker, n_agents) not in present:
                partial_outputs = CANCELLED_PARTIAL_OUTPUTS.get(("scaling", ticker, n_agents), 0)
                rows.append({
                    "config": f"scaling_n{n_agents}",
                    "ticker": ticker,
                    "status": "budget_cancelled_partial" if partial_outputs else "missing_or_cancelled",
                    "outputs": partial_outputs,
                    "expected": n_agents * EXPECTED_DAYS,
                    "sim_days": 0,
                })
        for kind in ("news_off", "personas_off"):
            if (kind, ticker, 100) not in present:
                rows.append({
                    "config": f"{kind}_n100",
                    "ticker": ticker,
                    "status": "missing_or_cancelled",
                    "outputs": 0,
                    "expected": 100 * EXPECTED_DAYS,
                    "sim_days": 0,
                })
    return rows


def load_complete_frame(records: list[RunRecord]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in records:
        if record.status != "complete":
            continue
        for row in iter_jsonl(record.path / "sim.jsonl"):
            row["experiment_kind"] = record.kind
            row["experiment_config"] = record.config
            row["experiment_n_agents"] = record.n_agents
            rows.append(row)
    if not rows:
        raise FileNotFoundError("No complete follow-up sim.jsonl files found")
    frame = pd.DataFrame(rows)
    frame["day"] = pd.to_datetime(frame["day"])
    return frame.sort_values(["experiment_config", "ticker", "day"]).reset_index(drop=True)


def metric_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (config, ticker), group in frame.groupby(["experiment_config", "ticker"], sort=True):
        for weighting, column in SIGNALS.items():
            values = metric_values(group, column)
            rows.append({
                "scope": ticker,
                "config": config,
                "weighting": weighting,
                "days": group["day"].nunique(),
                "entropy": float(group["decision_entropy"].mean()),
                **values,
            })
    for config, group in frame.groupby("experiment_config", sort=True):
        for weighting, column in SIGNALS.items():
            values = metric_values(group, column)
            rows.append({
                "scope": "ALL",
                "config": config,
                "weighting": weighting,
                "days": group["day"].nunique(),
                "entropy": float(group["decision_entropy"].mean()),
                **values,
            })
    return rows


def ablation_delta_rows(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {
        (row["scope"], row["config"], row["weighting"]): row
        for row in metrics
    }
    rows: list[dict[str, Any]] = []
    for scope in ["NVNI", "TLRY", "ALL"]:
        for weighting in SIGNALS:
            baseline = lookup.get((scope, "scaling_n100", weighting))
            if not baseline:
                continue
            for config in ("news_off_n100", "personas_off_n100"):
                row = lookup.get((scope, config, weighting))
                if not row:
                    continue
                rows.append({
                    "scope": scope,
                    "ablation": config,
                    "weighting": weighting,
                    "ic_delta": row["ic"] - baseline["ic"],
                    "hit_delta": row["hit_rate"] - baseline["hit_rate"],
                    "sharpe_delta": row["sharpe"] - baseline["sharpe"],
                    "entropy_delta": row["entropy"] - baseline["entropy"],
                })
    return rows


def fmt(value: Any) -> str:
    if isinstance(value, float) and not math.isfinite(value):
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render_report(records: list[RunRecord], frame: pd.DataFrame) -> str:
    coverage = [
        {
            "config": record.config,
            "ticker": record.ticker,
            "status": record.status,
            "outputs": record.outputs,
            "expected": record.expected_outputs,
            "sim_days": record.sim_days,
        }
        for record in records
    ]
    coverage.extend(missing_rows(records))
    coverage = sorted(coverage, key=lambda row: (row["config"], row["ticker"]))
    metrics = metric_rows(frame)
    scaling = [row for row in metrics if row["config"].startswith("scaling_")]
    ablations = [row for row in metrics if not row["config"].startswith("scaling_")]
    deltas = ablation_delta_rows(metrics)

    lines = [
        "# P4 Follow-Up Report",
        "",
        "- Source: completed A-402/A-403 Vertex artifacts only.",
        "- Incomplete or budget-cancelled shards are listed in coverage and excluded from metrics.",
        "- Scaling N1000 was budget-cancelled before completion; preserved partial outputs are reported for audit only, not interpreted as results.",
        "",
        "## Coverage",
        "",
    ]
    lines.extend(table(coverage, [
        ("Config", "config"), ("Ticker", "ticker"), ("Status", "status"),
        ("Outputs", "outputs"), ("Expected", "expected"), ("Sim days", "sim_days"),
    ]))
    lines += ["", "## Scaling Metrics", ""]
    lines.extend(table(scaling, [
        ("Scope", "scope"), ("Config", "config"), ("Weighting", "weighting"),
        ("Days", "days"), ("N", "n"), ("IC", "ic"), ("Hit", "hit_rate"),
        ("Sharpe", "sharpe"), ("Entropy", "entropy"),
    ]))
    lines += ["", "## Ablation Metrics", ""]
    lines.extend(table(ablations, [
        ("Scope", "scope"), ("Config", "config"), ("Weighting", "weighting"),
        ("Days", "days"), ("N", "n"), ("IC", "ic"), ("Hit", "hit_rate"),
        ("Sharpe", "sharpe"), ("Entropy", "entropy"),
    ]))
    lines += ["", "## Ablation Delta vs Scaling N100", ""]
    lines.extend(table(deltas, [
        ("Scope", "scope"), ("Ablation", "ablation"), ("Weighting", "weighting"),
        ("IC delta", "ic_delta"), ("Hit delta", "hit_delta"),
        ("Sharpe delta", "sharpe_delta"), ("Entropy delta", "entropy_delta"),
    ]))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("runs/p4"))
    parser.add_argument("--output", type=Path, default=Path("docs/P4_FOLLOWUP_REPORT.md"))
    args = parser.parse_args()

    records = discover_runs(args.input_dir)
    frame = load_complete_frame(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(records, frame), encoding="utf-8")
    print(json.dumps({
        "complete_runs": sum(record.status == "complete" for record in records),
        "partial_runs": sum(record.status != "complete" for record in records),
        "rows": len(frame),
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
