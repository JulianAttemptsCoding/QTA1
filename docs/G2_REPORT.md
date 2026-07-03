# G2 Real-Model Gate Report

- Overall: **PASS**
- Gate detail: 2 models across 2 families survived G2.
- Measurement location: Vertex AI custom jobs on n1-standard-8 + 1x NVIDIA_TESLA_T4.
- Model weights source: GCS cache populated by Vertex model-cache jobs; no local weight downloads or inference.
- Snapshot source: `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/snapshots/g1/manifest.json`.

| Model | Family | Smoke prompts | Valid JSON | Max probe non-UNKNOWN | Survives |
|---|---|---:|---:|---:|---|
| Qwen/Qwen2.5-1.5B-Instruct | qwen2_5 | 200 | 1.000 | 0.000 | True |
| microsoft/Phi-3.5-mini-instruct | phi3_5 | 200 | 1.000 | 0.000 | True |

## Smoke Path Summary

| Model | Days | First price | Last price | Mean abs imbalance |
|---|---:|---:|---:|---:|
| Qwen/Qwen2.5-1.5B-Instruct | 10 | 125.02 | 125.02 | 1.000 |
| microsoft/Phi-3.5-mini-instruct | 10 | 125.02 | 125.02 | 1.000 |
