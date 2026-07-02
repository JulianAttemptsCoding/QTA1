"""Realism track: Cont (2001) stylized-fact battery on simulated return paths.

Checks (report, not pass/fail -- thresholds set in configs/):
  SF1 heavy tails            : excess kurtosis of returns >> 0
  SF2 no raw linear autocorr : |acf(r, lag 1..5)| small
  SF3 volatility clustering  : acf(|r|, lag 1..20) positive and slowly decaying
  SF4 volume-volatility corr : corr(volume, |r|) > 0
"""
from __future__ import annotations

import numpy as np


def _acf(x: np.ndarray, lag: int) -> float:
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    denom = float(np.dot(x, x))
    if denom == 0 or lag >= len(x):
        return 0.0
    return float(np.dot(x[:-lag], x[lag:]) / denom)


def excess_kurtosis(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    s = r.std()
    if s == 0:
        return 0.0
    z = (r - r.mean()) / s
    return float((z ** 4).mean() - 3.0)


def stylized_fact_report(returns: np.ndarray, volume: np.ndarray | None = None) -> dict:
    r = np.asarray(returns, dtype=float)
    rep = {
        "n": int(len(r)),
        "excess_kurtosis": excess_kurtosis(r),
        "acf_r_lag1": _acf(r, 1),
        "acf_abs_r_lag1": _acf(np.abs(r), 1),
        "acf_abs_r_lag5": _acf(np.abs(r), 5),
        "acf_abs_r_lag20": _acf(np.abs(r), 20),
    }
    if volume is not None and len(volume) == len(r) and np.std(volume) > 0 and np.std(np.abs(r)) > 0:
        rep["corr_volume_absr"] = float(np.corrcoef(volume, np.abs(r))[0, 1])
    return rep
