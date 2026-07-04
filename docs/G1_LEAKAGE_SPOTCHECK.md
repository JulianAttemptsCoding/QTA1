# G1 Leakage Spot Check

- Generated UTC: 2026-07-04T13:21:41+00:00
- Method: deterministic ticker/date checks rendered from frozen snapshots via the production prompt templates (L-01).
- PASS: no rendered prompt includes bars or news dated after its as-of date.

| Kind | Symbol | As-of | Bars | News | Max bar | Max news | Post-asof | Prompt SHA |
|---|---|---|---:|---:|---|---|---:|---|
| oos | NVNI | 2025-01-15 | 9 | 1 | 2025-01-15 | 2025-01-15 | 0 | c352feeb6f6b3ba7 |
| oos | TLRY | 2025-03-17 | 30 | 5 | 2025-03-17 | 2025-03-17 | 0 | 567a1768757cbb35 |
| oos | EDIT | 2025-06-16 | 30 | 5 | 2025-06-16 | 2025-06-12 | 0 | ea1dfca087c68634 |
| oos | CHPT | 2025-09-15 | 30 | 5 | 2025-09-15 | 2025-09-08 | 0 | 79db9a049fa255d6 |
| oos | BLNK | 2026-01-15 | 30 | 5 | 2026-01-15 | 2026-01-12 | 0 | af37f365c5cd0b61 |
| oos | FRSX | 2026-03-16 | 30 | 5 | 2026-03-16 | 2026-03-16 | 0 | fe2461633bdf6eeb |
| oos | TPET | 2026-06-15 | 30 | 5 | 2026-06-15 | 2026-06-11 | 0 | 2f8857664fcb4ed4 |

Result: **PASS**.
