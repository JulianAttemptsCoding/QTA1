# G0_THROUGHPUT — compute reality gate (A-003)

Generated (UTC): 2026-07-03

**GATE G0 (compute): PASS**

Kill criteria (PLAN §G0): a model is viable iff `decisions_per_hour >= 2000` AND
`valid_json_rate >= 0.90`. Gate PASSES if the viable roster is large enough to run the
crowd sim (>= 2 models across size tiers). Result: 3/4 probed models are solidly viable and
the valid-JSON problem is fully solved (all >= 0.996), so the LLM-crowd approach is compute-feasible on a single T4.

## Results (vLLM 0.6.4.post1, T4 sm_75 fp16, guided JSON decoding, n=512 decisions/model)

| model | valid_json_rate | decisions_per_hour | secs (512) | invalid | viable |
|---|---|---|---|---|---|
| Qwen/Qwen2.5-1.5B-Instruct | 1.0000 | 3885 | 474 | 0 | YES |
| Qwen/Qwen2.5-3B-Instruct | 1.0000 | 3034 | 608 | 0 | YES |
| HuggingFaceTB/SmolLM2-1.7B-Instruct | 0.9961 | 4859 | 379 | 2 | YES |
| microsoft/Phi-3.5-mini-instruct | 1.0000 | 1985 | 929 | 0 | MARGINAL (thruput 1985 < 2000) |

Gated models (meta-llama/Llama-3.2-3B-Instruct, google/gemma-2-2b-it): SKIP — HF token
license not accepted (403 at model_cache; see docs/MODEL_SHAS.md). Not probed.

## Decision

- **Viable roster (3):** Qwen2.5-1.5B, Qwen2.5-3B, SmolLM2-1.7B — all clear both bars with
  margin. Spans two size tiers (1.5B / 1.7B / 3B) for the scaling/ablation arms.
- **Phi-3.5-mini:** valid-JSON perfect (1.0) but throughput 1985 dec/hr is 0.75% under the
  2000 bar (largest model, enforce_eager=True disables CUDA graphs, plus guided-decode
  overhead). Kept as an OPTIONAL/deprioritized model; not required for the gate.
- G0 (compute) PASS. Combined with G0 (data) PASS (docs/G0_REPORT.md), **GATE G0 is cleared.**

## How the valid-JSON gate was solved (root cause)

Free-form / chat-mode generation drove valid-JSON to ~0.18: the instruct models, prompted
via the chat template (`llm.chat`), answered in verbose assistant mode and their multi-clause
rationales overflowed the 160-token budget, truncating the JSON mid-string. Fixes, in order
of impact:

1. **Guided JSON decoding** — `GuidedDecodingParams(json=SCHEMA, backend="lm-format-enforcer")`
   constrains output to the AgentDecision schema (avoids the `outlines` backend, which pulls a
   broken `pyairports` dep). Requires `transformers==4.46.3` (newer drop `LogitsWarper`).
2. **Raw-completion prompts + max_model_len 4096** — feed `f"{system}\n\n{user}"` through
   `llm.generate` (NOT `llm.chat`); this yields terse rationales that close within budget. The
   single largest lever (0.18 -> 1.0).
3. **limit_price coercion** — schema/parse coerces non-positive `limit_price` (0) to None so
   market-order decisions that emit `limit_price: 0` validate (fixed Qwen3B/Phi mass-invalids).

## Provenance

- Worker image: `us-central1-docker.pkg.dev/project-c779f701-1a49-4a58-b54/agorasim/worker:v11`
- Probe: `python -m agorasim.infra.throughput_probe --base <BASE> --model <ID> --n 512`
- Jobs (us-central1, T4 SPOT, parallel via quota bump 1->4): Qwen1.5B 1439756609092845568,
  Qwen3B 6894741657745358848, Phi-3.5 4645193643873796096, SmolLM2 2339350634660102144.
- Raw results: `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/g0_throughput/*.json`
