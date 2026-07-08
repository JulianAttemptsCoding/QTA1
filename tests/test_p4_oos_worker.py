import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p4_oos_worker.py"
SPEC = importlib.util.spec_from_file_location("p4_oos_worker", SCRIPT)
p4_worker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = p4_worker
SPEC.loader.exec_module(p4_worker)


def test_add_prediction_targets_uses_only_next_close_and_past_momentum():
    rows = [
        {"real_close": 10.0},
        {"real_close": 11.0},
        {"real_close": 9.9},
    ]

    result = p4_worker.add_prediction_targets(rows)

    assert result[0]["next_day_return"] == pytest.approx(0.1)
    assert result[1]["next_day_return"] == pytest.approx(-0.1)
    assert result[2]["next_day_return"] is None
    assert result[0]["momentum_1d"] is None
    assert result[1]["momentum_1d"] == pytest.approx(0.1)


def test_add_model_flows_keeps_model_baselines_separate():
    requests = [
        {"request_id": "r1", "day": "2025-01-02", "model_id": "model-a"},
        {"request_id": "r2", "day": "2025-01-02", "model_id": "model-b"},
    ]
    outputs = [
        {
            "request_id": "r1",
            "decision": {
                "action": "buy",
                "order_type": "market",
                "qty": 10,
                "limit_price": 10.0,
                "confidence": 1.0,
                "horizon_days": 1,
            },
        },
        {
            "request_id": "r2",
            "decision": {
                "action": "sell",
                "order_type": "market",
                "qty": 10,
                "limit_price": 10.0,
                "confidence": 1.0,
                "horizon_days": 1,
            },
        },
    ]
    rows = [{"day": "2025-01-02"}]

    result = p4_worker.add_model_flows(rows, requests, outputs)

    assert result[0]["model_flow_imbalance"]["model-a"] > 0
    assert result[0]["model_flow_imbalance"]["model-b"] < 0
