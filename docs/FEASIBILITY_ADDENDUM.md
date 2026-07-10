# G0 Feasibility Addendum

- Generated UTC: 2026-07-03T04:31:00Z
- Gate: **G0-PASS**
- Evidence: `docs/G0_REPORT.md`, `docs/G0_THROUGHPUT.md`, `docs/MODEL_SHAS.md`
- Compute location: Vertex AI custom jobs in `us-central1`
- Worker: `n1-standard-8` + 1x NVIDIA_TESLA_T4, spot scheduling
- Model weights: downloaded and cached by Vertex jobs under
  `gs://project-82d97cf9-5889-43a4-850-agorasim/agorasim/models`

## Kill Criteria Check

| Criterion | Threshold | Result | Status |
|---|---:|---:|---|
| Workable historical bar feed for small caps | required | Alpaca default/IEX/SIP probes returned bars for KOSS, MVIS, and SNDL | PASS |
| News history usable | required | Alpaca news probe returned historical articles back to 2018-01-01 in sample | PASS |
| Throughput on selectable worker/model | >= 2,000 decisions/hour | SmolLM2 measured 4,747 decisions/hour | PASS |
| Valid JSON rate | >= 0.900 | Lowest accepted G0 rate was 0.988 | PASS |

## Throughput Measurements

| Model | Decisions/hour | Valid JSON | G0 use |
|---|---:|---:|---|
| `HuggingFaceTB/SmolLM2-1.7B-Instruct` | 4,747 | 0.988 | Primary budget model |
| `Qwen/Qwen2.5-1.5B-Instruct` | 2,541 | 1.000 | Diversity / fallback |
| `Qwen/Qwen2.5-3B-Instruct` | 2,203 | 0.990 | Diversity / fallback |
| `microsoft/Phi-3.5-mini-instruct` | 1,907 | 1.000 | Diversity only unless budget allows |

The final selected budget rate is the best passing worker/model measurement:
4,747 decisions/hour. Phi is kept as a diversity candidate but not as the cost
baseline because it falls just below the 2,000 decisions/hour planning threshold.

## Budget Update

Original planning rate: 5,000 decisions/hour. G0 selected rate: 4,747
decisions/hour. This changes the planned 710k-decision program from roughly 142
T4-hours to roughly 150 T4-hours. At the `$0.30/hr` spot planning rate, the core
GPU budget is about `$45`; with contingency and fallback risk the full envelope is
still about `$61-76`, inside the `$100` project cap.

Actual P0 Vertex spend recorded through G0 is `$0.50` in `BUDGET.md`.

## Decision

G0 is passed. Proceed to P1 with no active Vertex jobs and no local LLM weights or
local inference artifacts.
