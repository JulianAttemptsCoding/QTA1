import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p3_calibration_worker.py"
SPEC = importlib.util.spec_from_file_location("p3_calibration_worker", SCRIPT)
p3_worker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = p3_worker
SPEC.loader.exec_module(p3_worker)


def test_alias_symbol_and_scrub_are_stable():
    alias = p3_worker.alias_symbol("IIPR", "calib-2019-v1")
    assert alias.startswith("X")
    assert alias == p3_worker.alias_symbol("IIPR", "calib-2019-v1")
    scrubbed = p3_worker.scrub_alias_text("IIPR rose on NASDAQ after IIPR Holdings news.", "IIPR", alias, f"{alias} Holdings")
    assert "IIPR" not in scrubbed
    assert "NASDAQ" not in scrubbed
    assert alias in scrubbed


def test_summarize_simulation_includes_robintrack_and_entropy():
    requests = [
        {"request_id": "r1", "run_id": "run", "ticker": "IIPR", "arm": "named", "day": "2019-07-01", "last_price": 10.0},
        {"request_id": "r2", "run_id": "run", "ticker": "IIPR", "arm": "named", "day": "2019-07-01", "last_price": 10.0},
        {"request_id": "r3", "run_id": "run", "ticker": "IIPR", "arm": "named", "day": "2019-07-02", "last_price": 11.0},
    ]
    output_rows = [
        {
            "request_id": "r1",
            "decision": {"action": "buy", "order_type": "market", "qty": 10, "limit_price": 10, "confidence": 0.8, "horizon_days": 1},
        },
        {
            "request_id": "r2",
            "decision": {"action": "sell", "order_type": "market", "qty": 5, "limit_price": 10, "confidence": 0.4, "horizon_days": 1},
        },
        {
            "request_id": "r3",
            "decision": {"action": "hold", "order_type": "market", "qty": 0, "limit_price": 11, "confidence": 0.5, "horizon_days": 1},
        },
    ]
    robintrack = {
        "2019-07-01": {"users_holding": 100.0, "d_holders": 3.0},
        "2019-07-02": {"users_holding": 98.0, "d_holders": -2.0},
    }

    rows = p3_worker.summarize_simulation(requests, output_rows, robintrack)

    assert rows[0]["run_id"] == "run"
    assert rows[0]["ticker"] == "IIPR"
    assert rows[0]["arm"] == "named"
    assert rows[0]["robintrack_d_holders"] == 3.0
    assert rows[0]["decision_entropy"] == 1.0
    assert rows[1]["hold_count"] == 1
