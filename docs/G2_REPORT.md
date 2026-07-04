# G2_REPORT — agent bring-up gate (P2 / A-201, A-203)

Generated (UTC): 2026-07-04

**GATE G2 (valid-JSON): PASS**

Kill criterion (PLAN §G2): valid-JSON < 99% after 3 prompt iterations on ≥ 2 model families →
drop failing families; if < 2 families survive, STOP. Result: **2 families survive at 100%**
(Qwen, Phi) → PASS. SmolLM2 dropped.

## Real-model smoke (A-203)

Production inference path (`agents/vllm_batch.run_offline`, guided JSON decoding) run on a
real frozen OOS ticker (TLRY), 20 personas × 10 point-in-time decision days = 200 decisions
per model, named arm, worker:v12. Prompts assembled by `agents/sim_prompts.build_requests`
(leakage L-01 enforced; verified 0 look-ahead in the G1 spot-check and unit tests).

| model | family | valid_json_rate | n | verdict |
|---|---|---:|---:|---|
| Qwen/Qwen2.5-1.5B-Instruct | Qwen | 1.000 | 200 | KEEP |
| Qwen/Qwen2.5-3B-Instruct | Qwen | 1.000 | 200 | KEEP |
| microsoft/Phi-3.5-mini-instruct | Phi | 1.000 | 200 | KEEP |
| HuggingFaceTB/SmolLM2-1.7B-Instruct | SmolLM2 | 0.960 | 200 | **DROP** (< 0.99) |

### Why SmolLM2 was dropped

Its 8/200 invalid outputs were genuine model-quality failures that guided decoding did not
fully prevent (not a prompt bug): negative share quantities (`"qty": -10`), a malformed
object, and — most tellingly — **prompt regurgitation** (echoing the input bar block back
instead of emitting a decision). These are not fixable by prompt iteration and would not be
honestly repaired by loosening the parser (a negative share count is a real error, unlike the
benign `limit_price: 0` market-order placeholder that IS coerced). Per the G2 rule, drop the
failing family; 2 families still survive, so the gate holds.

## Surviving model roster (post-G2)

- **Qwen family:** Qwen2.5-1.5B-Instruct (3885 dec/hr), Qwen2.5-3B-Instruct (3034 dec/hr) —
  fast, carry the high-volume P4 shards.
- **Phi family:** Phi-3.5-mini-instruct (1985 dec/hr) — throughput-marginal but valid-JSON
  perfect; provides the second family for the crowd-diversity / anonymization contrasts (D-06,
  D-08). Given the two viable families, agent-diversity via family × persona × temperature ×
  seed (D-07) is satisfied.

## Remaining P2 work

- A-202 contamination (C-2) recall probes → per (model, ticker) exclusion matrix. C-1 (cutoff
  gate) is satisfied by construction: the OOS window (2025-01-02 →) starts strictly after every
  enabled model's release. C-3 (named-vs-alias A/B) is wired (`sim_prompts` alias arm) and
  measured in the P3/P4 experiments.

## Provenance

- Worker image: `.../agorasim/worker:v12`; entrypoint `scripts/p2_gate_real_model.py`.
- Jobs (us-central1, T4 SPOT, parallel via quota=4): Qwen1.5B 2705285696569999360,
  Qwen3B 224365251842277376, SmolLM2 3815423004716826624, Phi-3.5 1330561910315155456.
- Raw results: `gs://…/agorasim/runs/g2_smoke/<model>__TLRY_named.json`.
