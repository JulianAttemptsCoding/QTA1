import numpy as np

from agorasim.evals import (deflated_sharpe, diebold_mariano, hit_rate,
                            information_coefficient, stylized_fact_report)


def test_ic_and_hit_rate_on_perfect_signal():
    rng = np.random.default_rng(0)
    r = rng.normal(0, 0.02, 250)
    assert information_coefficient(r, r) > 0.99
    assert hit_rate(np.sign(r), r) == 1.0


def test_dm_detects_better_forecast():
    rng = np.random.default_rng(1)
    loss_bad = rng.normal(1.0, 0.1, 300)
    loss_good = loss_bad - 0.2
    dm, p = diebold_mariano(loss_good, loss_bad)
    assert dm < 0 and p < 0.01


def test_dsr_penalizes_many_trials():
    one = deflated_sharpe(sr_hat=0.08, n_obs=252, skew=0.0, kurt=3.0,
                          n_trials=1, sr_var_across_trials=0.0)
    many = deflated_sharpe(sr_hat=0.08, n_obs=252, skew=0.0, kurt=3.0,
                           n_trials=200, sr_var_across_trials=0.02)
    assert 0 <= many < one <= 1


def test_stylized_facts_flags_heavy_tails():
    rng = np.random.default_rng(2)
    t_returns = rng.standard_t(df=3, size=5000) * 0.01
    rep = stylized_fact_report(t_returns)
    assert rep["excess_kurtosis"] > 1.0
    assert abs(rep["acf_r_lag1"]) < 0.1
