# TRIALS.md — Registered trial ledger (feeds Deflated Sharpe, D-11)

Rule: every evaluated (signal definition x universe x window x weighting) tuple is
one trial, REGISTERED BEFORE its stats are computed. n_trials passed to
`evals.prediction.deflated_sharpe` must equal the count of rows below at analysis
time. Ablations count. Prompt iterations before G2 do not (no return stats viewed).

OOS-10 universe (G1-frozen, docs/G1_UNIVERSES.md): NVNI TLRY EDIT CHPT BLNK FRSX TPET OGI CCO
ICCM. Selection 2024-12-20; window 2025-01-02..2026-06-30. Roster: Qwen2.5-1.5B/3B, Phi-3.5.
Run: `oos-main-v1` (alias arm), forward-return horizons {1d, 5d}.

| # | Date | Phase | Signal / config | Universe | Window | Status |
|---|------|-------|-----------------|----------|--------|--------|
| 1 | 2026-07-05 | P4 | flow_imbalance (conf-weighted), alias arm | OOS-10 | G1-frozen | registered |
| 2 | 2026-07-05 | P4 | flow_imbalance (unweighted), alias arm | OOS-10 | G1-frozen | registered |
| 3 | 2026-07-05 | P4 | single-strong-LLM sentiment baseline | OOS-10 | G1-frozen | registered |
| 4 | 2026-07-05 | P4 | momentum(1/5/20), AR(1), logistic baselines | OOS-10 | G1-frozen | registered |

n_trials = 4 (rows above) feeds Deflated Sharpe (evals.prediction.deflated_sharpe, D-11) at
P5. Add rows before running; never delete rows; failed/abandoned trials stay counted. Prompt
iterations before G2 do not count (no return stats were viewed).
