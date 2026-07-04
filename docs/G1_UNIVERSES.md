# G1 Frozen Universes

- Generated UTC: 2026-07-04T13:21:41+00:00
- CALIB: PENDING (Robintrack export required) — selection 2019-06-28, window 2019-07-01..2019-12-31
- OOS: FROZEN — selection 2024-12-20, window 2025-01-02..2026-06-30
- OOS start is strictly after the max enabled-model cutoff from G0 (D-04).

## CALIB-2019

Rank valid small-cap common shares by Robintrack holders / SEC shares outstanding as of the selection date (U-C1..U-C4).

_PENDING: not yet frozen (see status above)._

## OOS-2025

Retail-attention score frozen before inference: z(news_count_60d) + z(dollar_volume_spike) + 0.5*z(1/price), after Alpaca active-common, price, SEC shares, and $50M-$2B market-cap filters (U-O1..U-O3).

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

Raw snapshots live under gitignored `data/snapshots/g1/`; only SHA-256 hashes and metadata (docs/G1_SNAPSHOT_MANIFEST.json) are committed.
