# P5_STATS -- RQ3 prediction statistics (oos-main-v2)

Generated (UTC): 2026-07-05

Crowd flow-imbalance signal vs realized forward real returns on the G1-frozen OOS-10 universe (alias arm). Estimators: agorasim.evals.prediction. DSR uses the registered trial count n_trials=4 (docs/TRIALS.md, D-11).

| signal x horizon | ticker-days | IC | IC 95% CI | hit rate | strat SR | DM vs mom5 (p) | DSR |
|---|---:|---:|---|---:|---:|---:|---:|
| imbalance_cw_h1 | 290 | 0.0167 | [-0.0838, 0.1174] | 0.4552 | 0.924 | -0.956 (0.339) | 0.2415 |
| imbalance_cw_h5 | 250 | -0.1367 | [-0.2711, -0.0068] | 0.396 | 2.17 | 0.32 (0.7486) | 0.9904 |
| imbalance_uw_h1 | 290 | 0.0178 | [-0.0856, 0.1188] | 0.4621 | -0.932 | -1.123 (0.2613) | 0.0 |
| imbalance_uw_h5 | 250 | -0.1352 | [-0.2667, -0.0048] | 0.388 | 1.406 | 0.434 (0.6643) | 0.7764 |

IC = Spearman rank corr(signal_t, forward_return). hit rate on nonzero-signal days. DM > 0 favors the crowd over the 5-day momentum baseline (positive = lower directional loss); p is two-sided. DSR = P(true SR > 0) deflated for 4 trials.

Interpretation is written after inspecting the numbers; a near-zero IC / DSR < 0.5 is the expected honest outcome for weak small models on hard-to-trade small caps (PLAN section 1) and is reported as such, not buried.
