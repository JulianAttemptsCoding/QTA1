# G1 Frozen Universes

- Generated UTC: 2026-07-03T05:16:55+00:00
- Status: **G1 universe freeze complete; snapshot hash manifest generated**
- CALIB selection date: 2019-06-28
- CALIB window: 2019-07-01 through 2019-12-31
- OOS selection date: 2024-12-20
- OOS window: 2025-01-02 through 2026-06-30
- OOS start is after the latest enabled model release/cutoff proxy from G0.

## CALIB-2019

Rule implementation: rank valid small-cap common-share candidates by Robintrack holders / SEC shares outstanding as of the selection date.

| Rank | Ticker | Price | Market cap | Metric | Notes |
|---:|---|---:|---:|---:|---|
| 1 | IIPR | 123.56 | 1211653331 | 0.00153189 | holders=15022 |
| 2 | IGC | 1.64 | 64798707 | 0.00138724 | holders=54812 |
| 3 | GOLD | 13.05 | 91760422 | 0.00109138 | holders=7674 |
| 4 | RIOT | 3.14 | 50105165 | 0.00100269 | holders=16000 |
| 5 | CRBP | 6.93 | 446674682 | 0.00060827 | holders=39206 |
| 6 | BLNK | 2.68 | 70314635 | 0.00048539 | holders=12735 |
| 7 | PLUG | 2.25 | 552183048 | 0.00047572 | holders=116749 |
| 8 | XXII | 2.09 | 260539400 | 0.00040290 | holders=50226 |
| 9 | LEVI | 20.88 | 785147362 | 0.00033787 | holders=12705 |
| 10 | VKTX | 8.30 | 597995553 | 0.00032480 | holders=23401 |

## OOS-2025

Retail-attention score frozen before inference: z(news_count_60d) + z(dollar_volume_spike) + 0.5*z(1/price), after Alpaca active-equity, price, SEC shares, and market-cap filters.

| Rank | Ticker | Price | Market cap | Metric | Notes |
|---:|---|---:|---:|---:|---|
| 1 | NVNI | 8.58 | 237949131 | 8.01143588 | news60=18; dv_spike=168022.271; lot_proxy=0.1166 |
| 2 | TLRY | 1.26 | 1138140684 | 4.71189283 | news60=42; dv_spike=1.224; lot_proxy=0.7937 |
| 3 | EDIT | 1.31 | 108138010 | 3.23593963 | news60=32; dv_spike=1.000; lot_proxy=0.7634 |
| 4 | CHPT | 1.24 | 548502684 | 2.70072345 | news60=27; dv_spike=2.306; lot_proxy=0.8065 |
| 5 | BLNK | 1.49 | 150751355 | 1.54450911 | news60=22; dv_spike=1.511; lot_proxy=0.6711 |
| 6 | FRSX | 1.25 | 574722570 | 1.18952379 | news60=16; dv_spike=355.867; lot_proxy=0.8000 |
| 7 | TPET | 1.11 | 55864444 | 1.11102695 | news60=13; dv_spike=8.370; lot_proxy=0.9009 |
| 8 | OGI | 1.56 | 169393368 | 1.02859301 | news60=19; dv_spike=2.405; lot_proxy=0.6410 |
| 9 | CCO | 1.38 | 674928226 | 0.90858632 | news60=16; dv_spike=5.393; lot_proxy=0.7246 |
| 10 | ICCM | 1.12 | 51217246 | 0.80856132 | news60=11; dv_spike=1.460; lot_proxy=0.8929 |

## Raw Data Policy

Raw snapshots live under ignored `data/snapshots/g1/`; only hashes and metadata are committed.
