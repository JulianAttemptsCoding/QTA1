# IDEA2_FALSIFICATION.md — Pre-registered falsification protocol
# (function-dictionary / analog-library medium-frequency idea — PARKED)

Purpose: a ~2–3 day, ~$0 (CPU-only) study that Idea 2 must PASS before any further
investment. Pre-registered here so results can't be argued with after the fact.
Expected outcome, stated up front: NULL (see DECISION_MEMO for why).

## 1. Data
- 20 liquid US tickers (top-ADV megacaps + SPY/QQQ), NOT 5 small ones: maximizes
  statistical power and minimizes spread noise, i.e. gives the idea its best shot.
- 5-minute bars (not 1-minute): halves microstructure noise; free via Alpaca
  historical (G0-verified feed). 3 years of history; last 12 months held out.

## 2. Function dictionary (bounded, well-posed — this is deliberately friendlier
##    than the original list)
- Families: linear, logistic, Gompertz, power (x-a)^n - b with n ∈ [0.5, 3],
  root, exponential, sine (period bounded to [20, 240] min). EXCLUDED: tan and
  inverse families (poles ⇒ unstable fits on noisy windows; including them only
  adds label noise).
- Fit: rolling 60-bar window, center anchored at t=now; Huber loss; parameters
  box-bounded; a fit is VALID only if condition number and parameter s.e. pass
  thresholds fixed in the config; otherwise label = "none".
- Symbol at t = argmin-loss family (or "none"); record loss and parameters.

## 3. Library and forecast
- State = last k symbols (k ∈ {1, 2, 3}, registered) + coarse loss tercile.
- Forecast for horizon h ∈ {6, 12, 24} bars: empirical conditional distribution of
  forward returns over historical occurrences of the same state, exponentially
  recency-weighted (half-life registered at 60 trading days). No LSTM, no AHP —
  if the raw conditional distributions carry nothing, learned weightings of them
  will not rescue the idea, and they multiply the trial count.

## 4. Validation and accounting
- Combinatorially purged cross-validation with embargo ≥ h bars (López de Prado);
  final 12 months touched exactly once.
- Costs: per-side fee + half effective spread estimated from bar data; also report
  a zero-cost column so the failure mode (signal vs costs) is identifiable.
- Every (k, h, weighting) tuple = one registered trial in this file's ledger.

## 5. Pre-registered PASS criteria (all required)
1. Pooled OOS IC of the state-conditional forecast > 0 with block-bootstrap 95% CI
   excluding 0;
2. DM test beats BOTH momentum(1-bar) and AR(1) at p < 0.05 on the held-out year;
3. Net-of-cost long/short Sharpe over the held-out year with DSR ≥ 0.95 given the
   registered trial count;
4. Net-of-cost total return ≥ SPY buy-and-hold over the same held-out year
   (the user's own go/no-go condition).

FAIL on any criterion ⇒ Idea 2 stays parked; the study is archived as evidence.
PASS on all ⇒ escalate to a proper research plan with fresh OOS data.

## Trial ledger
| # | Date | k | h | weighting | Status |
|---|------|---|---|-----------|--------|
| — | —    | — | — | —         | none registered yet |
