# TRIALS.md — Registered trial ledger (feeds Deflated Sharpe, D-11)

Rule: every evaluated (signal definition x universe x window x weighting) tuple is
one trial, REGISTERED BEFORE its stats are computed. n_trials passed to
`evals.prediction.deflated_sharpe` must equal the count of rows below at analysis
time. Ablations count. Prompt iterations before G2 do not (no return stats viewed).

| # | Date | Phase | Signal / config | Universe | Window | Status |
|---|------|-------|-----------------|----------|--------|--------|
| 1 | TBD  | P4    | flow_imbalance (conf-weighted), alias arm | OOS-10 | G1-frozen | registered |
| 2 | TBD  | P4    | flow_imbalance (unweighted) | OOS-10 | G1-frozen | registered |
| 3 | TBD  | P4    | single-strong-LLM sentiment baseline | OOS-10 | G1-frozen | registered |
| 4 | TBD  | P4    | momentum(1/5/20), AR(1), logistic baselines | OOS-10 | G1-frozen | registered |

Add rows before running; never delete rows; failed/abandoned trials stay counted.
