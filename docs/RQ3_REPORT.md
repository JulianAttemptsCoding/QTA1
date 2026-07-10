# RQ3 OOS Prediction Report

- Source: frozen P4 alias-arm Vertex artifacts.
- Forecast target: next-trading-day close-to-close return.
- DM loss: directional 0-1 loss; negative DM favors the crowd.
- Baselines are walk-forward and use only information available by each decision date.

## Pooled Results

| Signal | N | IC | IC 2.5% | IC 97.5% | Hit | Hit 2.5% | Hit 97.5% | Sharpe |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| crowd_weighted | 620 | 0.0055 | -0.0699 | 0.0719 | 0.4371 | 0.3919 | 0.4661 | -0.0079 |
| crowd_unweighted | 620 | 0.0025 | -0.0732 | 0.0691 | 0.4371 | 0.3919 | 0.4661 | -0.0079 |
| single_qwen | 620 | 0.0846 | 0.0193 | 0.1755 | 0.4371 | 0.3903 | 0.4645 | -0.5491 |
| momentum_1d | 615 | -0.0690 | -0.1592 | -0.0099 | 0.4818 | 0.4395 | 0.5158 | 1.0756 |
| momentum_5d | 595 | -0.0247 | -0.1072 | 0.0385 | 0.5017 | 0.4644 | 0.5358 | 1.3232 |
| momentum_20d | 520 | -0.0080 | -0.0966 | 0.0669 | 0.5154 | 0.4712 | 0.5577 | 0.9715 |
| ar1 | 515 | -0.0329 | -0.1158 | 0.0471 | 0.5049 | 0.4680 | 0.5437 | 0.4876 |
| logistic | 320 | 0.0183 | -0.0730 | 0.0937 | 0.4875 | 0.4437 | 0.5406 | -3.0813 |

## Diebold-Mariano vs Crowd

| Baseline | N | DM | p | Crowd error | Baseline error |
| --- | --- | --- | --- | --- | --- |
| crowd_unweighted | 124 | 0.0000 | 1.0000 | 0.5629 | 0.5629 |
| single_qwen | 124 | -0.0000 | 1.0000 | 0.5629 | 0.5629 |
| momentum_1d | 123 | 1.1812 | 0.2375 | 0.5642 | 0.5220 |
| momentum_5d | 119 | 1.4026 | 0.1607 | 0.5630 | 0.5042 |
| momentum_20d | 104 | 1.6205 | 0.1051 | 0.5538 | 0.4846 |
| ar1 | 103 | 1.2275 | 0.2196 | 0.5534 | 0.4951 |
| logistic | 64 | -0.0000 | 1.0000 | 0.5125 | 0.5125 |

## Deflated Sharpe

| Signal | N | Trials | Annualized Sharpe | DSR |
| --- | --- | --- | --- | --- |
| crowd_weighted | 124 | 4 | -0.0079 | 0.1492 |
| crowd_unweighted | 124 | 4 | -0.0079 | 0.1492 |
| single_qwen | 124 | 4 | -0.5491 | 0.0856 |
| momentum_1d | 123 | 4 | 1.0756 | 0.3775 |
| momentum_5d | 119 | 4 | 1.3232 | 0.4608 |
| momentum_20d | 104 | 4 | 0.9715 | 0.3729 |
| ar1 | 103 | 4 | 0.4876 | 0.2579 |
| logistic | 64 | 4 | -3.0813 | 0.0044 |

## Per-Ticker Results

| Ticker | Signal | N | IC | Hit | Sharpe |
| --- | --- | --- | --- | --- | --- |
| BLNK | crowd_weighted | 124 | -0.0587 | 0.4677 | -0.4989 |
| BLNK | crowd_unweighted | 124 | -0.0743 | 0.4677 | -0.4989 |
| BLNK | single_qwen | 124 | 0.0331 | 0.4597 | -0.7325 |
| BLNK | momentum_1d | 123 | -0.0263 | 0.5083 | 0.4966 |
| BLNK | momentum_5d | 119 | -0.0952 | 0.4322 | -0.4045 |
| BLNK | momentum_20d | 104 | -0.0260 | 0.5000 | 0.5769 |
| BLNK | ar1 | 103 | -0.0912 | 0.5049 | 0.1550 |
| BLNK | logistic | 64 | 0.0230 | 0.4844 | -1.0037 |
| CHPT | crowd_weighted | 124 | -0.0125 | 0.4435 | -1.2759 |
| CHPT | crowd_unweighted | 124 | -0.0243 | 0.4435 | -1.2759 |
| CHPT | single_qwen | 124 | 0.0790 | 0.4516 | -0.6914 |
| CHPT | momentum_1d | 123 | 0.0078 | 0.5000 | -0.5621 |
| CHPT | momentum_5d | 119 | -0.1429 | 0.4622 | -0.9557 |
| CHPT | momentum_20d | 104 | -0.0031 | 0.4904 | 0.0123 |
| CHPT | ar1 | 103 | -0.0774 | 0.5146 | -0.6561 |
| CHPT | logistic | 64 | -0.0622 | 0.4375 | -1.2066 |
| EDIT | crowd_weighted | 124 | 0.1033 | 0.4758 | 1.5204 |
| EDIT | crowd_unweighted | 124 | 0.1015 | 0.4758 | 1.5204 |
| EDIT | single_qwen | 124 | 0.1180 | 0.4839 | -0.1022 |
| EDIT | momentum_1d | 123 | -0.0747 | 0.4250 | -0.3680 |
| EDIT | momentum_5d | 119 | -0.0924 | 0.5263 | 0.7542 |
| EDIT | momentum_20d | 104 | -0.0837 | 0.5000 | 1.3483 |
| EDIT | ar1 | 103 | -0.0105 | 0.4757 | 1.8848 |
| EDIT | logistic | 64 | -0.2687 | 0.3281 | -5.3345 |
| NVNI | crowd_weighted | 124 | 0.0678 | 0.4194 | 0.1458 |
| NVNI | crowd_unweighted | 124 | 0.0651 | 0.4194 | 0.1458 |
| NVNI | single_qwen | 124 | 0.1050 | 0.4032 | 0.0633 |
| NVNI | momentum_1d | 123 | -0.0759 | 0.4508 | 1.4756 |
| NVNI | momentum_5d | 119 | 0.0721 | 0.5678 | 1.5189 |
| NVNI | momentum_20d | 104 | -0.1104 | 0.5000 | -0.4760 |
| NVNI | ar1 | 103 | -0.1968 | 0.4660 | -1.0040 |
| NVNI | logistic | 64 | -0.0025 | 0.6094 | -1.5814 |
| TLRY | crowd_weighted | 124 | 0.1289 | 0.3790 | -1.9758 |
| TLRY | crowd_unweighted | 124 | 0.1312 | 0.3790 | -1.9758 |
| TLRY | single_qwen | 124 | 0.1211 | 0.3871 | -1.9512 |
| TLRY | momentum_1d | 123 | -0.1350 | 0.5250 | -0.3570 |
| TLRY | momentum_5d | 119 | -0.0309 | 0.5210 | 0.3418 |
| TLRY | momentum_20d | 104 | -0.0175 | 0.5865 | 2.2470 |
| TLRY | ar1 | 103 | 0.1539 | 0.5631 | 1.7378 |
| TLRY | logistic | 64 | 0.1428 | 0.5781 | 1.0389 |

## Herding Diagnostics

- Mean daily decision entropy: `1.0348` bits.
- Median daily decision entropy: `1.0536` bits.
- Minimum daily decision entropy: `0.4774` bits.
