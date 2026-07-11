import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p4_collect_followups.py"
SPEC = importlib.util.spec_from_file_location("p4_collect_followups", SCRIPT)
collector = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = collector
SPEC.loader.exec_module(collector)


def write_run(root: Path, run_id: str, n_agents: int, days: int = 60) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    requests = []
    outputs = []
    sim = []
    for day in range(days):
        target = 0.01 if day % 2 == 0 else -0.01
        sim.append({
            "ticker": "NVNI",
            "day": f"2025-01-{(day % 28) + 1:02d}",
            "next_day_return": target,
            "flow_imbalance": target,
            "flow_imbalance_unweighted": target,
            "decision_entropy": 1.0,
        })
        for agent in range(n_agents):
            requests.append({"request_id": f"{day}-{agent}"})
            outputs.append({"request_id": f"{day}-{agent}", "raw_text": "{}"})
    (run_dir / "requests.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in requests),
        encoding="utf-8",
    )
    (run_dir / "outputs.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in outputs),
        encoding="utf-8",
    )
    (run_dir / "sim.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in sim),
        encoding="utf-8",
    )


def test_discovers_complete_and_partial_runs(tmp_path):
    write_run(
        tmp_path,
        "oos-2025-g1-scaling-nvni-alias-n50-v1",
        n_agents=50,
        days=60,
    )
    write_run(
        tmp_path,
        "oos-2025-g1-scaling-nvni-alias-n1000-v1",
        n_agents=1000,
        days=1,
    )

    records = collector.discover_runs(tmp_path)

    statuses = {record.n_agents: record.status for record in records}
    assert statuses[50] == "complete"
    assert statuses[1000] == "partial"


def test_report_excludes_partial_metrics_and_lists_missing(tmp_path):
    write_run(
        tmp_path,
        "oos-2025-g1-scaling-nvni-alias-n50-v1",
        n_agents=50,
        days=60,
    )
    write_run(
        tmp_path,
        "oos-2025-g1-scaling-nvni-alias-n1000-v1",
        n_agents=1000,
        days=1,
    )
    records = collector.discover_runs(tmp_path)
    frame = collector.load_complete_frame(records)
    report = collector.render_report(records, frame)

    assert "scaling_n50" in report
    assert "scaling_n1000 | NVNI | partial" in report
    assert "scaling_n1000 | TLRY | missing_or_cancelled" in report
    assert frame["experiment_n_agents"].unique().tolist() == [50]
