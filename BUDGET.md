# BUDGET.md — Vertex job cost ledger (R5)

HARD STOP: do NOT launch the next job if cumulative estimate would exceed **$85**.
Assumptions: spot `n1-standard-8` + 1x T4 ≈ **$0.30/hr** (PLAN §6); on-demand fallback ≈ **$0.75/hr** (only for jobs ≤ 2h). Prefer spot.

On-demand `n1-standard-8` (no GPU) ≈ **$0.38/hr** (model_cache download job; on-demand for reliability, no preemption mid-download).

| # | job id | display name | machine | gpu | spot | wall h | $/hr | est $ | cumulative $ |
|---|--------|--------------|---------|-----|------|--------|------|-------|--------------|
| 1 | 2444747620275453952 | agorasim-model-cache | n1-standard-8 | none | no | 0.14 | 0.38 | 0.05 | 0.05 |
| 2 | (g0-thru x4 serial) | agorasim-g0-thru-* | n1-standard-8 | T4 | yes | ~0.8 tot | 0.30 | ~0.24 | ~0.29 |
