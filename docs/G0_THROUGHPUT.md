# G0 Throughput Gate Report

- Overall: **PASS**
- Gate detail: Best measured throughput 4747/hour; lowest valid-JSON rate 0.988.
- Measurement location: Vertex AI custom jobs on n1-standard-8 + 1x NVIDIA_TESLA_T4.
- Model weights source: GCS cache populated by the Vertex model-cache job; no local weight downloads or inference.

| Model | Prompts | Elapsed seconds | Decisions/hour | Valid JSON rate |
|---|---:|---:|---:|---:|
| HuggingFaceTB/SmolLM2-1.7B-Instruct | 512 | 388.27 | 4747 | 0.988 |
| Qwen/Qwen2.5-1.5B-Instruct | 512 | 725.36 | 2541 | 1.000 |
| Qwen/Qwen2.5-3B-Instruct | 512 | 836.68 | 2203 | 0.990 |
| microsoft/Phi-3.5-mini-instruct | 512 | 966.39 | 1907 | 1.000 |
