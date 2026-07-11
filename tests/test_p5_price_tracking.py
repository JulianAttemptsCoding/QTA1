import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p5_price_tracking.py"
SPEC = importlib.util.spec_from_file_location("p5_price_tracking", SCRIPT)
tracker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = tracker
SPEC.loader.exec_module(tracker)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_classifies_calibration_and_oos_runs():
    calib = tracker.classify_run("calib-2019-g1-blnk-named-v1")
    oos = tracker.classify_run("oos-2025-g1-scaling-nvni-alias-n300-v1")

    assert calib["split"] == "calib-2019"
    assert calib["is_oos"] is False
    assert oos["split"] == "oos-2025-followups"
    assert oos["is_oos"] is True
    assert oos["config"] == "scaling_n300"


def test_collects_metrics_and_writes_svg(tmp_path):
    rows = []
    for idx, day in enumerate(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"]):
        rows.append({
            "run_id": "oos-2025-g1-tlry-alias-v1",
            "ticker": "TLRY",
            "arm": "alias",
            "day": day,
            "real_close": [10.0, 11.0, 12.0, 11.5][idx],
            "auction_price": [10.0, 10.5, 11.8, 12.1][idx],
            "next_day_return": [0.10, 0.09, -0.04, 0.00][idx],
        })
    write_jsonl(tmp_path / "runs" / "p4" / "main" / "one" / "sim.jsonl", rows)

    out_dir = tmp_path / "figures"
    metrics = tracker.collect(tmp_path / "runs", out_dir, cost_bps=25)
    report = tracker.render_report(metrics, cost_bps=25)

    assert len(metrics) == 1
    assert metrics[0]["is_oos"] is True
    assert "oos-2025-main" in report
    assert Path(metrics[0]["figure"]).exists()
    assert "sim auction price" in Path(metrics[0]["figure"]).read_text(encoding="utf-8")
