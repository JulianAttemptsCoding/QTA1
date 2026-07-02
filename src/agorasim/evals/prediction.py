"""Prediction track: incremental-information tests for the simulated flow signal.

All statistics are standard (no technical novelty):
- information_coefficient : Spearman rank corr(signal_t, realized real return_{t+1})
- hit_rate                : sign agreement on nonzero-signal days
- diebold_mariano         : DM test on loss differentials vs a baseline forecast
- deflated_sharpe         : Bailey & Lopez de Prado DSR; n_trials MUST equal the
                            registered count in docs/TRIALS.md (gate G5).
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

_N = NormalDist()


def _rank(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(x), dtype=float)
    # average ties
    vals, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.zeros(len(vals)); np.add.at(sums, inv, ranks)
    return sums[inv] / counts[inv]


def information_coefficient(signal: np.ndarray, fwd_return: np.ndarray) -> float:
    s, r = np.asarray(signal, float), np.asarray(fwd_return, float)
    if len(s) < 3 or np.std(s) == 0 or np.std(r) == 0:
        return 0.0
    rs, rr = _rank(s), _rank(r)
    return float(np.corrcoef(rs, rr)[0, 1])


def hit_rate(signal: np.ndarray, fwd_return: np.ndarray) -> float:
    s, r = np.asarray(signal, float), np.asarray(fwd_return, float)
    mask = s != 0
    if mask.sum() == 0:
        return 0.5
    return float((np.sign(s[mask]) == np.sign(r[mask])).mean())


def diebold_mariano(loss_a: np.ndarray, loss_b: np.ndarray, h: int = 1) -> tuple[float, float]:
    """DM statistic and two-sided p-value for H0: equal expected loss. h = forecast horizon."""
    d = np.asarray(loss_a, float) - np.asarray(loss_b, float)
    T = len(d)
    if T < 5:
        return 0.0, 1.0
    dbar = d.mean()
    gamma0 = float(((d - dbar) ** 2).mean())
    lrv = gamma0
    for k in range(1, h):
        cov = float(((d[k:] - dbar) * (d[:-k] - dbar)).mean())
        lrv += 2.0 * cov
    if lrv <= 0:
        return 0.0, 1.0
    dm = dbar / math.sqrt(lrv / T)
    p = 2.0 * (1.0 - _N.cdf(abs(dm)))
    return float(dm), float(p)


def deflated_sharpe(sr_hat: float, n_obs: int, skew: float, kurt: float,
                    n_trials: int, sr_var_across_trials: float) -> float:
    """DSR = P(true SR > 0 | multiple testing). kurt is FULL kurtosis (normal = 3).
    Returns probability in [0, 1]. See Bailey & Lopez de Prado (2014)."""
    if n_obs < 3 or n_trials < 1:
        return 0.0
    e = math.e
    gamma = 0.5772156649015329
    if n_trials == 1:
        sr0 = 0.0
    else:
        sd = math.sqrt(max(sr_var_across_trials, 1e-12))
        sr0 = sd * ((1 - gamma) * _N.inv_cdf(1 - 1.0 / n_trials)
                    + gamma * _N.inv_cdf(1 - 1.0 / (n_trials * e)))
    denom = 1.0 - skew * sr_hat + ((kurt - 1.0) / 4.0) * sr_hat ** 2
    if denom <= 0:
        return 0.0
    z = (sr_hat - sr0) * math.sqrt(n_obs - 1) / math.sqrt(denom)
    return float(_N.cdf(z))
