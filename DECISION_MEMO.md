# DECISION_MEMO.md — Which idea first, and why

**Decision: Idea 1 (LLM-agent retail crowd simulation) first.** Idea 2 (regression-
function dictionary / analog method) is parked with a cheap pre-registered
falsification protocol (`docs/IDEA2_FALSIFICATION.md`) it must pass before any real
investment of time.

## Scoring

| Criterion (weight) | Idea 1: LLM crowd sim | Idea 2: function-dictionary MFT |
|---|---|---|
| Novelty positioning (high) | Strong. LLM market simulation is an active 2024–2026 literature (TwinMarket, StockAgent, ASFM, Lopez-Lira 2025, MarS), but none targets *prediction of real retail-heavy small caps via simulated crowd flow with contamination controls*. The idea slots into a hot conversation with a clear delta. | Weak. It is a re-parameterization of 20+ years of prior art: symbolic/segment features (SAX), case-based/k-NN analog forecasting, and technical-pattern conditioning (Lo–Mamaysky–Wang 2000). The "different basis functions" twist does not change the statistical structure. |
| Value of a null result (high) | High. Null RQ3 + positive RQ1/RQ2 = validated retail-crowd simulator (event studies, counterfactuals, education, further research) — demonstrably fundable as a PoC. | Near zero. A null is the expected, unpublishable outcome; a positive would be suspect until it survives DSR/purged-CV, which the literature suggests it won't net of costs. |
| Fit to constraints (med) | Good: daily frequency, free Alpaca/EDGAR/Robintrack data, T4-sized models, ~$60–75 of the $100 budget (PLAN §6). | Compute-trivial (CPU), but the *data* constraint bites: clean small-universe 1-min data on the free feed is the weakest link, and 5 tickers give no cross-sectional power. |
| Expected real alpha (low weight, honest) | ~0. Any RQ3 signal will be small, small-cap-concentrated, and likely untradeable net of costs. | ~0, with higher confidence in the null: minute-scale edges on a 5-ticker book must clear spreads that are typically far larger than any plausible pattern edge. |
| Direct answer to "could it beat SPY?" | Not a design goal; do not expect it. | **No.** I do not genuinely believe it beats SPY net of costs, which was your stated go/no-go condition. |

## Why Idea 2 is parked, specifically

1. **Prior art density.** Conditioning next-move forecasts on a discretized shape of
   the recent path is exactly what SAX-style symbolization, k-NN/case-based-reasoning
   forecasting, and algorithmic chart-pattern work already do; the canonical result
   (Lo–Mamaysky–Wang 2000) is that such patterns can carry *some* incremental
   information while *profitability remains unestablished*, and the follow-on survey
   literature (Park & Irwin 2007) finds reported profits shrink under proper
   out-of-sample testing and costs.
2. **The feature is statistically fragile.** "Which of {logistic, Gompertz, (x−a)^n−b,
   tan, sin, …} fits a 30–60 minute noisy window best" is a high-variance label:
   several families are near-unidentifiable on short windows (tan/inverse blow up;
   Gompertz vs logistic differ by curvature you cannot resolve at 1-min noise), so
   the symbol sequence largely encodes noise. Garbage symbols in → garbage library out.
3. **Nonstationarity kills libraries.** Regime drift means the "what happened after
   this pattern" distribution moves; recency-weighting (your LSTM idea) fights this
   but reintroduces the NN you wanted to avoid, and AHP is a subjective-weighting
   method with no place in a data-driven pipeline.
4. **Microstructure and costs.** At 1-min on small tickers, effective spreads and
   fees dominate plausible edges; the well-documented intraday effects that survive
   (e.g., first-half-hour → last-half-hour index momentum) are index-level, tiny,
   and crowded.
5. **Multiple testing.** A large function dictionary × thresholds × horizons is a
   trial-count explosion; under DSR discipline the bar rises exactly as fast as the
   search space.

**Escape hatch (respecting the idea):** `docs/IDEA2_FALSIFICATION.md` specifies a
2–3 day, ~$0 CPU study (20 liquid tickers, 5-min bars, bounded well-posed function
dictionary, purged/embargoed CV, cost model, pre-registered DSR ≥ 0.95 threshold).
If it passes, reopen. Expected outcome: null.

## Compliance and honesty notes

- **GCP credits:** creating additional accounts to farm $300 free-trial credits
  violates Google Cloud's terms of service; all budgeting assumes one account.
  Legitimate scaling paths: GCP research credits, academic credit programs, and the
  TPU Research Cloud (vLLM supports TPUs).
- **Not investment advice.** This is research infrastructure; PoC results, even
  positive ones, are not evidence a strategy is deployable.
- **Manipulation optics:** simulating retail behavior to *predict* is passive
  research; nothing here posts content, trades, or attempts to influence any market.
