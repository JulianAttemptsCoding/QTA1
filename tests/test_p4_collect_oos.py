import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p4_collect_oos.py"
SPEC = importlib.util.spec_from_file_location("p4_collect_oos", SCRIPT)
collector = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = collector
SPEC.loader.exec_module(collector)


def synthetic_frame(n: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    returns = rng.normal(0, 0.02, n)
    close = 10 * np.cumprod(1 + returns)
    target = np.r_[returns[1:], np.nan]
    momentum_1d = np.r_[np.nan, returns[1:]]
    frame = pd.DataFrame({
        "ticker": "TEST",
        "day": pd.date_range("2025-01-02", periods=n, freq="B"),
        "real_close": close,
        "next_day_return": target,
        "flow_imbalance": np.nan_to_num(target, nan=0.0),
        "flow_imbalance_unweighted": np.nan_to_num(target, nan=0.0),
        "decision_entropy": 1.2,
        "single_model_signal": rng.normal(0, 1, n),
        "momentum_1d": momentum_1d,
        "momentum_5d": pd.Series(close).pct_change(5),
        "momentum_20d": pd.Series(close).pct_change(20),
        "bar_range": 0.03,
        "bar_volume": np.linspace(100, 200, n) + rng.normal(0, 5, n),
    })
    frame["volume_z20"] = (
        (frame["bar_volume"] - frame["bar_volume"].rolling(20, min_periods=5).mean())
        / frame["bar_volume"].rolling(20, min_periods=5).std(ddof=0)
    )
    return frame


def test_single_model_signal_prefers_qwen():
    flows = {
        "microsoft/Phi-3.5-mini-instruct": -0.4,
        "Qwen/Qwen2.5-1.5B-Instruct": 0.3,
    }
    assert collector.single_model_signal(flows) == 0.3


def test_walk_forward_baselines_leave_warmup_empty():
    frame = synthetic_frame()
    collector.add_ar1_signal(frame, min_train=10)
    collector.add_logistic_signal(frame, min_train=20)

    assert frame["ar1_signal"].iloc[:10].isna().all()
    assert frame["ar1_signal"].notna().sum() > 20
    assert frame["logistic_signal"].iloc[:20].isna().all()
    assert frame["logistic_signal"].notna().sum() > 10


def test_metrics_and_dm_reward_perfect_crowd_signal():
    frame = synthetic_frame()
    collector.add_ar1_signal(frame, min_train=10)
    collector.add_logistic_signal(frame, min_train=20)

    metrics = collector.metric_values(frame, "flow_imbalance")
    dm = collector.dm_rows(frame)

    assert metrics["ic"] > 0.99
    assert metrics["hit_rate"] == 1.0
    single = next(row for row in dm if row["baseline"] == "single_qwen")
    assert single["crowd_error"] < single["baseline_error"]
    assert single["dm"] < 0


def test_pooled_strategy_returns_average_tickers_by_day():
    frame = synthetic_frame(30)
    second = frame.copy()
    second["ticker"] = "OTHER"
    second["next_day_return"] *= -1
    combined = pd.concat([frame, second], ignore_index=True)

    strategy = collector.strategy_returns(combined, "flow_imbalance")

    assert len(strategy) == combined["day"].nunique() - 1
    assert np.allclose(strategy, 0.0)


def test_trial_count_reads_registered_rows(tmp_path):
    path = tmp_path / "TRIALS.md"
    path.write_text(
        "| # | Date |\n|---|---|\n| 1 | today |\n| 2 | today |\n",
        encoding="utf-8",
    )
    assert collector.count_registered_trials(path) == 2


def test_load_sim_rows_flattens_model_flow(tmp_path):
    run_dir = tmp_path / "one"
    run_dir.mkdir()
    row = {
        "ticker": "TEST",
        "day": "2025-01-02",
        "real_close": 10.0,
        "next_day_return": 0.1,
        "flow_imbalance": 0.2,
        "flow_imbalance_unweighted": 0.1,
        "decision_entropy": 1.0,
        "model_flow_imbalance": {"Qwen/Qwen2.5-1.5B-Instruct": 0.25},
    }
    (run_dir / "sim.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    frame = collector.load_sim_rows(tmp_path)

    assert frame.loc[0, "single_model_signal"] == 0.25
