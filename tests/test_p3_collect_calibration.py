import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p3_collect_calibration.py"
SPEC = importlib.util.spec_from_file_location("p3_collect_calibration", SCRIPT)
p3_collect = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = p3_collect
SPEC.loader.exec_module(p3_collect)


def write_jsonl(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def test_collect_reports_from_sim_rows(tmp_path):
    rows = []
    for arm in ["named", "alias"]:
        for idx, day in enumerate(["2019-07-01", "2019-07-02", "2019-07-03", "2019-07-05"]):
            rows.append({
                "run_id": f"run-{arm}",
                "ticker": "IIPR",
                "arm": arm,
                "day": day,
                "flow_imbalance": [1, -1, 1, -1][idx],
                "robintrack_d_holders": [5, -2, 3, -1][idx],
                "auction_price": [10, 11, 10.5, 11.2][idx],
                "auction_volume": [10, 20, 30, 40][idx],
                "decision_entropy": 0.8,
            })
    write_jsonl(tmp_path / "runs" / "run" / "sim.jsonl", rows)
    df = p3_collect.load_sim_rows(tmp_path / "runs")

    rq1 = p3_collect.rq1_rows(df)
    rq2 = p3_collect.rq2_rows(df)

    assert len(rq1) == 2
    pooled = [row for row in rq2 if row["scope"] == "pooled"]
    assert len(pooled) == 2
    assert all(row["sign_agreement"] == 1.0 for row in pooled)
    assert "does not fire" in p3_collect.g3_gate_summary(rq1, rq2)


def test_markdown_table_escapes_pipe_characters():
    lines = p3_collect.markdown_table(
        [{"metric": "left|right"}],
        [("ACF |r| lag1", "metric")],
    )

    assert lines[0] == r"| ACF \|r\| lag1 |"
    assert lines[2] == r"| left\|right |"
