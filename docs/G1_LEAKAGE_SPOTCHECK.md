# G1 Leakage Spot Check

- Generated UTC: 2026-07-03T05:16:55+00:00
- Method: 10 deterministic ticker/date checks rendered from frozen snapshots using the production prompt templates.
- PASS condition: no rendered prompt includes bars or news after its as-of date.

| Kind | Symbol | As-of | Bars | News | Max included bar | Max included news | Post-asof included | Prompt SHA-256 |
|---|---|---|---:|---:|---|---|---:|---|
| calib | IIPR | 2019-07-15 | 10 | 5 | 2019-07-15T04:00:00Z | 2019-07-15T20:21:37Z | 0 | 61d4afd0cacfb64a50f1c4e2045148b7f13aeb914906aad4e0519d0aa526cccc |
| calib | IGC | 2019-09-03 | 30 | 5 | 2019-09-03T04:00:00Z | 2019-08-20T20:21:48Z | 0 | 92f2a246e014a54e4ef724843f4e772ede44805099f46d363ac7a6baac704b3f |
| calib | GOLD | 2019-12-16 | 30 | 5 | 2019-12-16T05:00:00Z | 2019-12-11T15:46:35Z | 0 | 12910db92e02241cd02d399d8ac549519ce24668acb9c4264656b165684e561c |
| oos | CHPT | 2025-01-15 | 9 | 1 | 2025-01-15T05:00:00Z | 2025-01-14T18:56:17Z | 0 | 5252bcae3a488934c1fa0b4bd3521b2196ae5c38df9a82a62bdbb511c3df606c |
| oos | BLNK | 2025-03-17 | 30 | 5 | 2025-03-17T04:00:00Z | 2025-03-16T15:38:04Z | 0 | cb94348969fdc0e7043aaf6bc3ad7479abcfcfa2d4baba69b3a3554f391b4843 |
| oos | FRSX | 2025-06-16 | 30 | 5 | 2025-06-16T04:00:00Z | 2025-05-19T12:35:07Z | 0 | 0324e12fa1211c77487db23dad5e821837c2f7ab5004907b9e088fce3b94def4 |
| oos | TPET | 2025-09-15 | 30 | 5 | 2025-09-15T04:00:00Z | 2025-09-12T20:57:37Z | 0 | 665de9efd4d6387daa7cd86c744fac452a3cf94926424da10165f163de142d9f |
| oos | OGI | 2026-01-15 | 30 | 5 | 2026-01-15T05:00:00Z | 2025-12-31T11:03:25Z | 0 | b7d7e32a97502a4c7b1f6df3154ec8ff7cabc14cd149aa18c05e4be1e159fbd3 |
| oos | CCO | 2026-03-16 | 30 | 5 | 2026-03-16T04:00:00Z | 2026-03-12T12:18:06Z | 0 | 4644b7b7f64ad7745907b8a18f2f554055a4ee9782d6aa9d64a98db563cab4c5 |
| oos | ICCM | 2026-06-15 | 30 | 5 | 2026-06-15T04:00:00Z | 2026-06-09T17:06:11Z | 0 | 30a88bbd8775658a92f74872d7bdae675affb398f6c99a0e2d763c89da2dfa20 |

Result: **PASS**.
