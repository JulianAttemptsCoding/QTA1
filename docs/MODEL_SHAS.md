# MODEL_SHAS.md

Resolved HF commit SHAs for the cached agent models (P-17 model_cache job
`2444747620275453952`, 2026-07-03). SHAs pin the exact weights used; `revision`
in `configs/models.yaml` is set from this table. Cache lives at
`gs://project-82d97cf9-5889-43a4-850-agorasim/agorasim/models/<org>__<name>/`.

| Model | Status | Revision SHA | GCS cache dir |
|---|---|---|---|
| Qwen/Qwen2.5-1.5B-Instruct | OK | 989aa7980e4cf806f80c7fef2b1adb7bc71aa306 | models/Qwen__Qwen2.5-1.5B-Instruct |
| Qwen/Qwen2.5-3B-Instruct | OK | aa8e72537993ba99e69dfaafa59ed015b17504d1 | models/Qwen__Qwen2.5-3B-Instruct |
| microsoft/Phi-3.5-mini-instruct | OK | 2fe192450127e6a83f7441aef6e3ca586c338b77 | models/microsoft__Phi-3.5-mini-instruct |
| HuggingFaceTB/SmolLM2-1.7B-Instruct | OK | 31b70e2e869a7173562077fd711b654946d38674 | models/HuggingFaceTB__SmolLM2-1.7B-Instruct |
| meta-llama/Llama-3.2-3B-Instruct | SKIP (gated 403) | - | - |
| google/gemma-2-2b-it | SKIP (gated 403) | - | - |

Gated repos (Llama-3.2-3B, gemma-2-2b) returned `GatedRepoError: 403`; the HF
token has not accepted their licenses. Per P-05 they are skipped (non-fatal);
the four ungated models proceed to GATE G0 throughput.
