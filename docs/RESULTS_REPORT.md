# AgoraSim Results Report

## Executive Summary

AgoraSim built and evaluated a Vertex-only LLM-agent retail crowd simulator across
data gates, calibration-era realism/fidelity, and a strictly post-cutoff OOS
prediction study. Heavy inference and model-weight use ran on Vertex AI custom
jobs; local work was limited to orchestration, artifact sync, deterministic
statistics, and tests.

The result is a credible proof of concept, not a trading signal. The simulator
passes the project gates, produces auditable crowd-flow artifacts, and shows
weak calibration-era behavioral fidelity. RQ3 is a controlled null/tiny-effect
result: the crowd-flow signal does not beat cheap baselines in a statistically
compelling way on the frozen OOS main run.

## Registered Questions

### RQ1: Market Realism

Source: `docs/RQ1_REPORT.md`.

The calibration auction paths reproduce some stylized-fact ingredients, most
clearly heavy-tailed return behavior for several tickers and nontrivial auction
volume/entropy. They are not a full synthetic-market substitute: many ticker-arm
paths have zero median absolute returns and flat auction-return diagnostics. The
right claim is narrow: the engine produces auditable market-like paths for some
retail-heavy names, but not broad price-process realism.

### RQ2: Behavioral Fidelity

Source: `docs/RQ2_REPORT.md`.

The calibration-era crowd-flow comparison to Robintrack clears the G3 kill gate,
but weakly. Pooled sign agreement is `0.524` for both alias and named arms, with
pooled Spearman `0.044` in alias and `0.036` in named. The named-vs-alias gap is
effectively absent, which is useful contamination evidence but not a strong
behavioral-fidelity win.

### RQ3: Incremental OOS Information

Source: `docs/RQ3_REPORT.md`.

The main OOS result is not predictive enough to claim alpha. The crowd-weighted
pooled IC is `0.0276` with bootstrap interval crossing zero (`-0.0281` to
`0.0775`), hit rate is `0.4363`, and DSR is `0.0299` after all `16` registered
trials. The single-Qwen and momentum baselines are competitive or better on
several metrics. This is a useful negative result because the universe, trials,
windows, artifacts, and DSR correction were frozen before the final analyses.

## Follow-Up Experiments

Source: `docs/P4_FOLLOWUP_REPORT.md`.

The completed two-ticker follow-ups show that larger crowds can change the
measured flow signal on the short Jan-Mar 2025 window, but the outcome remains
exploratory:

| Follow-up | Pooled weighted IC | Hit | Notes |
|---|---:|---:|---|
| Scaling N=50 | `0.0629` | `0.3898` | Complete for NVNI/TLRY |
| Scaling N=100 | `-0.0115` | `0.3898` | Complete control for ablations |
| Scaling N=300 | `0.1543` | `0.3898` | Complete; IC improves on this window |
| Scaling N=1000 | NA | NA | Budget-cancelled partial; not interpreted |
| News-off N=100 | `0.0832` | `0.3898` | Complete; no evidence news removal hurts here |
| Personas-off N=100 | `0.1072` | `0.3898` | Complete; entropy drops sharply |

The N1000 scaling shards were intentionally cancelled under the original budget
guardrail, preserving partial GCS outputs only for audit: NVNI `10,752/60,000`,
TLRY `1,408/60,000`.

## Price Tracking And Tradability

Source: `docs/PRICE_TRACKING_REPORT.md` and
`docs/ARBITRAGE_TEST_PROTOCOL.md`.

The repository now includes simulated auction-price vs actual-close overlays for
all available P3/P4 splits: calibration, OOS main, and OOS follow-ups. The price
track is diagnostic only. Many OOS auction-price paths are flat or weakly
correlated with actual closes, and current spread diagnostics do not establish
an arbitrage opportunity. Any tradability claim requires a new pre-registered,
cost-aware, multiple-testing-adjusted holdout or live paper-trading experiment.

## OOS Return-Over-Time Backtest

Source: `docs/OOS_BACKTEST_REPORT.md`,
`docs/OOS_BACKTEST_DAILY_RETURNS.csv`, and
`docs/figures/oos_backtest/`.

The exploratory OOS strategy backtest converts archived P4 `sim.jsonl` outputs
into close-to-next-close daily returns with a 25 bps one-way turnover cost. It is
diagnostic only and does not rerun LLM inference.

On the 10-stock OOS main split, every tested strategy lost money after costs.
The least-bad strategy was equal-weight buy-and-hold at `-9.23%` total return
over 124 trading days. The LLM crowd-flow strategies returned `-11.07%`, the
simulated-price spread long-rich strategy returned `-11.57%`, and the
opposite spread strategy returned `-10.05%`. None beat the cheap buy-and-hold
baseline in a useful way.

On the short two-stock OOS follow-up split, the simple `momentum_1d` baseline
returned `+61.94%`, but it is not an LLM-agent strategy and carried a `-40.56%`
maximum drawdown with high turnover. In the same window, LLM crowd-flow and
buy-and-hold both returned `-73.34%`. This reinforces the main conclusion: the
current artifacts are useful for simulator diagnostics, not for an arbitrage or
live trading claim.

## Compute And Budget

Final conservative tracked spend is `$80.25`, below the original `$85` guardrail
used during the migration and follow-up phase. No Vertex jobs remain active.
Vertex AI custom-training T4 quota on the new project was approved to `24` for
regular and preemptible T4s. Matching CPU quota increases were still reconciling
at last recorded check.

## Reproducibility

Key reproducibility artifacts:

- `docs/TRIALS.md`: all `16` registered trials.
- `docs/RQ1_REPORT.md`, `docs/RQ2_REPORT.md`, `docs/RQ3_REPORT.md`,
  `docs/P4_FOLLOWUP_REPORT.md`, `docs/OOS_BACKTEST_REPORT.md`: final
  statistics and OOS return curves.
- `docs/vertex_job_specs/`: redacted Vertex custom job specs.
- `BUDGET.md`: job-level budget ledger.
- `STATE.json`: final local execution state.
- Ignored local `runs/` and GCS bucket artifacts: raw requests, raw outputs,
  manifests, sim rows, and worker summaries.

Final QA command: `python -m pytest -q`.

## Conclusion

AgoraSim succeeds as a controlled, auditable simulator prototype and produces a
publishable negative/weak-result measurement for OOS prediction. The next
scientific step is not more blind scale; it is diagnosing why crowd direction is
biased toward poor hit rates, then rerunning only after a pre-registered model or
prompt change.
