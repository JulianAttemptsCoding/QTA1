# P4_PILOT — sim-engine end-to-end validation (run-id oos-pilot-v2)

Generated (UTC): 2026-07-05

**Result: the full RQ3 sim pipeline works end-to-end on real frozen OOS data.**

## Setup

- Roster: Qwen2.5-1.5B, Qwen2.5-3B, Phi-3.5-mini (worker:v15), one Vertex T4-spot job each,
  parallel. Arm: **alias**. Tickers: TLRY, CHPT. 30 agents/model × 20 point-in-time days.
- Crowd = union of the three per-model sub-crowds → **90 agents/ticker-day**.
- Pipeline: `run_sim_phase.py` (render → guided-decode `run_offline` → raw decisions to GCS)
  → `collect_sim_phase.py` (pool per (ticker, day) → flow_imbalance + call_auction).

## Signals

| metric | value |
|---|---|
| total decisions | 3600 |
| valid-JSON rate | **0.9994** (2/3600 invalid) |
| ticker-days | 40 (2 × 20) |
| decisions/ticker-day | ~90 |
| flow_imbalance (conf-wtd) | min −0.308, max +0.978, mean **+0.523**, nonzero 40/40 |
| auction | crossing volume on 40/40 days (max 9872 sh) |

Signals are non-degenerate: the crowd produces a varying daily order-flow imbalance and a
clearing auction every day. `gs://…/runs/oos-pilot-v2/signals.jsonl`.

## Findings (fold into the full P4 run)

1. **Throughput** — real ~900–1000-token prompts (30 bars + 5 news) are slow to prefill on
   T4: ~256 decisions per ~8 min, ~1900/hr, well below the G0 synthetic-prompt rate. The full
   P4 (250k decisions) needs prompt trimming (≈20 bars / 3 news), `max_model_len` 2048, and a
   larger per-call batch (≈512) before launch, or it blows the time/budget envelope.
2. **Host-RAM OOM (fixed)** — the first pilot OOM-ed the n1-standard-8 host by handing vLLM the
   whole run at once; `run_offline` now feeds 256 prompts/call with `swap_space=2` (commit
   94bbb44).
3. **Alias-arm de-anonymization** — in the alias arm the ticker LABEL is hidden, but real news
   headlines still name the company (a Phi rationale referenced "tilray"). The named-vs-alias
   contrast therefore measures *label* memorization only; for a stricter test the news text
   would also need aliasing. Documented as a limitation (contamination probes at A-202 already
   showed zero post-cutoff price recall, so leakage risk to RQ3 is low).
4. **Collector auth** — `collect_sim_phase.py` via the google-cloud-storage client uses local
   ADC, which resolves to an account without bucket access; run the collector on the Vertex
   worker (service-account creds) or `gcloud auth application-default login` locally. For this
   pilot the raw was pulled with the `gcloud` CLI and aggregated locally.

## Next

Optimize per finding #1, register the RQ3 trials in docs/TRIALS.md, launch the full OOS main
run (10 tickers × ~100–200 agents × ~125 days, alias primary), then P5 stats (IC/DM/DSR vs the
D-09 baselines).
