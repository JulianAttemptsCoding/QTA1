# P4 Follow-Up Report

- Source: completed A-402/A-403 Vertex artifacts only.
- Incomplete or budget-cancelled shards are listed in coverage and excluded from metrics.
- Scaling N1000 was budget-cancelled before completion; preserved partial outputs are reported for audit only, not interpreted as results.

## Coverage

| Config | Ticker | Status | Outputs | Expected | Sim days |
| --- | --- | --- | --- | --- | --- |
| news_off_n100 | NVNI | complete | 6000 | 6000 | 60 |
| news_off_n100 | TLRY | complete | 6000 | 6000 | 60 |
| personas_off_n100 | NVNI | complete | 6000 | 6000 | 60 |
| personas_off_n100 | TLRY | complete | 6000 | 6000 | 60 |
| scaling_n100 | NVNI | complete | 6000 | 6000 | 60 |
| scaling_n100 | TLRY | complete | 6000 | 6000 | 60 |
| scaling_n1000 | NVNI | budget_cancelled_partial | 10752 | 60000 | 0 |
| scaling_n1000 | TLRY | budget_cancelled_partial | 1408 | 60000 | 0 |
| scaling_n300 | NVNI | complete | 18000 | 18000 | 60 |
| scaling_n300 | TLRY | complete | 18000 | 18000 | 60 |
| scaling_n50 | NVNI | complete | 3000 | 3000 | 60 |
| scaling_n50 | TLRY | complete | 3000 | 3000 | 60 |

## Scaling Metrics

| Scope | Config | Weighting | Days | N | IC | Hit | Sharpe | Entropy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NVNI | scaling_n100 | weighted | 60 | 59 | -0.0397 | 0.4576 | -0.7234 | 1.0774 |
| NVNI | scaling_n100 | unweighted | 60 | 59 | -0.0441 | 0.4576 | -0.7234 | 1.0774 |
| TLRY | scaling_n100 | weighted | 60 | 59 | 0.1058 | 0.3220 | -4.2287 | 1.0542 |
| TLRY | scaling_n100 | unweighted | 60 | 59 | 0.1355 | 0.3220 | -4.2287 | 1.0542 |
| NVNI | scaling_n300 | weighted | 60 | 59 | 0.1408 | 0.4576 | -0.7234 | 1.0561 |
| NVNI | scaling_n300 | unweighted | 60 | 59 | 0.1351 | 0.4576 | -0.7234 | 1.0561 |
| TLRY | scaling_n300 | weighted | 60 | 59 | 0.2577 | 0.3220 | -4.2287 | 1.0447 |
| TLRY | scaling_n300 | unweighted | 60 | 59 | 0.2836 | 0.3220 | -4.2287 | 1.0447 |
| NVNI | scaling_n50 | weighted | 60 | 59 | -0.0322 | 0.4576 | -0.7234 | 1.0412 |
| NVNI | scaling_n50 | unweighted | 60 | 59 | -0.0340 | 0.4576 | -0.7234 | 1.0412 |
| TLRY | scaling_n50 | weighted | 60 | 59 | 0.1925 | 0.3220 | -4.2287 | 1.0216 |
| TLRY | scaling_n50 | unweighted | 60 | 59 | 0.2389 | 0.3220 | -4.2287 | 1.0216 |
| ALL | scaling_n100 | weighted | 60 | 118 | -0.0115 | 0.3898 | -1.3280 | 1.0658 |
| ALL | scaling_n100 | unweighted | 60 | 118 | -0.0033 | 0.3898 | -1.3280 | 1.0658 |
| ALL | scaling_n300 | weighted | 60 | 118 | 0.1543 | 0.3898 | -1.3280 | 1.0504 |
| ALL | scaling_n300 | unweighted | 60 | 118 | 0.1579 | 0.3898 | -1.3280 | 1.0504 |
| ALL | scaling_n50 | weighted | 60 | 118 | 0.0629 | 0.3898 | -1.3280 | 1.0314 |
| ALL | scaling_n50 | unweighted | 60 | 118 | 0.0736 | 0.3898 | -1.3280 | 1.0314 |

## Ablation Metrics

| Scope | Config | Weighting | Days | N | IC | Hit | Sharpe | Entropy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NVNI | news_off_n100 | weighted | 60 | 59 | 0.0533 | 0.4576 | -0.7234 | 1.0668 |
| NVNI | news_off_n100 | unweighted | 60 | 59 | 0.0445 | 0.4576 | -0.7234 | 1.0668 |
| TLRY | news_off_n100 | weighted | 60 | 59 | 0.1983 | 0.3220 | -4.2287 | 1.0079 |
| TLRY | news_off_n100 | unweighted | 60 | 59 | 0.1697 | 0.3220 | -4.2287 | 1.0079 |
| NVNI | personas_off_n100 | weighted | 60 | 59 | 0.0904 | 0.4576 | -0.7234 | 0.4096 |
| NVNI | personas_off_n100 | unweighted | 60 | 59 | 0.0876 | 0.4576 | -0.7234 | 0.4096 |
| TLRY | personas_off_n100 | weighted | 60 | 59 | 0.1565 | 0.3220 | -4.2287 | 0.4719 |
| TLRY | personas_off_n100 | unweighted | 60 | 59 | 0.1672 | 0.3220 | -4.2287 | 0.4719 |
| ALL | news_off_n100 | weighted | 60 | 118 | 0.0832 | 0.3898 | -1.3280 | 1.0373 |
| ALL | news_off_n100 | unweighted | 60 | 118 | 0.0690 | 0.3898 | -1.3280 | 1.0373 |
| ALL | personas_off_n100 | weighted | 60 | 118 | 0.1072 | 0.3898 | -1.3280 | 0.4407 |
| ALL | personas_off_n100 | unweighted | 60 | 118 | 0.1091 | 0.3898 | -1.3280 | 0.4407 |

## Ablation Delta vs Scaling N100

| Scope | Ablation | Weighting | IC delta | Hit delta | Sharpe delta | Entropy delta |
| --- | --- | --- | --- | --- | --- | --- |
| NVNI | news_off_n100 | weighted | 0.0930 | 0.0000 | 0.0000 | -0.0106 |
| NVNI | personas_off_n100 | weighted | 0.1302 | 0.0000 | 0.0000 | -0.6678 |
| NVNI | news_off_n100 | unweighted | 0.0886 | 0.0000 | 0.0000 | -0.0106 |
| NVNI | personas_off_n100 | unweighted | 0.1318 | 0.0000 | 0.0000 | -0.6678 |
| TLRY | news_off_n100 | weighted | 0.0925 | 0.0000 | 0.0000 | -0.0463 |
| TLRY | personas_off_n100 | weighted | 0.0507 | 0.0000 | 0.0000 | -0.5823 |
| TLRY | news_off_n100 | unweighted | 0.0343 | 0.0000 | 0.0000 | -0.0463 |
| TLRY | personas_off_n100 | unweighted | 0.0317 | 0.0000 | 0.0000 | -0.5823 |
| ALL | news_off_n100 | weighted | 0.0947 | 0.0000 | 0.0000 | -0.0285 |
| ALL | personas_off_n100 | weighted | 0.1187 | 0.0000 | 0.0000 | -0.6251 |
| ALL | news_off_n100 | unweighted | 0.0723 | 0.0000 | 0.0000 | -0.0285 |
| ALL | personas_off_n100 | unweighted | 0.1124 | 0.0000 | 0.0000 | -0.6251 |
