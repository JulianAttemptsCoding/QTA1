# TRIALS.md — Registered trial ledger (feeds Deflated Sharpe, D-11)

Rule: every evaluated (signal definition x universe x window x weighting) tuple is
one trial, REGISTERED BEFORE its stats are computed. n_trials passed to
`evals.prediction.deflated_sharpe` must equal the count of rows below at analysis
time. Ablations count. Prompt iterations before G2 do not (no return stats viewed).

| # | Date | Phase | Signal / config | Universe | Window | Status |
|---|------|-------|-----------------|----------|--------|--------|
| 1 | 2026-07-08 | P4 | flow_imbalance (conf-weighted), alias arm | OOS-10 | 2025-01-02 to 2025-07-03 | registered |
| 2 | 2026-07-08 | P4 | flow_imbalance (unweighted), alias arm | OOS-10 | 2025-01-02 to 2025-07-03 | registered |
| 3 | 2026-07-08 | P4 | single-strong-LLM sentiment baseline | OOS-10 | 2025-01-02 to 2025-07-03 | registered |
| 4 | 2026-07-08 | P4 | momentum(1/5/20), AR(1), logistic baselines | OOS-10 | 2025-01-02 to 2025-07-03 | registered |

Add rows before running; never delete rows; failed/abandoned trials stay counted.
