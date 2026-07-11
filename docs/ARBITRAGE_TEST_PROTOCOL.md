# Arbitrage Test Protocol

## Bottom Line

The current artifacts do not prove an arbitrage opportunity. At most, they
produce exploratory signals that could be turned into a pre-registered trading
test. Because the price-vs-actual analysis was requested after the OOS artifacts
were already inspected, any result in `docs/PRICE_TRACKING_REPORT.md` is
hypothesis-generating, not confirmatory.

In this context, "arbitrage" should be reserved for a self-financing, executable,
hedged strategy with negligible residual risk. A daily signal from simulated
auction price to small-cap stock returns is more realistically a candidate alpha
signal until it survives the tests below.

## Evidence From Current Price Diagnostics

Source: `docs/PRICE_TRACKING_REPORT.md`.

- OOS exists: P4 main is `oos-2025-main`, and P4 scaling/ablation runs are
  `oos-2025-followups`.
- Many simulated auction-price paths are flat or weakly correlated with actual
  closes. This is consistent with the original design: the auction-price track
  was a market-realism diagnostic, while RQ3 used flow imbalance for prediction.
- The exploratory `auction_price / real_close - 1` spread diagnostic has mixed
  OOS behavior. Some OOS rows have positive net diagnostic Sharpe after a simple
  25 bps cost model, but hit rates and cross-run stability are not strong enough
  to justify an arbitrage claim.

## Research Grounding

- The SEC warns that back-tested performance is hypothetical and does not reflect
  actual performance; it also highlights fees, methodology, market conditions,
  and cherry-picking as key reliability issues:
  [SEC Investor Bulletin: Performance Claims](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-47).
- Bailey and Lopez de Prado's Deflated Sharpe Ratio addresses selection bias,
  multiple testing, and non-normal returns, all of which matter here:
  [The Deflated Sharpe Ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551).
- Sullivan, Timmermann, and White use White's Reality Check bootstrap to adjust
  for data-snooping across trading-rule universes:
  [Data-Snooping, Technical Trading Rule Performance, and the Bootstrap](https://ideas.repec.org/a/bla/jfinan/v54y1999i5p1647-1691.html).
- FINRA's current intraday-margin guidance emphasizes real-time margin adequacy
  and the risk of frequent margin trading:
  [Understanding the New Intraday Margin Requirements](https://www.finra.org/investors/insights/intraday-margin-requirements).

## Confirmatory Test Design

### 1. Freeze A New Test Before Looking

Do not reuse the already-viewed P4 OOS period as confirmatory evidence. Freeze a
new untouched holdout or run a live paper-trading period. Register:

- eligible ticker universe and delisting handling;
- exact signal definitions;
- exact execution timestamp;
- cost, borrow, slippage, spread, and capacity assumptions;
- all variants and stop conditions;
- primary metric and pass/fail threshold.

### 2. Define Executable Signals

Candidate signals:

- `price_spread`: `auction_price / real_close - 1`;
- `flow_imbalance`: existing RQ3 signal;
- `hybrid`: price-spread direction only when flow and price-spread agree.

Execution rule must avoid lookahead. If `real_close` is used to compute
`price_spread`, the earliest realistic fill is next open or next close, not a
same-close fill unless an actual close auction execution model is implemented.

### 3. Use Realistic Costs

At minimum:

- bid-ask spread and slippage by ticker/day;
- commissions, SEC/FINRA fees, and borrow fees;
- short locate failure and hard-to-borrow exclusions;
- corporate actions, halts, delistings, and missing bars;
- position size capped by ADV participation, e.g. 1 percent of dollar volume;
- margin and maintenance rules from the actual broker.

### 4. Benchmark Against Cheap Alternatives

The signal must beat:

- buy-and-hold per ticker;
- equal-weight long/short baseline;
- momentum 1/5/20d;
- AR(1) and logistic baselines already used in RQ3;
- the single-model sentiment baseline;
- sector/market beta hedges for residual-return tests.

### 5. Statistical Tests

Primary null:

`H0: expected net excess return after all costs and constraints is <= 0.`

Required tests:

- Newey-West or block-bootstrap confidence interval for mean net daily return;
- block-bootstrap confidence interval for hit rate;
- Diebold-Mariano directional loss test versus each baseline;
- White Reality Check or Hansen SPA across all tried strategy variants;
- Deflated Sharpe Ratio using the full registered trial count;
- drawdown, turnover, skew, tail-loss, and capacity stress tests;
- sensitivity to cost assumptions from 10 bps through 200 bps.

Pass threshold should be hard before launch, for example:

- net annualized Sharpe above `1.0`;
- DSR above `0.95`;
- Reality Check or SPA adjusted p-value below `0.05`;
- positive net return after 100 bps one-way stress cost;
- no single ticker contributes more than one-third of total PnL;
- live paper-trading confirmation for at least 60 trading days.

### 6. Arbitrage-Specific Bar

Only call it arbitrage if all are true:

- self-financing long/short book;
- beta-neutral and sector-neutral residual returns;
- borrow and execution are available at tested size;
- PnL remains positive after stressed costs and financing;
- losses are bounded by a documented hedge relationship, not just historical
  backtest behavior.

If those conditions fail but net predictive performance remains significant, call
it a speculative alpha signal, not arbitrage.

## Recommended Next Experiment

1. Pre-register a new `docs/TRIALS.md` section for the price-spread/hybrid
   strategy family.
2. Build `scripts/p5_arbitrage_backtest.py` that consumes only point-in-time
   `sim.jsonl` and execution-cost inputs.
3. Run it first on already-viewed data only as a unit/integration check.
4. Freeze the code hash.
5. Evaluate on a new future holdout or live paper-trading stream.

No money should be traded from the current backtest alone.
