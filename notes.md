## [2026-07-02T22:00:13.2588800Z] P0/START
- Mission: execute the AgoraSim plan end-to-end from section 1, maintaining Vertex-only heavy compute and append-only notes.
- Working root assumption: `C:\Users\bubga.JULIAN-LAPTOPE2\OneDrive\Desktop\coding\currect QR\codex` is the intended AgoraSim project root for `JulianAttemptsCoding/QTA1`; the parent git repository points at `QTA0` and is treated as unrelated.
- Git state: initialized a new repository in this project root on branch `main`; remote set to `https://github.com/JulianAttemptsCoding/QTA1.git`; no repo commit exists yet.
- Required read-through completed for README, PLAN, FEASIBILITY, DECISION_MEMO, QC_AUDIT, SOURCES, vertex notes, docs, configs, prompts, scripts, src, and tests.
- Environment summary: `.env` exists and is gitignored. Variable names present: `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `FRED_API_KEY`. Variable names absent: `SEC_API_USER_AGENT`, `GCP_PROJECT`, `GCS_BUCKET`, `GOOGLE_CLOUD_PROJECT`, `HF_TOKEN`.
- HF token handling: token was supplied in the user prompt and will not be committed or written to tracked files; only `HF_TOKEN` may be passed to Vertex model-cache jobs if the run reaches that point.
- GCloud summary: Google Cloud SDK present; active account found via `gcloud auth list`.
- Current known risks: GCP project/bucket not yet resolved; SEC user-agent missing from `.env`; P0 scripts are currently stubs and must be implemented before G0 can pass.

## [2026-07-02T22:07:00Z] P0/A-001
- Commands run: `pip install -e ".[dev]"`, `pytest -q`, `make smoke`, and the Makefile-equivalent `python scripts\p2_smoke_sim.py --config configs\sim_smoke.yaml`.
- Local install completed with dev dependencies only; no `vllm`, `torch`, model runtime, model weights, or LLM inference ran locally.
- `pytest -q` result: 14 passed.
- `make smoke` could not run because `make` is not installed in this Windows shell; the equivalent smoke command passed with parse-valid 0.995 and `GATE G2 SMOKE: PASS`.
- GCP project resolved from gcloud config: `project-c779f701-1a49-4a58-b54`; region resolved from gcloud config: `us-central1`.
- Billing check: `gcloud beta billing projects describe ...` reported billing enabled.
- QA delta against QC_AUDIT master checklist: M-14 local reproducibility checks remain green; M-12/M-13 are still gated on G0 measurements; no heavy-compute rule violation observed.

## [2026-07-02T22:14:00Z] P0/A-002
- Implemented `scripts/p0_gate_data.py` with real checks for Alpaca bars/feed matrix, Alpaca news depth, Robintrack archive load, SEC EDGAR, and FRED.
- Added non-network tests for the P0 gate helper logic; `pytest -q` result after implementation: 17 passed.
- Ran `python scripts\p0_gate_data.py`; first attempt passed Alpaca, Robintrack, and FRED but failed EDGAR because the fallback User-Agent lacked an email-shaped contact and SEC returned HTML.
- Fixed EDGAR response handling and fallback User-Agent, then reran `python scripts\p0_gate_data.py --no-robintrack-download`; all checks PASS.
- Robintrack archive was downloaded/extracted under ignored `data/raw/robintrack/`; sample CSVs loaded for AAPL, TSLA, and GME. Raw vendor data remains untracked.
- `docs/G0_REPORT.md` written with PASS details. Data-side G0 criteria are satisfied; throughput-side G0 remains pending and must run on Vertex.
- QA loop: `pytest -q` passed, smoke command passed, no secrets were printed or committed, and QC_AUDIT M-13 is now resolved for the checked data endpoints.

## [2026-07-02T22:30:00Z] P0/VERTEX-INFRA
- Verified `gcloud ai custom-jobs create --help`; installed CLI exposes `--worker-pool-spec` for custom containers/accelerators but not a spot scheduling shorthand.
- Implemented REST-based Vertex launcher to set `jobSpec.scheduling.strategy=SPOT`; redacted request specs will be saved under `docs/vertex_job_specs/`.
- Resolved GCP resources: project `project-c779f701-1a49-4a58-b54`, region `us-central1`, bucket `gs://project-c779f701-1a49-4a58-b54-agorasim`, Artifact Registry repo `us-central1-docker.pkg.dev/project-c779f701-1a49-4a58-b54/agorasim`.
- Quota check: `us-central1` T4 quota is 1 regular T4 and 1 preemptible T4, so `N_workers = min(1, 6) = 1`.
- Cloud Build source submission initially failed because the default compute service account lacked source-bucket read permission; added bucket/project IAM bindings for source read, Artifact Registry write, and logging.
- Submitted Cloud Build `49a1e6e2-bc00-44d1-a150-d90db6549228` for `docker/Dockerfile.worker`; build is running/pushing the worker image. No Vertex jobs are active yet.

## [2026-07-02T22:36:00Z] P0/MODEL-CACHE-LAUNCH
- Cloud Build `49a1e6e2-bc00-44d1-a150-d90db6549228` completed successfully and pushed `us-central1-docker.pkg.dev/project-c779f701-1a49-4a58-b54/agorasim/worker:latest`.
- Launched Vertex model-cache job `projects/987318647780/locations/us-central1/customJobs/2567998475702632448` (`agorasim-p0-model-cache-20260702-2235`) with `jobSpec.scheduling.strategy=SPOT`.
- HF token was passed only as Vertex env var `HF_TOKEN`; redacted request spec written to `docs/vertex_job_specs/agorasim-p0-model-cache-20260702-2235.json`.
- Budget estimate added: n1-standard-8 + 1x T4 spot, assume <=2.0 h at $0.30/h, est $0.60 cumulative.

## [2026-07-02T22:47:07Z] P0/VERTEX-POLL
- Model-cache job `projects/987318647780/locations/us-central1/customJobs/2567998475702632448` moved from `JOB_STATE_PENDING` to `JOB_STATE_RUNNING`.
- Vertex logs before running showed framework provisioning/preparation only; no failure or license error yet.

## [2026-07-02T22:52:43Z] P0/MODEL-CACHE-RELAUNCH-1
- Model-cache job `projects/987318647780/locations/us-central1/customJobs/2567998475702632448` failed after caching the four ungated models.
- Root cause from Vertex logs: the supplied HF token is not authorized for `meta-llama/Llama-3.2-3B-Instruct`; per P-05, the gated pair is excluded and execution proceeds with the ungated four model families.
- Cached before failure: `Qwen/Qwen2.5-1.5B-Instruct`, `Qwen/Qwen2.5-3B-Instruct`, `microsoft/Phi-3.5-mini-instruct`, `HuggingFaceTB/SmolLM2-1.7B-Instruct`.
- Updated budget estimate for failed run: ~0.10 h at $0.30/h = $0.03 cumulative. Relaunch count for model-cache: 1 of 5.

## [2026-07-02T22:55:00Z] P0/MODEL-CACHE-LAUNCH
- Launched ungated-only model-cache job `projects/987318647780/locations/us-central1/customJobs/2166474421424881664` (`agorasim-p0-model-cache-20260702-2255`) with no HF token env var.
- Redacted request spec written to `docs/vertex_job_specs/agorasim-p0-model-cache-20260702-2255.json`.
- Budget estimate added: assume <=2.0 h at $0.30/h, est $0.60; cumulative estimate $0.63.

## [2026-07-02T22:58:35Z] P0/VERTEX-POLL
- Ungated model-cache job `projects/987318647780/locations/us-central1/customJobs/2166474421424881664` moved to `JOB_STATE_RUNNING`.

## [2026-07-02T23:04:38Z] P0/MODEL-CACHE-PASS
- Ungated model-cache job `projects/987318647780/locations/us-central1/customJobs/2166474421424881664` reached `JOB_STATE_SUCCEEDED`.
- Synced `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/models/MODEL_SHAS.md` to `docs/MODEL_SHAS.md`.
- Cached model SHAs recorded for the four ungated models: Qwen 1.5B, Qwen 3B, Phi 3.5 mini, and SmolLM2 1.7B.
- Updated `configs/models.yaml` to mark the gated Llama/Gemma pair disabled for this run because the supplied token lacked Llama access; P-05 permits proceeding with the ungated four.
- Budget actualized for successful cache job: ~0.10 h at $0.30/h = $0.03; cumulative estimate $0.06. No Vertex jobs remain active.

## [2026-07-02T23:08:00Z] P0/A-003-THROUGHPUT-LAUNCH
- Launched throughput job `projects/987318647780/locations/us-central1/customJobs/1342878639569502208` for `Qwen/Qwen2.5-1.5B-Instruct`.
- Job reads cached weights from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/models`; output JSON target is `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/gates/g0/throughput/Qwen--Qwen2.5-1.5B-Instruct.json`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.14.

## [2026-07-02T23:13:38Z] P0/A-003-THROUGHPUT-FIX
- Throughput job `projects/987318647780/locations/us-central1/customJobs/1342878639569502208` failed before inference due to prompt template path resolution inside the installed worker package.
- Root cause: `prompt_builder` resolved `prompts/` relative to `site-packages`; fixed it to prefer `AGORASIM_PROMPT_DIR`, then current working directory `/app/prompts`, then package-relative fallback.
- Restructured `docker/Dockerfile.worker` so the expensive vLLM dependency layer is installed before copying repo source; future source-only rebuilds should be faster.
- Updated budget actual for the failed throughput attempt: ~0.03 h at $0.30/h = $0.01; cumulative estimate $0.07. No Vertex jobs remain active.

## [2026-07-02T23:26:00Z] P0/A-003-THROUGHPUT-RELAUNCH
- Cloud Build `38c09767-a769-422e-ad64-0bc3e007fb76` succeeded and pushed fixed `worker:latest` digest `sha256:d065300635dc48a64d62c3db922a9e911c9366f2f1aa72197758912345b5d225`.
- Relaunched throughput job `projects/987318647780/locations/us-central1/customJobs/7625118644774633472` for `Qwen/Qwen2.5-1.5B-Instruct`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.15.

## [2026-07-02T23:33:54Z] P0/VERTEX-POLL
- Throughput job `projects/987318647780/locations/us-central1/customJobs/7625118644774633472` moved to `JOB_STATE_RUNNING`.
- Logs show the worker process has started; no inference result JSON yet.

## [2026-07-02T23:34:24Z] P0/A-003-THROUGHPUT-FIX
- Throughput job `projects/987318647780/locations/us-central1/customJobs/7625118644774633472` failed before inference with vLLM `Device string must not be empty`.
- Verified the Vertex job spec did include `acceleratorType=NVIDIA_TESLA_T4` and `acceleratorCount=1`; failure is in container CUDA/vLLM device detection, not launcher GPU omission.
- Patched worker environment with NVIDIA visibility/driver capability variables and NVIDIA library path; patched throughput script to pass `device="cuda"` to vLLM explicitly.
- Updated budget actual for this failed throughput attempt: ~0.01 h at $0.30/h, rounded to $0.01; cumulative estimate $0.08.

## [2026-07-02T23:51:00Z] P0/A-003-THROUGHPUT-RELAUNCH
- Cloud Build `f31c6011-8ece-47af-abdc-9da194f83b26` succeeded after the CUDA/device patch.
- Relaunched throughput job `projects/987318647780/locations/us-central1/customJobs/7648199592864907264` for `Qwen/Qwen2.5-1.5B-Instruct`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.16.

## [2026-07-02T23:58:38Z] P0/VERTEX-POLL
- Throughput job `projects/987318647780/locations/us-central1/customJobs/7648199592864907264` moved to `JOB_STATE_RUNNING`.

## [2026-07-02T23:59:39Z] P0/A-003-THROUGHPUT-FIX
- Throughput job `projects/987318647780/locations/us-central1/customJobs/7648199592864907264` failed before inference because vLLM 0.24 does not accept `device=` as an `LLM(...)` kwarg.
- Patched throughput script to remove the unsupported kwarg and set `VLLM_TARGET_DEVICE=cuda` before importing vLLM.
- Updated budget actual for this failed throughput attempt: ~0.02 h at $0.30/h, rounded to $0.01; cumulative estimate $0.09.

## [2026-07-03T00:20:00Z] P0/A-003-THROUGHPUT-RELAUNCH
- Cloud Build `255bfc7a-c017-4ad7-b2b0-22fa27ef55c2` succeeded after the `VLLM_TARGET_DEVICE=cuda` patch.
- Relaunched throughput job `projects/987318647780/locations/us-central1/customJobs/8922260890573602816` for `Qwen/Qwen2.5-1.5B-Instruct`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.17.

## [2026-07-03T00:28:36Z] P0/A-003-THROUGHPUT-FIX
- Throughput job `projects/987318647780/locations/us-central1/customJobs/8922260890573602816` failed before inference with Transformers rejecting the local model path as a Hugging Face repo id.
- Root cause: `download_prefix` stripped the GCS prefix trailing slash, producing relative names that began with `/` and escaped the intended local model directory.
- Patched GCS download path normalization and added regression coverage for model-root and nested cache blobs.
- Updated budget actual for this failed throughput attempt: ~0.01 h at $0.30/h, rounded to $0.01; cumulative estimate $0.10. Relaunch count for Qwen throughput: 4 attempts used.

## [2026-07-03T00:50:00Z] P0/A-003-THROUGHPUT-RELAUNCH
- Cloud Build `0aed9840-5dcc-49e9-922d-c1770b61ac6c` succeeded after the GCS path-normalization patch and pushed worker digest `sha256:1cae6704b287bb1967c268d8832d97625a4e1c6fa0d0d7c8a4def2a6248aca66`.
- Relaunched throughput job `projects/987318647780/locations/us-central1/customJobs/3167786466700951552` for `Qwen/Qwen2.5-1.5B-Instruct`.
- Job reads cached weights from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/models`; no model weights are downloaded or run locally.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.18. Relaunch count for Qwen throughput: 5 attempts used.

## [2026-07-03T01:02:31Z] P0/A-003-THROUGHPUT-FIX
- Throughput job `projects/987318647780/locations/us-central1/customJobs/3167786466700951552` failed during vLLM engine startup after the GCS model path fix.
- Root cause from Vertex logs: the floating `vllm>=0.6` dependency resolved to vLLM `0.24.0` / Torch `2.11.0`, whose CUDA 13 runtime requires a newer NVIDIA driver than Vertex's T4 host driver (`12020`) provides.
- Patched the worker image to pin vLLM `0.6.4.post1`, Transformers `4.46.3`, NumPy `1.26.4`, and Torch/Torchvision `2.5.1+cu121` from the official PyTorch CUDA 12.1 wheel index.
- Updated budget actual for this failed throughput attempt: ~0.02 h at $0.30/h, rounded to $0.01; cumulative estimate $0.11. No Vertex jobs remain active.

## [2026-07-03T01:18:00Z] P0/A-003-THROUGHPUT-RELAUNCH
- Cloud Build `1614f2e4-fb56-40a1-aed5-fdfd8bd4dfbb` succeeded after the CUDA-12 runtime pin and pushed worker digest `sha256:a634199fe0934742942486f1c155180e8218e3549bae8a5920d40654276fa865`.
- Relaunched throughput job `projects/987318647780/locations/us-central1/customJobs/7244247816913027072` for `Qwen/Qwen2.5-1.5B-Instruct`.
- This is the fifth Qwen throughput relaunch after the original attempt; if it fails for a non-transient engine issue, the P0 fail-safe should stop further Qwen relaunches.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.19.

## [2026-07-03T01:28:28Z] P0/A-003-THROUGHPUT-QA
- Throughput job `projects/987318647780/locations/us-central1/customJobs/7244247816913027072` succeeded on Vertex with the CUDA-12 runtime.
- Qwen 1.5B measured `7,799` decisions/hour over 512 prompts, but valid-JSON rate was only `0.688`, below the G0 threshold of `0.900`.
- Patched the throughput worker to use vLLM guided JSON decoding with an explicit decision schema and temperature `0.0`; updated the prompt so `limit_price` is always a positive number, which matches the guided schema and is ignored by the clearing engine for market orders.
- Updated budget actual for this successful throughput measurement: ~0.08 h at $0.30/h = $0.02; cumulative estimate $0.13. No Vertex jobs remain active.

## [2026-07-03T01:42:00Z] P0/A-003-THROUGHPUT-GUIDED-RERUN
- Cloud Build `94be17fd-c46f-49fd-be2c-1eb330824fb2` succeeded after enabling guided JSON decoding and pushed worker digest `sha256:84fdc46dbe2fce47d8d779fb15f5747f13c8d6151621632f6bf839e40887ed10`.
- Launched guided-decoding throughput job `projects/987318647780/locations/us-central1/customJobs/6616558618848264192` for `Qwen/Qwen2.5-1.5B-Instruct`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.21.

## [2026-07-03T01:49:13Z] P0/A-003-THROUGHPUT-GUIDED-FIX
- Guided-decoding job `projects/987318647780/locations/us-central1/customJobs/6616558618848264192` loaded the model on Vertex but failed before output because vLLM's default `outlines` backend imported `pyairports`, which was unavailable at runtime.
- Inspected the installed vLLM `0.6.4.post1` wheel and confirmed the alternate `lm-format-enforcer` guided-decoding backend is supported for JSON schemas.
- Patched the throughput worker to request `GuidedDecodingParams(..., backend="lm-format-enforcer")`.
- Updated budget actual for this failed guided attempt: ~0.03 h at $0.30/h, rounded to $0.01; cumulative estimate $0.14. No Vertex jobs remain active.

## [2026-07-03T02:04:00Z] P0/A-003-THROUGHPUT-LMFE-RERUN
- Cloud Build `b0fe2991-5200-4482-adf9-afd6ae586074` succeeded after switching guided decoding to `lm-format-enforcer` and pushed worker digest `sha256:b90cd602bdc335853e395f2dfa7f450846b2e959178a99d8f2097005564497f0`.
- Launched guided-decoding throughput job `projects/987318647780/locations/us-central1/customJobs/7429176876611928064` for `Qwen/Qwen2.5-1.5B-Instruct`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.22.

## [2026-07-03T02:21:36Z] P0/A-003-THROUGHPUT-QWEN15-PASS
- Guided-decoding throughput job `projects/987318647780/locations/us-central1/customJobs/7429176876611928064` succeeded on Vertex.
- Result JSON: `2,541` decisions/hour, valid-JSON rate `1.000`, 512 prompts, weights loaded from the GCS model cache.
- Updated budget actual for this successful throughput measurement: ~0.21 h at $0.30/h = $0.06; cumulative estimate $0.20. No Vertex jobs remain active.

## [2026-07-03T02:22:00Z] P0/A-003-THROUGHPUT-QWEN3-LAUNCH
- Launched guided-decoding throughput job `projects/987318647780/locations/us-central1/customJobs/2646917022297882624` for `Qwen/Qwen2.5-3B-Instruct`.
- Job reads cached weights from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/models` and writes `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/gates/g0/throughput/Qwen--Qwen2.5-3B-Instruct.json`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.28.

## [2026-07-03T02:38:18Z] P0/A-003-THROUGHPUT-QWEN3-PASS
- Guided-decoding throughput job `projects/987318647780/locations/us-central1/customJobs/2646917022297882624` succeeded on Vertex.
- Result JSON: `2,203` decisions/hour, valid-JSON rate `0.990`, 512 prompts, weights loaded from the GCS model cache.
- Updated budget actual for this successful throughput measurement: ~0.25 h at $0.30/h = $0.08; cumulative estimate $0.28. No Vertex jobs remain active.

## [2026-07-03T02:39:00Z] P0/A-003-THROUGHPUT-PHI35-LAUNCH
- Launched guided-decoding throughput job `projects/987318647780/locations/us-central1/customJobs/4141197304910577664` for `microsoft/Phi-3.5-mini-instruct`.
- Job reads cached weights from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/models` and writes `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/gates/g0/throughput/microsoft--Phi-3.5-mini-instruct.json`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.36.

## [2026-07-03T02:44:52Z] P0/A-003-THROUGHPUT-PHI35-FIX
- Phi 3.5 throughput job `projects/987318647780/locations/us-central1/customJobs/4141197304910577664` failed after loading weights on Vertex with a CUDA out-of-memory error during vLLM cudagraph capture.
- Added throughput-worker flags for `--enforce-eager` and `--gpu-memory-utilization` so larger models can disable cudagraph capture and reduce memory pressure without changing the smaller-model measurements.
- Planned Phi relaunch: `--enforce-eager --gpu-memory-utilization 0.85`.
- Updated budget actual for this failed Phi attempt: ~0.05 h at $0.30/h = $0.02; cumulative estimate $0.30. No Vertex jobs remain active.

## [2026-07-03T02:58:00Z] P0/A-003-THROUGHPUT-PHI35-RELAUNCH
- Cloud Build `5e635811-ff26-4acf-ab9a-a8115a3a08f1` succeeded after adding memory-control flags and pushed worker digest `sha256:8b0e35e211690c0529763477795bdffab7590c003ad767020164faf6ca63cd81`.
- Relaunched guided-decoding throughput job `projects/987318647780/locations/us-central1/customJobs/6271962878610243584` for `microsoft/Phi-3.5-mini-instruct` with `--enforce-eager --gpu-memory-utilization 0.85`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.38.

## [2026-07-03T03:20:44Z] P0/A-003-THROUGHPUT-PHI35-PASS
- Phi 3.5 eager throughput job `projects/987318647780/locations/us-central1/customJobs/6271962878610243584` succeeded on Vertex.
- Result JSON: `1,907` decisions/hour, valid-JSON rate `1.000`, 512 prompts, `--enforce-eager --gpu-memory-utilization 0.85`.
- Updated budget actual for this successful throughput measurement: ~0.29 h at $0.30/h = $0.09; cumulative estimate $0.39. No Vertex jobs remain active.

## [2026-07-03T03:22:00Z] P0/A-003-THROUGHPUT-SMOLLM2-LAUNCH
- Launched guided-decoding throughput job `projects/987318647780/locations/us-central1/customJobs/8943441882571079680` for `HuggingFaceTB/SmolLM2-1.7B-Instruct`.
- Job reads cached weights from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/models` and writes `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/gates/g0/throughput/HuggingFaceTB--SmolLM2-1.7B-Instruct.json`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.47.

## [2026-07-03T03:33:18Z] P0/A-003-THROUGHPUT-SMOLLM2-QA
- SmolLM2 throughput job `projects/987318647780/locations/us-central1/customJobs/8943441882571079680` succeeded on Vertex.
- Result JSON: `4,445` decisions/hour, but valid-JSON rate `0.820`; invalid examples were structurally valid JSON with `horizon_days: 0`, which the parser rejects.
- Patched the guided JSON schema to express `horizon_days` as an explicit enum from `1` through `30`, because LMFE enforced structure but not the numeric min/max range.
- Updated budget actual for this successful-but-below-threshold SmolLM2 measurement: ~0.14 h at $0.30/h = $0.04; cumulative estimate $0.43. No Vertex jobs remain active.

## [2026-07-03T03:44:00Z] P0/A-003-THROUGHPUT-SMOLLM2-ENUM-RERUN
- Switched local repository work from `main` to new branch `codex`; future commits/pushes will target `codex` only.
- Cloud Build `d203a28e-b1e6-4805-9a94-d54f382eef89` succeeded after changing `horizon_days` to an explicit enum and pushed worker digest `sha256:9c76ac85c647f62803da5855317f688505798fc4a849d8600768bb7b2e16add9`.
- Relaunched guided-decoding throughput job `projects/987318647780/locations/us-central1/customJobs/6129255065417940992` for `HuggingFaceTB/SmolLM2-1.7B-Instruct`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.51.

## [2026-07-03T03:49:42Z] P0/A-003-THROUGHPUT-SMOLLM2-PREFIX-FIX
- SmolLM2 enum rerun `projects/987318647780/locations/us-central1/customJobs/6129255065417940992` failed before inference because the worker derived a `--` GCS model prefix, while the actual Vertex model-cache manifest uses `__` prefixes.
- Verified `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/models/_cache_manifest.json` and patched the throughput worker to resolve model cache URIs from the manifest instead of guessing.
- Updated `scripts/model_cache.py` and `docs/MODEL_SHAS.md` to match the manifest convention.
- Updated budget actual for this failed SmolLM2 attempt: ~0.01 h at $0.30/h, rounded to $0.01; cumulative estimate $0.44. No Vertex jobs remain active.

## [2026-07-03T04:16:00Z] P0/A-003-THROUGHPUT-SMOLLM2-MANIFEST-RERUN
- Cloud Build `57039a0f-0027-4b3b-aa94-773b955dcea8` succeeded after the manifest-aware cache lookup and pushed worker digest `sha256:0b8c125d70bdf9e4de8e7b10a4c5740d98097c05f035895774486309a15f8772`.
- Relaunched guided-decoding throughput job `projects/987318647780/locations/us-central1/customJobs/6892474464768884736` for `HuggingFaceTB/SmolLM2-1.7B-Instruct`.
- Job reads cached weights from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/models` via `_cache_manifest.json` and writes `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/gates/g0/throughput/HuggingFaceTB--SmolLM2-1.7B-Instruct.json`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.52.

## [2026-07-03T04:31:00Z] P0/A-003-THROUGHPUT-PASS
- SmolLM2 manifest rerun `projects/987318647780/locations/us-central1/customJobs/6892474464768884736` reached `JOB_STATE_SUCCEEDED`.
- Result JSON: `4,747` decisions/hour, valid-JSON rate `0.988`, 512 prompts, weights loaded from the GCS manifest path `models/HuggingFaceTB__SmolLM2-1.7B-Instruct`.
- Synced the four G0 throughput result JSONs from GCS into ignored `runs/g0-throughput/` and generated `docs/G0_THROUGHPUT.md`.
- G0 throughput side is PASS: best measured throughput `4,747` decisions/hour is above the `2,000` threshold, and the lowest accepted valid-JSON rate is `0.988`, above the `0.900` threshold.
- Updated budget actual for this final SmolLM2 measurement: ~0.21 h at $0.30/h = $0.06; cumulative estimate $0.50. No Vertex jobs remain active.

## [2026-07-03T04:36:00Z] P0/A-004-G0-PASS
- Wrote `docs/FEASIBILITY_ADDENDUM.md` and updated `FEASIBILITY.md` with measured G0 data, throughput, and the revised compute/cost table.
- Updated `README.md` and `PLAN.md` status so the repository no longer advertises G0 as not run.
- GATE G0 final decision: PASS. Data checks passed; selected budget model SmolLM2 measured `4,747` decisions/hour and accepted valid JSON rate floor is `0.988`; P1 may begin.

## [2026-07-03T05:17:00Z] P1/G1-PASS
- Implemented `scripts/p1_freeze_universes.py` and tests for deterministic universe/snapshot helper logic.
- Froze CALIB-2019 universe: `IIPR`, `IGC`, `GOLD`, `RIOT`, `CRBP`, `BLNK`, `PLUG`, `XXII`, `LEVI`, `VKTX` using selection date `2019-06-28`.
- Froze OOS-2025 universe: `NVNI`, `TLRY`, `EDIT`, `CHPT`, `BLNK`, `FRSX`, `TPET`, `OGI`, `CCO`, `ICCM` using selection date `2024-12-20` and OOS start `2025-01-02`, after the max enabled-model cutoff proxy from G0.
- Wrote `docs/G1_UNIVERSES.md`, `docs/G1_SNAPSHOT_MANIFEST.json`, and `docs/G1_LEAKAGE_SPOTCHECK.md`; spot check rendered 10 filtered prompts from frozen snapshots with zero post-asof included rows.
- Corrected the P1 freezer to use raw Alpaca prices for universe market-cap filters after a QA pass caught split-adjusted historical prices.
- Synced ignored raw snapshots to `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/snapshots/g1/` and uploaded the tracked manifest as `manifest.json`.
- P1 used local CPU/network only; no local LLM weights, local inference, or Vertex heavy-compute jobs were launched. GATE G1 final decision: PASS; P2 may begin.

## [2026-07-03T05:43:00Z] P2/A-201-A-203-QWEN15-LAUNCH
- Implemented `scripts/p2_gate_real_model.py`, `scripts/p2_collect_gate.py`, and collector tests; Cloud Build `07221b55-260a-48e2-9cf9-8ad9adbcf994` pushed worker digest `sha256:71e1a1bbbb72fa00fec2001ee22105c40fc7b145b0a03cf35a31fb028f3e5f88`.
- Queued P2 real-model gate job `projects/987318647780/locations/us-central1/customJobs/4485025586032410624` for `Qwen/Qwen2.5-1.5B-Instruct`.
- Job reads G1 snapshots from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/snapshots/g1/manifest.json`, cached model weights from GCS, and writes `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/gates/g2/Qwen--Qwen2.5-1.5B-Instruct.json`.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.58.

## [2026-07-03T06:18:00Z] P2/A-201-A-203-QWEN15-SCORER-FIX
- First Qwen P2 job `projects/987318647780/locations/us-central1/customJobs/4485025586032410624` succeeded with valid JSON `1.000`, but QA found the contamination scorer counted `UNKNOWN.` as non-UNKNOWN.
- Patched `scripts/p2_gate_real_model.py` to normalize punctuation around UNKNOWN answers, rebuilt worker image with Cloud Build `02e0b581-a0ce-47eb-96ae-b97aa07c239e`, digest `sha256:30432e187ff1cb76a626fde5eab25b7d1edff9f51296c30d4f59d9dd5c40fdc1`.
- Queued corrected Qwen P2 rerun `projects/987318647780/locations/us-central1/customJobs/8714609323575083008`; budget estimate adds another <=0.25 h at $0.30/h = $0.08, cumulative estimate $0.63 after actualizing the first Qwen run at about $0.05.

## [2026-07-03T06:31:00Z] P2/A-201-A-203-PHI35-LAUNCH
- Corrected Qwen P2 rerun `projects/987318647780/locations/us-central1/customJobs/8714609323575083008` succeeded: valid JSON `1.000`, contamination max non-UNKNOWN `0.000`; Qwen family survives G2.
- Queued Phi P2 real-model gate job `projects/987318647780/locations/us-central1/customJobs/1480702422111223808` with `--enforce-eager --gpu-memory-utilization 0.85`, matching the G0 Phi memory workaround.
- Budget estimate added: assume <=0.25 h at $0.30/h = $0.08; cumulative estimate $0.68 after actualizing the two Qwen P2 jobs at about $0.10 total.

## [2026-07-03T06:59:00Z] P2/A-201-A-203-PHI35-SCORER-FIX
- Phi P2 job `projects/987318647780/locations/us-central1/customJobs/1480702422111223808` succeeded with valid JSON `1.000`, but QA found the contamination scorer counted `Answer: UNKNOWN ...` as non-UNKNOWN.
- Patched `scripts/p2_gate_real_model.py` to strip an `ANSWER:` prefix before applying the UNKNOWN detector, rebuilt worker image with Cloud Build `815ba04d-3fe8-4fd6-8b09-9861af9d4168`, digest `sha256:3af89b314af44064655b3cec7460b5eb8ff956f207c5b740fc0351ca383318fa`.
- Queued corrected Phi P2 rerun `projects/987318647780/locations/us-central1/customJobs/5330717153559576576`; budget estimate adds another <=0.25 h at $0.30/h = $0.08, cumulative estimate $0.73 after actualizing the first Phi P2 job at about $0.05.

## [2026-07-03T07:09:00Z] P2/G2-PASS
- Corrected Phi rerun `projects/987318647780/locations/us-central1/customJobs/5330717153559576576` succeeded on Vertex and overwrote the Phi G2 result at `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/gates/g2/microsoft--Phi-3.5-mini-instruct.json`.
- Final G2 survivors: `Qwen/Qwen2.5-1.5B-Instruct` and `microsoft/Phi-3.5-mini-instruct`; both reached valid JSON `1.000` and contamination max non-UNKNOWN `0.000`.
- Generated `docs/G2_REPORT.md`; GATE G2 final decision: PASS. Both smoke paths had mean absolute flow imbalance `1.000`, so P3/P5 should treat F-06 herding/entropy diagnostics as high priority.
- Actualized P2 Vertex budget: four short spot T4 jobs totaling about `$0.20`, cumulative project estimate `$0.70`. No Codex-owned Vertex jobs remain active.

## [2026-07-03T07:21:00Z] QA/PLAN-GATE-TEXT-CORRECTION
- Re-read the execution brief and caught that PLAN.md gate criteria must remain unchanged.
- Restored the original G2 kill criterion text in PLAN.md; G2 PASS evidence remains in `docs/G2_REPORT.md`, README status, STATE.json, and this append-only log.

## [2026-07-03T07:23:00Z] QA/GATE-TAGS
- Pushed annotated tags `G0-PASS`, `G1-PASS`, and `G2-PASS` to `origin`.
- `G2-PASS` points at the corrected `codex` tip so the tagged branch state preserves the original PLAN.md gate criterion text.

## [2026-07-03T07:38:00Z] P3/A-301-IMPLEMENTATION-START
- Started P3 calibration implementation after G2 PASS; no Codex-owned Vertex jobs were active.
- Aligned `configs/sim_calib_2019.yaml` to the pinned P3 workload shape: 100 agents per ticker/arm, matching the execution brief and PLAN A-301 estimate.
- Added a Vertex-only calibration worker plus local launcher and collector scripts. Local QA before build: `pytest -q` 40/40 passing, compileall passing, stub smoke PASS, secret scan clean.
- Alias scrubbing is best-effort for ticker tokens, the synthetic `<TICKER> Holdings` name used in prompts, and exchange mentions; EDGAR legal-name scrubbing is logged as a known limitation because G1 snapshots do not carry company legal-name metadata.

## [2026-07-03T07:52:00Z] P3/A-301-WORKER-BUILD-QA
- Verified `gcloud builds submit --help`; the installed CLI does not support `--file`, so the working command is `gcloud builds submit --project project-c779f701-1a49-4a58-b54 --region us-central1 --config cloudbuild.worker.yaml .`.
- Cloud Build `befb1739-8e0d-4f20-87dd-25cdd3940518` succeeded and pushed worker digest `sha256:b238b0dbde4b773ff42785e7c7543932bc9145f4be39e5b5a11beddf45f156d2`.
- Dry-run launch caught local environment drift: `agorasim` initially resolved from the sibling `claude` checkout. Added repo-local import guards to the new scripts and reinstalled `pip install -e ".[dev]"` from the `codex` folder.
- Post-fix QA: `pytest -q` 40/40 passing, compileall passing, `python -c "import agorasim"` resolves to the local `codex/src/agorasim`, and secret scan is clean.

## [2026-07-03T07:59:00Z] P3/A-301-FINAL-WORKER-BUILD
- Rebuilt the worker after the import-guard patch so the Artifact Registry image matches the local P3 scripts.
- Cloud Build `7ca656e6-b345-4eb9-b847-88f817aa2782` succeeded and pushed worker digest `sha256:bf698ed30e55b843654b987000423b2d0c99326e9db5951d829bd7b1e3715450`.
- No Codex-owned Vertex GPU job was launched during the build; a separate sibling validation job remained active and was not touched.

## [2026-07-03T08:02:00Z] P3/A-301-LAUNCHER-WINDOWS-FIX
- First P3 launch attempt failed locally before submission because `subprocess.run(["gcloud", ...])` cannot resolve the executable on this Windows shell; no Vertex job was created and no GPU budget was spent.
- Patched `scripts/run_sim_phase.py` to resolve `gcloud` or `gcloud.cmd` via `shutil.which`, matching the existing Vertex launcher helper.

## [2026-07-03T08:07:00Z] P3/A-301-IIPR-NAMED-LAUNCH
- Launched first P3 calibration shard after queue was clear: `projects/987318647780/locations/us-central1/customJobs/8715101904784326656` (`agorasim-p3-iipr-named-v1`), spot T4.
- Run id `calib-2019-g1-iipr-named-v1`; manifest uploaded before launch to `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-iipr-named-v1/manifest.json`.
- Worker will load only GCS-cached model weights (`Qwen/Qwen2.5-1.5B-Instruct`, `microsoft/Phi-3.5-mini-instruct`) and write requests, raw outputs, and `sim.jsonl` to the same GCS run directory. Local machine remains orchestration-only.
- Conservative budget reservation: <=6 h at `$0.30/h` = `$1.80`; cumulative estimate `$2.50`, below the `$85` hard stop.

## [2026-07-03T08:14:00Z] P3/A-301-IIPR-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8715101904784326656` is `JOB_STATE_RUNNING`.
- GCS run directory currently contains the pre-launch `manifest.json` and Vertex-rendered `requests.jsonl` (~40 MiB); `outputs.jsonl` is not present yet, consistent with model download/load/inference startup.

## [2026-07-03T08:22:00Z] P3/A-301-IIPR-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8715101904784326656` remains `JOB_STATE_RUNNING`.
- First chunk uploaded `outputs.jsonl`: 512 rows, 509 parsed (`99.4%`), model `Qwen/Qwen2.5-1.5B-Instruct`. The request ledger is working and syncing to GCS after chunks.

## [2026-07-03T08:32:00Z] P3/A-301-IIPR-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8715101904784326656` remains `JOB_STATE_RUNNING`.
- GCS `outputs.jsonl` is still at 512 rows / 509 parsed. Continuing to monitor chunk cadence before taking action.

## [2026-07-03T08:43:00Z] P3/A-301-IIPR-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8715101904784326656` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,024 rows / 1,021 parsed (`99.7%` cumulative), all Qwen so far. The chunk ledger is healthy, so the job continues.

## [2026-07-03T08:53:00Z] P3/A-301-IIPR-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8715101904784326656` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,536 rows / 1,532 parsed (`99.7%` cumulative), still within the Qwen portion of the shard.

## [2026-07-03T09:03:00Z] P3/A-301-IIPR-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8715101904784326656` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` remains at 1,536 rows / 1,532 parsed, but Vertex logs show the current 512-prompt Qwen chunk is actively progressing, so no relaunch action taken.

## [2026-07-03T09:21:00Z] P3/A-301-IIPR-NAMED-FAILED-RESUME
- Job `projects/987318647780/locations/us-central1/customJobs/8715101904784326656` ended `JOB_STATE_FAILED` at `2026-07-03T09:14:19Z` with Vertex error code 8: replicas low on memory.
- Preserved partial ledger in GCS: `requests.jsonl` has 12,800 requests; `outputs.jsonl` has 2,048 rows / 2,041 parsed (`99.7%` cumulative), all in the Qwen portion. The worker resume path skips answered request ids, so no local heavy compute or local model inference is needed.
- Recorded the failed attempt in `BUDGET.md` at `$0.36` estimated cost, cumulative `$1.06`, still below the `$85` hard stop. Reduced P3 chunk defaults from 512 to 128 before relaunch.

## [2026-07-03T09:24:00Z] P3/A-301-IIPR-NAMED-RELAUNCH
- Backed up the original GCS manifest to `manifest_before_rerun1.json`, then relaunched the same run id `calib-2019-g1-iipr-named-v1` so completed request ids can be skipped.
- New Vertex job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` (`agorasim-p3-iipr-named-v1-rerun1`) is `JOB_STATE_PENDING` with explicit `--chunk-size 128`, `--gpu-memory-utilization 0.85`, and `--enforce-eager`.
- A separate project job is currently occupying the T4 slot; this rerun is queued/pending without cancelling other work. Conservative cumulative budget estimate is `$2.86`, below the `$85` hard stop.

## [2026-07-03T09:34:00Z] P3/A-301-IIPR-NAMED-POLL
- Sibling project job `agorasim-g0-thru-v10-validate` completed successfully; rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` is now `JOB_STATE_RUNNING` with start time `2026-07-03T09:31:41Z`.
- The rerun refreshed `requests.jsonl` in the same GCS run directory. `outputs.jsonl` remains at the preserved 2,048 rows / 2,041 parsed while the worker loads models and resumes.

## [2026-07-03T09:44:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- The smaller chunk path is confirmed: `outputs.jsonl` advanced from the preserved 2,048 rows to 2,304 rows / 2,296 parsed. All computation and model inference remain on Vertex.

## [2026-07-03T09:54:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,560 rows / 2,552 parsed. The run is proceeding in 128-row chunks with no local model inference.

## [2026-07-03T10:04:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,944 rows / 2,936 parsed. Recent Vertex logs show 128-prompt chunks completing successfully at the reduced chunk size.

## [2026-07-03T10:14:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,200 rows / 3,192 parsed. Brief GCS copy misses occurred during worker sync windows, but object listing and retry confirmed the ledger is intact.

## [2026-07-03T10:24:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,456 rows / 3,446 parsed. The resumed shard remains on Vertex and continues saving every completed 128-row chunk to GCS.

## [2026-07-03T10:34:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,712 rows / 3,701 parsed. Resume-safe chunking continues to preserve completed work in GCS.

## [2026-07-03T10:44:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,968 rows / 3,957 parsed. The run remains stable under the reduced 128-row chunk size.

## [2026-07-03T10:54:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,224 rows / 4,210 parsed. The shard has completed 2,176 new rows since relaunch, with all heavy work on Vertex.

## [2026-07-03T11:04:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,480 rows / 4,462 parsed. The P3 ledger continues to advance in GCS; no local LLM weights or local inference were used.

## [2026-07-03T11:14:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,736 rows / 4,717 parsed. Current parsed rate remains above 99%, and all work is still executing on Vertex.

## [2026-07-03T11:24:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,992 rows / 4,972 parsed. The shard is approaching the end of the Qwen half and remains under the budget guardrail.

## [2026-07-03T11:34:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,248 rows / 5,228 parsed. The worker continues to checkpoint every completed 128-row batch to GCS.

## [2026-07-03T11:44:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,504 rows / 5,483 parsed. The Qwen portion is nearing completion before the worker switches to the second surviving model.

## [2026-07-03T11:54:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,760 rows / 5,739 parsed. The remaining Qwen requests are expected to finish before the worker loads `microsoft/Phi-3.5-mini-instruct`.

## [2026-07-03T12:04:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,016 rows / 5,995 parsed. The Qwen tranche is within three chunks of completion before the Phi model load.

## [2026-07-03T12:14:00Z] P3/A-301-IIPR-NAMED-MODEL-SWITCH
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,400 rows / 6,378 parsed, completing the Qwen request tranche. Vertex logs confirm `microsoft/Phi-3.5-mini-instruct` loaded from `/tmp/agorasim-models/microsoft__Phi-3.5-mini-instruct` with memory profiling completed on the T4 worker.

## [2026-07-03T12:24:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- Phi outputs are being checkpointed: `outputs.jsonl` advanced to 6,784 rows / 6,756 parsed after the model switch. The second surviving model is running on Vertex from GCS-cached weights.

## [2026-07-03T12:34:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,168 rows / 7,138 parsed. Phi chunking is stable after the model transition.
