# RQ3 OOS Prediction Report

- Source: frozen P4 alias-arm Vertex artifacts.
- Forecast target: next-trading-day close-to-close return.
- DM loss: directional 0-1 loss; negative DM favors the crowd.
- Baselines are walk-forward and use only information available by each decision date.

## Pooled Results

| Signal | N | IC | IC 2.5% | IC 97.5% | Hit | Hit 2.5% | Hit 97.5% | Sharpe |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| crowd_weighted | 1240 | 0.0276 | -0.0281 | 0.0775 | 0.4363 | 0.4048 | 0.4556 | -0.1329 |
| crowd_unweighted | 1240 | 0.0266 | -0.0302 | 0.0778 | 0.4363 | 0.4048 | 0.4556 | -0.1329 |
| single_qwen | 1240 | 0.0518 | 0.0109 | 0.1229 | 0.4379 | 0.4065 | 0.4589 | -0.4741 |
| momentum_1d | 1230 | -0.0825 | -0.1446 | -0.0410 | 0.4544 | 0.4246 | 0.4765 | -0.0016 |
| momentum_5d | 1190 | -0.0620 | -0.1204 | -0.0167 | 0.4810 | 0.4544 | 0.5069 | 0.0550 |
| momentum_20d | 1040 | 0.0098 | -0.0492 | 0.0595 | 0.5058 | 0.4744 | 0.5325 | 1.0653 |
| ar1 | 1030 | -0.0014 | -0.0615 | 0.0577 | 0.4913 | 0.4650 | 0.5223 | 0.6867 |
| logistic | 640 | -0.0276 | -0.0954 | 0.0336 | 0.4578 | 0.4250 | 0.4954 | -3.6416 |

## Diebold-Mariano vs Crowd

| Baseline | N | DM | p | Crowd error | Baseline error |
| --- | --- | --- | --- | --- | --- |
| crowd_unweighted | 124 | 0.0000 | 1.0000 | 0.5637 | 0.5637 |
| single_qwen | 124 | 0.5781 | 0.5632 | 0.5637 | 0.5621 |
| momentum_1d | 123 | 0.1544 | 0.8773 | 0.5659 | 0.5618 |
| momentum_5d | 119 | 1.1630 | 0.2448 | 0.5639 | 0.5294 |
| momentum_20d | 104 | 1.7628 | 0.0779 | 0.5558 | 0.4962 |
| ar1 | 103 | 1.3540 | 0.1757 | 0.5563 | 0.5087 |
| logistic | 64 | -0.4199 | 0.6745 | 0.5219 | 0.5422 |

## Deflated Sharpe

| Signal | N | Trials | Annualized Sharpe | DSR |
| --- | --- | --- | --- | --- |
| crowd_weighted | 124 | 4 | -0.1329 | 0.1275 |
| crowd_unweighted | 124 | 4 | -0.1329 | 0.1275 |
| single_qwen | 124 | 4 | -0.4741 | 0.0866 |
| momentum_1d | 123 | 4 | -0.0016 | 0.1475 |
| momentum_5d | 119 | 4 | 0.0550 | 0.1615 |
| momentum_20d | 104 | 4 | 1.0653 | 0.3901 |
| ar1 | 103 | 4 | 0.6867 | 0.2961 |
| logistic | 64 | 4 | -3.6416 | 0.0022 |

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
| CCO | crowd_weighted | 124 | 0.0544 | 0.4274 | -0.1495 |
| CCO | crowd_unweighted | 124 | 0.0598 | 0.4274 | -0.1495 |
| CCO | single_qwen | 124 | 0.0209 | 0.4194 | -0.2942 |
| CCO | momentum_1d | 123 | -0.1810 | 0.3519 | -2.9548 |
| CCO | momentum_5d | 119 | -0.0179 | 0.4911 | -0.4714 |
| CCO | momentum_20d | 104 | 0.0428 | 0.4851 | 0.4118 |
| CCO | ar1 | 103 | 0.1582 | 0.4563 | 0.2283 |
| CCO | logistic | 64 | -0.1111 | 0.3281 | -2.9686 |
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
| FRSX | crowd_weighted | 124 | 0.0555 | 0.4194 | -2.0893 |
| FRSX | crowd_unweighted | 124 | 0.0472 | 0.4194 | -2.0893 |
| FRSX | single_qwen | 124 | -0.0135 | 0.4194 | -1.7855 |
| FRSX | momentum_1d | 123 | -0.0679 | 0.5289 | 0.7720 |
| FRSX | momentum_5d | 119 | -0.1473 | 0.4874 | -1.0533 |
| FRSX | momentum_20d | 104 | -0.0195 | 0.5481 | 0.7960 |
| FRSX | ar1 | 103 | 0.0382 | 0.5631 | 1.7598 |
| FRSX | logistic | 64 | -0.1620 | 0.4688 | 0.4614 |
| ICCM | crowd_weighted | 124 | 0.0972 | 0.4758 | -0.1868 |
| ICCM | crowd_unweighted | 124 | 0.0980 | 0.4758 | -0.1868 |
| ICCM | single_qwen | 124 | 0.0314 | 0.4839 | 0.0911 |
| ICCM | momentum_1d | 123 | -0.0887 | 0.4107 | -1.8526 |
| ICCM | momentum_5d | 119 | -0.1147 | 0.4144 | -1.2890 |
| ICCM | momentum_20d | 104 | -0.0537 | 0.4712 | 0.8820 |
| ICCM | ar1 | 103 | -0.0867 | 0.4660 | -0.6694 |
| ICCM | logistic | 64 | -0.2972 | 0.4062 | -3.5450 |
| NVNI | crowd_weighted | 124 | 0.0678 | 0.4194 | 0.1458 |
| NVNI | crowd_unweighted | 124 | 0.0651 | 0.4194 | 0.1458 |
| NVNI | single_qwen | 124 | 0.1050 | 0.4032 | 0.0633 |
| NVNI | momentum_1d | 123 | -0.0759 | 0.4508 | 1.4756 |
| NVNI | momentum_5d | 119 | 0.0721 | 0.5678 | 1.5189 |
| NVNI | momentum_20d | 104 | -0.1104 | 0.5000 | -0.4760 |
| NVNI | ar1 | 103 | -0.1968 | 0.4660 | -1.0040 |
| NVNI | logistic | 64 | -0.0025 | 0.6094 | -1.5814 |
| OGI | crowd_weighted | 124 | 0.1762 | 0.4435 | -0.1973 |
| OGI | crowd_unweighted | 124 | 0.1805 | 0.4435 | -0.1973 |
| OGI | single_qwen | 124 | 0.1408 | 0.4516 | -0.1117 |
| OGI | momentum_1d | 123 | -0.0496 | 0.3964 | -1.8366 |
| OGI | momentum_5d | 119 | 0.0180 | 0.4912 | 0.0556 |
| OGI | momentum_20d | 104 | 0.0736 | 0.4902 | 0.1828 |
| OGI | ar1 | 103 | -0.0902 | 0.4466 | -1.8922 |
| OGI | logistic | 64 | -0.0992 | 0.3750 | -3.0967 |
| TLRY | crowd_weighted | 124 | 0.1289 | 0.3790 | -1.9758 |
| TLRY | crowd_unweighted | 124 | 0.1312 | 0.3790 | -1.9758 |
| TLRY | single_qwen | 124 | 0.1211 | 0.3871 | -1.9512 |
| TLRY | momentum_1d | 123 | -0.1350 | 0.5250 | -0.3570 |
| TLRY | momentum_5d | 119 | -0.0309 | 0.5210 | 0.3418 |
| TLRY | momentum_20d | 104 | -0.0175 | 0.5865 | 2.2470 |
| TLRY | ar1 | 103 | 0.1539 | 0.5631 | 1.7378 |
| TLRY | logistic | 64 | 0.1428 | 0.5781 | 1.0389 |
| TPET | crowd_weighted | 124 | 0.0076 | 0.4113 | 0.8412 |
| TPET | crowd_unweighted | 124 | 0.0060 | 0.4113 | 0.8412 |
| TPET | single_qwen | 124 | -0.0198 | 0.4194 | 1.1057 |
| TPET | momentum_1d | 123 | -0.1732 | 0.4274 | -0.8803 |
| TPET | momentum_5d | 119 | -0.2929 | 0.4138 | -3.2870 |
| TPET | momentum_20d | 104 | -0.0858 | 0.4854 | -0.4480 |
| TPET | ar1 | 103 | -0.0241 | 0.4563 | 1.4200 |
| TPET | logistic | 64 | 0.0765 | 0.5625 | 0.7344 |

## Herding Diagnostics

- Mean daily decision entropy: `1.0251` bits.
- Median daily decision entropy: `1.0339` bits.
- Minimum daily decision entropy: `0.4471` bits.
