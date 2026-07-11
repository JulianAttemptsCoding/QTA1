# Simulated Price vs Actual Price

Yes, the project has OOS data. P4 main and P4 follow-up runs are OOS; P3 is the 2019 calibration split.

The simulated price is the LLM-agent auction-clearing price (`auction_price`) and the actual price is the archived daily close (`real_close`). This charting pass is diagnostic: the original RQ3 prediction track tested flow imbalance, not the auction price as a fair-value model.

## Data Splits

| Split | OOS | Runs | Tickers | Start | End | Configs |
| --- | --- | --- | --- | --- | --- | --- |
| calib-2019 | no | 20 | 10 | 2019-07-01 | 2019-12-31 | alias, named |
| oos-2025-followups | yes | 10 | 2 | 2025-01-02 | 2025-03-31 | news_off_n100, personas_off_n100, scaling_n100, scaling_n300, scaling_n50 |
| oos-2025-main | yes | 10 | 10 | 2025-01-02 | 2025-07-03 | main_n200 |

## Run-Level Price Tracking Metrics

`spread_net_*` is an exploratory close-to-close diagnostic using `sign(auction_price / real_close - 1)` with `25.0` bps one-way turnover cost. It is not an arbitrage claim.

| Split | Ticker | Arm | Config | Days | Start | End | Level corr | Return corr | Sim ret hit | Spread next hit | Spread net mean bps | Spread net Sharpe | Figure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| calib-2019 | BLNK | alias | alias | 128 | 2019-07-01 | 2019-12-31 | -0.7047 | 0.0214 | 1.0000 | 0.4274 | -16.7661 | -0.7162 | docs/figures/price_tracking/calib-2019/calib-2019-g1-blnk-alias-v1.svg |
| calib-2019 | BLNK | named | named | 128 | 2019-07-01 | 2019-12-31 | -0.7047 | 0.0214 | 1.0000 | 0.4274 | -16.7661 | -0.7162 | docs/figures/price_tracking/calib-2019/calib-2019-g1-blnk-named-v1.svg |
| calib-2019 | CRBP | alias | alias | 128 | 2019-07-01 | 2019-12-31 | 0.0000 | NA | 0.5000 | 0.4683 | -15.3338 | -0.9330 | docs/figures/price_tracking/calib-2019/calib-2019-g1-crbp-alias-v1.svg |
| calib-2019 | CRBP | named | named | 128 | 2019-07-01 | 2019-12-31 | 0.0000 | NA | 0.5000 | 0.4683 | -15.3338 | -0.9330 | docs/figures/price_tracking/calib-2019/calib-2019-g1-crbp-named-v1.svg |
| calib-2019 | GOLD | alias | alias | 128 | 2019-07-01 | 2019-12-31 | NA | NA | 0.5000 | 0.4206 | -20.7912 | -1.3489 | docs/figures/price_tracking/calib-2019/calib-2019-g1-gold-alias-v1.svg |
| calib-2019 | GOLD | named | named | 128 | 2019-07-01 | 2019-12-31 | NA | NA | 0.5000 | 0.4206 | -20.7912 | -1.3489 | docs/figures/price_tracking/calib-2019/calib-2019-g1-gold-named-v1.svg |
| calib-2019 | IGC | alias | alias | 128 | 2019-07-01 | 2019-12-31 | -0.0000 | NA | 0.5000 | 0.3492 | -50.3490 | -2.0024 | docs/figures/price_tracking/calib-2019/calib-2019-g1-igc-alias-v1.svg |
| calib-2019 | IGC | named | named | 128 | 2019-07-01 | 2019-12-31 | -0.0000 | NA | 0.5000 | 0.3492 | -50.3490 | -2.0024 | docs/figures/price_tracking/calib-2019/calib-2019-g1-igc-named-v1.svg |
| calib-2019 | IIPR | alias | alias | 128 | 2019-07-01 | 2019-12-31 | NA | NA | 0.5000 | 0.4841 | -16.7543 | -0.7351 | docs/figures/price_tracking/calib-2019/calib-2019-g1-iipr-alias-v1.svg |
| calib-2019 | IIPR | named | named | 128 | 2019-07-01 | 2019-12-31 | NA | NA | 0.5000 | 0.4841 | -16.7543 | -0.7351 | docs/figures/price_tracking/calib-2019/calib-2019-g1-iipr-named-v1.svg |
| calib-2019 | LEVI | alias | alias | 128 | 2019-07-01 | 2019-12-31 | NA | NA | 0.5000 | 0.5159 | -3.0957 | -0.2029 | docs/figures/price_tracking/calib-2019/calib-2019-g1-levi-alias-v1.svg |
| calib-2019 | LEVI | named | named | 128 | 2019-07-01 | 2019-12-31 | NA | NA | 0.5000 | 0.5159 | -3.0957 | -0.2029 | docs/figures/price_tracking/calib-2019/calib-2019-g1-levi-named-v1.svg |
| calib-2019 | PLUG | alias | alias | 128 | 2019-07-01 | 2019-12-31 | 0.7488 | -0.1042 | 0.5000 | 0.4758 | -14.6373 | -0.7077 | docs/figures/price_tracking/calib-2019/calib-2019-g1-plug-alias-v1.svg |
| calib-2019 | PLUG | named | named | 128 | 2019-07-01 | 2019-12-31 | 0.7488 | -0.1042 | 0.5000 | 0.4758 | -14.6373 | -0.7077 | docs/figures/price_tracking/calib-2019/calib-2019-g1-plug-named-v1.svg |
| calib-2019 | RIOT | alias | alias | 128 | 2019-07-01 | 2019-12-31 | 0.0000 | NA | 0.5000 | 0.3651 | -56.8537 | -2.5123 | docs/figures/price_tracking/calib-2019/calib-2019-g1-riot-alias-v1.svg |
| calib-2019 | RIOT | named | named | 128 | 2019-07-01 | 2019-12-31 | 0.0000 | NA | 0.5000 | 0.3651 | -56.8537 | -2.5123 | docs/figures/price_tracking/calib-2019/calib-2019-g1-riot-named-v1.svg |
| calib-2019 | VKTX | alias | alias | 128 | 2019-07-01 | 2019-12-31 | -0.0000 | NA | 0.5000 | 0.5317 | 39.7756 | 1.8409 | docs/figures/price_tracking/calib-2019/calib-2019-g1-vktx-alias-v1.svg |
| calib-2019 | VKTX | named | named | 128 | 2019-07-01 | 2019-12-31 | -0.0000 | NA | 0.5000 | 0.5317 | 39.7756 | 1.8409 | docs/figures/price_tracking/calib-2019/calib-2019-g1-vktx-named-v1.svg |
| calib-2019 | XXII | alias | alias | 128 | 2019-07-01 | 2019-12-31 | -0.3734 | 0.0064 | 0.5000 | 0.4065 | -15.6541 | -0.3366 | docs/figures/price_tracking/calib-2019/calib-2019-g1-xxii-alias-v1.svg |
| calib-2019 | XXII | named | named | 128 | 2019-07-01 | 2019-12-31 | -0.3484 | 0.0131 | 1.0000 | 0.4194 | -8.2353 | -0.1768 | docs/figures/price_tracking/calib-2019/calib-2019-g1-xxii-named-v1.svg |
| oos-2025-followups | NVNI | alias | news_off_n100 | 60 | 2025-01-02 | 2025-03-31 | -0.0000 | NA | 0.5000 | 0.5000 | 11.9484 | 0.0635 | docs/figures/price_tracking/oos-2025-followups/oos-2025-g1-news_off-nvni-alias-n100-v1.svg |
| oos-2025-followups | NVNI | alias | personas_off_n100 | 60 | 2025-01-02 | 2025-03-31 | -0.0000 | NA | 0.5000 | 0.5000 | 11.9484 | 0.0635 | docs/figures/price_tracking/oos-2025-followups/oos-2025-g1-personas_off-nvni-alias-n100-v1.svg |
| oos-2025-followups | NVNI | alias | scaling_n100 | 60 | 2025-01-02 | 2025-03-31 | -0.0000 | NA | 0.5000 | 0.5000 | 11.9484 | 0.0635 | docs/figures/price_tracking/oos-2025-followups/oos-2025-g1-scaling-nvni-alias-n100-v1.svg |
| oos-2025-followups | NVNI | alias | scaling_n300 | 60 | 2025-01-02 | 2025-03-31 | -0.6633 | -0.0527 | 0.0000 | 0.5088 | 18.4931 | 0.0983 | docs/figures/price_tracking/oos-2025-followups/oos-2025-g1-scaling-nvni-alias-n300-v1.svg |
| oos-2025-followups | NVNI | alias | scaling_n50 | 60 | 2025-01-02 | 2025-03-31 | -0.0000 | NA | 0.5000 | 0.5000 | 11.9484 | 0.0635 | docs/figures/price_tracking/oos-2025-followups/oos-2025-g1-scaling-nvni-alias-n50-v1.svg |
| oos-2025-followups | TLRY | alias | news_off_n100 | 60 | 2025-01-02 | 2025-03-31 | 0.0000 | NA | 0.5000 | 0.3276 | -122.9148 | -4.1995 | docs/figures/price_tracking/oos-2025-followups/oos-2025-g1-news_off-tlry-alias-n100-v1.svg |
| oos-2025-followups | TLRY | alias | personas_off_n100 | 60 | 2025-01-02 | 2025-03-31 | 0.0000 | NA | 0.5000 | 0.3276 | -122.9148 | -4.1995 | docs/figures/price_tracking/oos-2025-followups/oos-2025-g1-personas_off-tlry-alias-n100-v1.svg |
| oos-2025-followups | TLRY | alias | scaling_n100 | 60 | 2025-01-02 | 2025-03-31 | 0.0000 | NA | 0.5000 | 0.3276 | -122.9148 | -4.1995 | docs/figures/price_tracking/oos-2025-followups/oos-2025-g1-scaling-tlry-alias-n100-v1.svg |
| oos-2025-followups | TLRY | alias | scaling_n300 | 60 | 2025-01-02 | 2025-03-31 | 0.0000 | NA | 0.5000 | 0.3276 | -122.9148 | -4.1995 | docs/figures/price_tracking/oos-2025-followups/oos-2025-g1-scaling-tlry-alias-n300-v1.svg |
| oos-2025-followups | TLRY | alias | scaling_n50 | 60 | 2025-01-02 | 2025-03-31 | 0.0000 | NA | 0.5000 | 0.3276 | -122.9148 | -4.1995 | docs/figures/price_tracking/oos-2025-followups/oos-2025-g1-scaling-tlry-alias-n50-v1.svg |
| oos-2025-main | BLNK | alias | main_n200 | 125 | 2025-01-02 | 2025-07-03 | NA | NA | 0.5000 | 0.4715 | -12.8684 | -0.4100 | docs/figures/price_tracking/oos-2025-main/oos-2025-g1-blnk-alias-v1.svg |
| oos-2025-main | CCO | alias | main_n200 | 125 | 2025-01-02 | 2025-07-03 | -0.7428 | 0.2051 | 1.0000 | 0.4538 | 8.7913 | 0.3901 | docs/figures/price_tracking/oos-2025-main/oos-2025-g1-cco-alias-v1.svg |
| oos-2025-main | CHPT | alias | main_n200 | 125 | 2025-01-02 | 2025-07-03 | 0.4290 | 0.3129 | 0.8750 | 0.4508 | -34.7797 | -1.0211 | docs/figures/price_tracking/oos-2025-main/oos-2025-g1-chpt-alias-v1.svg |
| oos-2025-main | EDIT | alias | main_n200 | 125 | 2025-01-02 | 2025-07-03 | 0.3167 | -0.3130 | 0.0000 | 0.4876 | -8.3679 | -0.1250 | docs/figures/price_tracking/oos-2025-main/oos-2025-g1-edit-alias-v1.svg |
| oos-2025-main | FRSX | alias | main_n200 | 125 | 2025-01-02 | 2025-07-03 | -0.0000 | NA | 0.5000 | 0.4390 | -40.5804 | -1.3266 | docs/figures/price_tracking/oos-2025-main/oos-2025-g1-frsx-alias-v1.svg |
| oos-2025-main | ICCM | alias | main_n200 | 125 | 2025-01-02 | 2025-07-03 | -0.3613 | -0.0200 | 0.5000 | 0.4701 | 6.1582 | 0.2564 | docs/figures/price_tracking/oos-2025-main/oos-2025-g1-iccm-alias-v1.svg |
| oos-2025-main | NVNI | alias | main_n200 | 125 | 2025-01-02 | 2025-07-03 | -0.7701 | -0.0506 | 0.0000 | 0.4426 | 95.7062 | 0.6318 | docs/figures/price_tracking/oos-2025-main/oos-2025-g1-nvni-alias-v1.svg |
| oos-2025-main | OGI | alias | main_n200 | 125 | 2025-01-02 | 2025-07-03 | 0.0000 | NA | 0.5000 | 0.4344 | 17.9581 | 0.7469 | docs/figures/price_tracking/oos-2025-main/oos-2025-g1-ogi-alias-v1.svg |
| oos-2025-main | TLRY | alias | main_n200 | 125 | 2025-01-02 | 2025-07-03 | -0.0000 | NA | 0.5000 | 0.3821 | -65.7004 | -1.9648 | docs/figures/price_tracking/oos-2025-main/oos-2025-g1-tlry-alias-v1.svg |
| oos-2025-main | TPET | alias | main_n200 | 125 | 2025-01-02 | 2025-07-03 | -0.6768 | -0.0102 | 0.0000 | 0.4836 | 1.5644 | 0.0253 | docs/figures/price_tracking/oos-2025-main/oos-2025-g1-tpet-alias-v1.svg |

## Interpretation Guardrails

- A flat or weakly correlated auction path is expected for some runs because the auction track was designed for realism diagnostics, not direct price forecasting.
- A positive spread diagnostic can be a post-hoc artifact unless it survives pre-registration, costs, borrow/shortability constraints, capacity, and multiple-testing correction.
- Treat these plots as model diagnostics and inputs to a future registered trading test, not investment advice.
