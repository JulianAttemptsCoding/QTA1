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


def test_build_requests_ablation_modes(monkeypatch):
    bars = [
        {"t": "2025-01-02T00:00:00Z", "o": 10, "h": 11, "l": 9, "c": 10, "v": 100},
    ]
    news = [
        {"created_at": "2025-01-02T00:00:00Z", "headline": "Ticker jumps"},
    ]

    def fake_read(uri):
        return news if uri.endswith("news.jsonl") else bars

    monkeypatch.setattr(p4_worker, "read_jsonl_gcs", fake_read, raising=False)
    monkeypatch.setattr(
        sys.modules["p3_calibration_worker"],
        "read_jsonl_gcs",
        fake_read,
    )
    requests = p4_worker.build_requests(
        manifest={
            "files": [
                {
                    "path": "data/snapshots/g1/oos/TEST/bars_1d.jsonl",
                    "gcs_uri": "gs://bucket/oos/TEST/bars_1d.jsonl",
                },
                {
                    "path": "data/snapshots/g1/oos/TEST/news.jsonl",
                    "gcs_uri": "gs://bucket/oos/TEST/news.jsonl",
                },
            ]
        },
        run_id="run",
        ticker="TEST",
        arm="named",
        n_agents=2,
        persona_seed=1,
        start="2025-01-02",
        end="2025-01-02",
        model_ids=["model"],
        temperatures=[0.7],
        run_salt="salt",
        snapshot_kind="oos",
        news_off=True,
        personas_off=True,
    )

    assert len(requests) == 2
    assert all("Ticker jumps" not in row["prompt"] for row in requests)
    assert all("two-year hobbyist" in row["prompt"] for row in requests)
