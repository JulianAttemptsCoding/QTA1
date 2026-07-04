"""Unit tests for the P5 stats helpers (forward returns, momentum, pairing, Sharpe)."""
import numpy as np

import scripts.p5_stats as p


def _closes():
    return [("2025-01-02", 10.0), ("2025-01-03", 11.0), ("2025-01-06", 12.0), ("2025-01-07", 9.0)]


def test_forward_returns_horizon():
    fr = p.forward_returns(_closes(), 1)
    assert abs(fr["2025-01-02"] - 0.10) < 1e-9
    assert abs(fr["2025-01-03"] - (12.0 / 11.0 - 1)) < 1e-9
    assert "2025-01-07" not in fr  # no bar h ahead


def test_momentum_trailing():
    mom = p.momentum(_closes(), 1)
    assert abs(mom["2025-01-03"] - 0.10) < 1e-9
    assert "2025-01-02" not in mom  # no bar k behind


def test_pair_aligns_signal_and_return():
    signals = [
        {"ticker": "AAA", "date": "2025-01-02", "imbalance_cw": 0.5},
        {"ticker": "AAA", "date": "2025-01-07", "imbalance_cw": -0.3},  # no fwd return -> dropped
        {"_summary": True},
    ]
    s, r, _ = p.pair(signals, {"AAA": _closes()}, "imbalance_cw", 1)
    assert len(s) == 1 and s[0] == 0.5
    assert abs(r[0] - 0.10) < 1e-9


def test_strategy_sharpe_positive_when_signal_predicts():
    sig = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
    fwd = np.array([0.01, 0.02, 0.015, 0.005, 0.02])
    sr, skew, kurt, n = p.strategy_sharpe(sig, fwd)
    assert sr > 0 and n == 5


def test_block_bootstrap_ic_runs():
    rng = np.random.default_rng(0)
    s = rng.normal(size=60)
    r = 0.3 * s + rng.normal(size=60)  # weak positive relation
    lo, hi = p.block_bootstrap_ic(s, r, n=200)
    assert lo <= hi
