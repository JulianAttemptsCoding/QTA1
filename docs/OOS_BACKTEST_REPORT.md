# OOS Backtest Return Over Time

This is an exploratory OOS backtest over archived P4 `sim.jsonl` artifacts only. It does not run LLM inference and it is not a live-trading result.

Assumptions: signal at day `t`, target `next_day_return`, equal-weight across available tickers, and `25.0` bps one-way turnover cost. Returns are hypothetical close-to-next-close returns; borrow fees, short locate failures, halts, market impact, taxes, and broker-specific margin limits are not fully modeled.

## Strategy Definitions

- `buy_hold_equal_weight`: long every available ticker.
- `flow_weighted`: long/short by signed confidence-weighted crowd flow.
- `flow_unweighted`: long/short by signed unweighted crowd flow.
- `price_spread_long_rich`: long when simulated auction price is above actual close; short when below.
- `price_spread_short_rich`: opposite of `price_spread_long_rich`.
- `hybrid_flow_price_agree`: trade only when weighted flow and price spread agree.
- `momentum_1d`: long/short by one-day momentum.

## What Happened

- OOS main: every tested strategy lost money after costs. The least-bad main strategy was `buy_hold_equal_weight` at `-9.2%` total return over `124` trading days.
- The main LLM crowd-flow strategy returned `-11.1%`; the main simulated-price spread strategy returned `-11.6%`. Neither beat buy-and-hold in a useful way.
- OOS follow-ups: `momentum_1d` returned `61.9%` over the short two-stock window, but it is a cheap baseline, not an LLM-agent strategy, and had `-40.6%` max drawdown with high turnover.
- Follow-up LLM flow returned `-73.3%` in the same short window, matching the bad long-biased exposure. This points to directional crowd bias rather than exploitable price discovery.

## Best Strategy By OOS Split/Config

| Split | Config | Strategy | Days | Tickers | Final Equity | Total Return | Ann Return | Ann Sharpe | Max DD | Mean bps/day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oos-2025-followups | news_off_n100 | momentum_1d | 59 | 2 | 1.6194 | 0.6194 | 6.84 | 1.7218 | -0.4056 | 163.77 |
| oos-2025-followups | personas_off_n100 | momentum_1d | 59 | 2 | 1.6194 | 0.6194 | 6.84 | 1.7218 | -0.4056 | 163.77 |
| oos-2025-followups | scaling_n100 | momentum_1d | 59 | 2 | 1.6194 | 0.6194 | 6.84 | 1.7218 | -0.4056 | 163.77 |
| oos-2025-followups | scaling_n300 | momentum_1d | 59 | 2 | 1.6194 | 0.6194 | 6.84 | 1.7218 | -0.4056 | 163.77 |
| oos-2025-followups | scaling_n50 | momentum_1d | 59 | 2 | 1.6194 | 0.6194 | 6.84 | 1.7218 | -0.4056 | 163.77 |
| oos-2025-main | main_n200 | buy_hold_equal_weight | 124 | 10 | 0.9077 | -0.0923 | -0.1786 | -0.0752 | -0.4774 | -1.6815 |

## All Strategy Metrics

| Split | Config | Strategy | Days | Tickers | Final Equity | Total Return | Ann Return | Ann Sharpe | Max DD | Min Daily | Hit | Turnover | Exposure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oos-2025-followups | news_off_n100 | buy_hold_equal_weight | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | news_off_n100 | flow_unweighted | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | news_off_n100 | flow_weighted | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | news_off_n100 | hybrid_flow_price_agree | 59 | 2 | 0.3532 | -0.6468 | -0.9883 | -0.9308 | -0.7563 | -0.3501 | 0.3390 | 0.0339 | 0.8475 |
| oos-2025-followups | news_off_n100 | momentum_1d | 59 | 2 | 1.6194 | 0.6194 | 6.84 | 1.7218 | -0.4056 | -0.2336 | 0.4237 | 1.0339 | 0.9492 |
| oos-2025-followups | news_off_n100 | price_spread_long_rich | 59 | 2 | 0.4173 | -0.5827 | -0.9761 | -0.5675 | -0.7303 | -0.3501 | 0.4237 | 0.0508 | 0.9831 |
| oos-2025-followups | news_off_n100 | price_spread_short_rich | 59 | 2 | 0.0440 | -0.9560 | -1.0000 | 0.5415 | -0.9876 | -0.9854 | 0.5593 | 0.0508 | 0.9831 |
| oos-2025-followups | personas_off_n100 | buy_hold_equal_weight | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | personas_off_n100 | flow_unweighted | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | personas_off_n100 | flow_weighted | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | personas_off_n100 | hybrid_flow_price_agree | 59 | 2 | 0.3532 | -0.6468 | -0.9883 | -0.9308 | -0.7563 | -0.3501 | 0.3390 | 0.0339 | 0.8475 |
| oos-2025-followups | personas_off_n100 | momentum_1d | 59 | 2 | 1.6194 | 0.6194 | 6.84 | 1.7218 | -0.4056 | -0.2336 | 0.4237 | 1.0339 | 0.9492 |
| oos-2025-followups | personas_off_n100 | price_spread_long_rich | 59 | 2 | 0.4173 | -0.5827 | -0.9761 | -0.5675 | -0.7303 | -0.3501 | 0.4237 | 0.0508 | 0.9831 |
| oos-2025-followups | personas_off_n100 | price_spread_short_rich | 59 | 2 | 0.0440 | -0.9560 | -1.0000 | 0.5415 | -0.9876 | -0.9854 | 0.5593 | 0.0508 | 0.9831 |
| oos-2025-followups | scaling_n100 | buy_hold_equal_weight | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | scaling_n100 | flow_unweighted | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | scaling_n100 | flow_weighted | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | scaling_n100 | hybrid_flow_price_agree | 59 | 2 | 0.3532 | -0.6468 | -0.9883 | -0.9308 | -0.7563 | -0.3501 | 0.3390 | 0.0339 | 0.8475 |
| oos-2025-followups | scaling_n100 | momentum_1d | 59 | 2 | 1.6194 | 0.6194 | 6.84 | 1.7218 | -0.4056 | -0.2336 | 0.4237 | 1.0339 | 0.9492 |
| oos-2025-followups | scaling_n100 | price_spread_long_rich | 59 | 2 | 0.4173 | -0.5827 | -0.9761 | -0.5675 | -0.7303 | -0.3501 | 0.4237 | 0.0508 | 0.9831 |
| oos-2025-followups | scaling_n100 | price_spread_short_rich | 59 | 2 | 0.0440 | -0.9560 | -1.0000 | 0.5415 | -0.9876 | -0.9854 | 0.5593 | 0.0508 | 0.9831 |
| oos-2025-followups | scaling_n300 | buy_hold_equal_weight | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | scaling_n300 | flow_unweighted | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | scaling_n300 | flow_weighted | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | scaling_n300 | hybrid_flow_price_agree | 59 | 2 | 0.3532 | -0.6468 | -0.9883 | -0.9308 | -0.7563 | -0.3501 | 0.3390 | 0.0339 | 0.8475 |
| oos-2025-followups | scaling_n300 | momentum_1d | 59 | 2 | 1.6194 | 0.6194 | 6.84 | 1.7218 | -0.4056 | -0.2336 | 0.4237 | 1.0339 | 0.9492 |
| oos-2025-followups | scaling_n300 | price_spread_long_rich | 59 | 2 | 0.4256 | -0.5744 | -0.9740 | -0.5342 | -0.7303 | -0.3501 | 0.4237 | 0.0678 | 0.9746 |
| oos-2025-followups | scaling_n300 | price_spread_short_rich | 59 | 2 | 0.0429 | -0.9571 | -1.0000 | 0.4994 | -0.9879 | -0.9854 | 0.5593 | 0.0678 | 0.9746 |
| oos-2025-followups | scaling_n50 | buy_hold_equal_weight | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | scaling_n50 | flow_unweighted | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | scaling_n50 | flow_weighted | 59 | 2 | 0.2666 | -0.7334 | -0.9965 | -1.3322 | -0.8352 | -0.3501 | 0.3729 | 0.0169 | 1.0000 |
| oos-2025-followups | scaling_n50 | hybrid_flow_price_agree | 59 | 2 | 0.3532 | -0.6468 | -0.9883 | -0.9308 | -0.7563 | -0.3501 | 0.3390 | 0.0339 | 0.8475 |
| oos-2025-followups | scaling_n50 | momentum_1d | 59 | 2 | 1.6194 | 0.6194 | 6.84 | 1.7218 | -0.4056 | -0.2336 | 0.4237 | 1.0339 | 0.9492 |
| oos-2025-followups | scaling_n50 | price_spread_long_rich | 59 | 2 | 0.4173 | -0.5827 | -0.9761 | -0.5675 | -0.7303 | -0.3501 | 0.4237 | 0.0508 | 0.9831 |
| oos-2025-followups | scaling_n50 | price_spread_short_rich | 59 | 2 | 0.0440 | -0.9560 | -1.0000 | 0.5415 | -0.9876 | -0.9854 | 0.5593 | 0.0508 | 0.9831 |
| oos-2025-main | main_n200 | buy_hold_equal_weight | 124 | 10 | 0.9077 | -0.0923 | -0.1786 | -0.0752 | -0.4774 | -0.1113 | 0.4435 | 0.0081 | 1.0000 |
| oos-2025-main | main_n200 | flow_unweighted | 124 | 10 | 0.8893 | -0.1107 | -0.2121 | -0.1530 | -0.4774 | -0.1113 | 0.4435 | 0.0177 | 1.0000 |
| oos-2025-main | main_n200 | flow_weighted | 124 | 10 | 0.8893 | -0.1107 | -0.2121 | -0.1530 | -0.4774 | -0.1113 | 0.4435 | 0.0177 | 1.0000 |
| oos-2025-main | main_n200 | hybrid_flow_price_agree | 124 | 10 | 0.8965 | -0.1035 | -0.1992 | -0.1484 | -0.4580 | -0.1113 | 0.3871 | 0.0460 | 0.8581 |
| oos-2025-main | main_n200 | momentum_1d | 124 | 10 | 0.6801 | -0.3199 | -0.5432 | -1.2658 | -0.4512 | -0.0860 | 0.4032 | 1.0379 | 0.9460 |
| oos-2025-main | main_n200 | price_spread_long_rich | 124 | 10 | 0.8843 | -0.1157 | -0.2211 | -0.1363 | -0.4693 | -0.1113 | 0.4516 | 0.0887 | 0.9790 |
| oos-2025-main | main_n200 | price_spread_short_rich | 124 | 10 | 0.8995 | -0.1005 | -0.1937 | -0.0519 | -0.3717 | -0.2295 | 0.5403 | 0.0887 | 0.9790 |

## Return-Over-Time Figures

- `docs/figures/oos_backtest/equity_oos-2025-followups_news_off_n100.svg`
- `docs/figures/oos_backtest/equity_oos-2025-followups_personas_off_n100.svg`
- `docs/figures/oos_backtest/equity_oos-2025-followups_scaling_n100.svg`
- `docs/figures/oos_backtest/equity_oos-2025-followups_scaling_n300.svg`
- `docs/figures/oos_backtest/equity_oos-2025-followups_scaling_n50.svg`
- `docs/figures/oos_backtest/equity_oos-2025-main_main_n200.svg`

## Daily Return Data

- CSV: `docs/OOS_BACKTEST_DAILY_RETURNS.csv`

## Interpretation

The backtest is useful for seeing return paths, drawdowns, and sensitivity across strategy definitions. It is not sufficient to claim arbitrage. Positive rows must be treated as data-mined until they survive a fresh pre-registered holdout or live paper-trading test with full execution, borrow, financing, capacity, and multiple-testing controls.
