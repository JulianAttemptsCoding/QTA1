# BUDGET.md — Vertex job cost ledger (R5)

HARD STOP: do NOT launch the next job if cumulative estimate would exceed **$85**.
Assumptions: spot `n1-standard-8` + 1x T4 ≈ **$0.30/hr** (PLAN §6); on-demand fallback ≈ **$0.75/hr** (only for jobs ≤ 2h). Prefer spot.

| # | job id | display name | machine | gpu | spot | wall h | $/hr | est $ | cumulative $ |
|---|--------|--------------|---------|-----|------|--------|------|-------|--------------|
| — | — | (none launched yet) | — | — | — | 0 | — | 0.00 | 0.00 |
