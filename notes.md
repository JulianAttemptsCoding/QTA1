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

## [2026-07-03T12:44:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,552 rows / 7,521 parsed. The Phi tranche is proceeding at the same checkpoint cadence as Qwen.

## [2026-07-03T12:54:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,808 rows / 7,777 parsed. The shard is past 60% completion with all outputs checkpointed to GCS.

## [2026-07-03T13:04:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,064 rows / 8,033 parsed. Phi inference remains stable and within the active budget estimate.

## [2026-07-03T13:14:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,320 rows / 8,288 parsed. GCS checkpointing and Vertex-only inference remain intact.

## [2026-07-03T13:24:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,576 rows / 8,544 parsed. A brief copy miss occurred during GCS sync, then retry confirmed the ledger was intact and advanced.

## [2026-07-03T13:34:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,832 rows / 8,800 parsed. The Phi tranche continues to save completed work to GCS at the expected cadence.

## [2026-07-03T13:44:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,088 rows / 9,056 parsed. Approximately 3,712 requests remain in the shard, all still running on Vertex.

## [2026-07-03T13:54:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,344 rows / 9,309 parsed. The shard is past 73% completion and continues under the reduced chunk size.

## [2026-07-03T14:04:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,600 rows / 9,563 parsed. Three quarters of the shard are complete and checkpointed in GCS.

## [2026-07-03T14:14:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,856 rows / 9,818 parsed. The shard remains healthy with 2,944 requests left.

## [2026-07-03T14:24:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,112 rows / 10,074 parsed. The run is past 79% completion and remains Vertex-only.

## [2026-07-03T14:34:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,368 rows / 10,329 parsed. The shard continues to advance with 2,432 requests remaining.

## [2026-07-03T14:44:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,624 rows / 10,584 parsed. Less than 2,200 requests remain in the shard.

## [2026-07-03T14:54:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,880 rows / 10,840 parsed. Fifteen 128-row chunks remain before shard completion.

## [2026-07-03T15:04:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,136 rows / 11,095 parsed. Thirteen 128-row chunks remain before shard completion.

## [2026-07-03T15:14:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,392 rows / 11,351 parsed. Eleven chunks remain before shard completion.

## [2026-07-03T15:24:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,648 rows / 11,607 parsed. Nine chunks remain before shard completion.

## [2026-07-03T15:34:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,904 rows / 11,863 parsed. Seven chunks remain before shard completion.

## [2026-07-03T15:44:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,160 rows / 12,119 parsed. Five chunks remain before shard completion.

## [2026-07-03T15:54:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,416 rows / 12,375 parsed. Three chunks remain before shard completion.

## [2026-07-03T16:04:00Z] P3/A-301-IIPR-NAMED-POLL
- Rerun job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,672 rows / 12,631 parsed. One final chunk remains before shard completion.

## [2026-07-03T15:06:00Z] P3/A-301-IIPR-NAMED-COMPLETE
- Append-only timestamp correction: the preceding poll headings from `2026-07-03T15:14:00Z` through `2026-07-03T16:04:00Z` overshot the wall clock. Authoritative Vertex/GCS timestamps are `createTime=2026-07-03T09:23:26.723872Z`, `startTime=2026-07-03T09:31:41Z`, `endTime=2026-07-03T15:02:49Z`; run artifacts were not modified.
- Job `projects/987318647780/locations/us-central1/customJobs/4048387528410005504` finished `JOB_STATE_SUCCEEDED`. Worker summary: `n_requests=12800`, `n_outputs=12800`, `valid_json_rate=0.99671875`, `sim.jsonl` rows `128`.
- Downloaded the completed run artifacts from GCS to ignored local path `runs/p3/calib-2019-g1-iipr-named-v1/` for downstream collection. Booked rerun cost at `$1.70`; cumulative estimated actual spend `$2.76`, below the `$85` hard stop.

## [2026-07-03T15:09:00Z] P3/A-301-IIPR-ALIAS-LAUNCH
- Launched the paired alias shard for ticker `IIPR`: job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840`, run id `calib-2019-g1-iipr-alias-v1`, display name `agorasim-p3-iipr-alias-v1`.
- Job is `JOB_STATE_PENDING` with explicit `--chunk-size 128`, `--gpu-memory-utilization 0.85`, and `--enforce-eager`. It uses only GCS-cached model weights on Vertex.
- Unrelated project Vertex jobs are currently running/pending, so this job may queue without cancelling sibling work. Conservative cumulative budget estimate is `$4.46`, below the `$85` hard stop.

## [2026-07-03T15:19:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` is `JOB_STATE_RUNNING` with start time `2026-07-03T15:10:20Z`.
- Vertex logs confirm Qwen loaded from `/tmp/agorasim-models/Qwen__Qwen2.5-1.5B-Instruct`; first `outputs.jsonl` checkpoint landed with 128 rows / 128 parsed.

## [2026-07-03T15:29:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 512 rows / 509 parsed. Alias shard chunking is stable under the 128-row setting.

## [2026-07-03T15:39:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 768 rows / 765 parsed. A brief GCS copy miss during sync retried cleanly.

## [2026-07-03T15:49:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,152 rows / 1,149 parsed. The alias shard continues on Vertex using the Qwen tranche.

## [2026-07-03T15:59:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,408 rows / 1,404 parsed. Qwen inference remains stable on Vertex.

## [2026-07-03T16:09:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,664 rows / 1,657 parsed. The alias shard remains on the Qwen tranche.

## [2026-07-03T16:19:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,920 rows / 1,913 parsed. The Qwen tranche is proceeding with GCS checkpoints.

## [2026-07-03T16:29:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,176 rows / 2,168 parsed. The run remains stable at the reduced chunk size.

## [2026-07-03T16:39:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,432 rows / 2,424 parsed. The Qwen tranche continues to checkpoint cleanly to GCS.

## [2026-07-03T16:49:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,816 rows / 2,808 parsed. The alias shard remains healthy and fully Vertex-run.

## [2026-07-03T16:59:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,072 rows / 3,063 parsed. The Qwen tranche is nearly one quarter complete.

## [2026-07-03T17:09:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,328 rows / 3,319 parsed. The alias shard remains within expected parse-rate bounds.

## [2026-07-03T17:19:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,584 rows / 3,574 parsed. The run remains healthy in the Qwen tranche.

## [2026-07-03T17:29:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,840 rows / 3,829 parsed. The alias shard continues at the expected checkpoint cadence.

## [2026-07-03T17:39:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,096 rows / 4,084 parsed. The shard is 32% complete and remains on Vertex-only execution.

## [2026-07-03T17:49:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,352 rows / 4,337 parsed. The Qwen tranche remains stable under the reduced chunk size.

## [2026-07-03T17:59:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,608 rows / 4,592 parsed. The alias shard is a little over 36% complete.

## [2026-07-03T18:09:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,992 rows / 4,975 parsed. The alias shard is approaching the end of the Qwen half.

## [2026-07-03T18:19:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,248 rows / 5,230 parsed. The Qwen tranche is nearing completion before the Phi model switch.

## [2026-07-03T18:29:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,504 rows / 5,485 parsed. The alias Qwen tranche continues to checkpoint cleanly.

## [2026-07-03T18:39:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,760 rows / 5,741 parsed. A brief GCS copy miss during sync retried cleanly; the Qwen tranche remains near completion.

## [2026-07-03T18:49:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,016 rows / 5,997 parsed. The Qwen tranche is within three chunks of completion.

## [2026-07-03T18:07:00Z] P3/A-301-IIPR-ALIAS-MODEL-SWITCH
- Append-only timestamp correction: recent alias poll headings from `2026-07-03T18:09:00Z` through `2026-07-03T18:49:00Z` were written ahead of the actual UTC clock while polling. Authoritative timestamps are the Vertex/GCS timestamps in this entry and subsequent entries.
- `outputs.jsonl` reached 6,400 rows / 6,381 parsed, completing the Qwen request tranche for the alias shard.
- Vertex logs confirm `microsoft/Phi-3.5-mini-instruct` loaded from `/tmp/agorasim-models/microsoft__Phi-3.5-mini-instruct` at `2026-07-03T18:06:07Z`, with memory profiling completed on the T4 worker. One vLLM KV-cache recompute warning was observed; the job remains `JOB_STATE_RUNNING`.

## [2026-07-03T18:17:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- Phi outputs are checkpointing: `outputs.jsonl` advanced to 7,040 rows / 7,015 parsed after the model switch.

## [2026-07-03T18:27:00Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,424 rows / 7,398 parsed. Phi chunking is stable after the model transition.

## [2026-07-03T18:37:10Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 7,680 rows / 7,654 parsed. The last two-minute poll showed no new checkpoint yet, consistent with a Phi chunk still in flight rather than a failure signal.

## [2026-07-03T18:47:07Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,064 rows / 8,038 parsed. A brief flat poll resolved with the next Phi checkpoint; no intervention needed.

## [2026-07-03T18:57:15Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,320 rows / 8,294 parsed. The Phi tranche continues to checkpoint after short in-flight pauses.

## [2026-07-03T19:07:22Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 8,576 rows / 8,550 parsed. The most recent poll was flat after the prior checkpoint; this remains within the observed chunk cadence.

## [2026-07-03T19:17:28Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,960 rows / 8,934 parsed. The alias shard is roughly 70% through the full 12,800 request set.

## [2026-07-03T19:27:35Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,216 rows / 9,189 parsed. The Phi tranche remains stable, with progress continuing after normal chunk pauses.

## [2026-07-03T19:37:41Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 9,472 rows / 9,443 parsed. The latest interval was a normal in-flight pause after the prior checkpoint.

## [2026-07-03T19:47:49Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,856 rows / 9,825 parsed. The shard is over three quarters complete and still checkpointing normally.

## [2026-07-03T19:57:55Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,240 rows / 10,209 parsed. The alias shard has reached 80% of the full request set.

## [2026-07-03T20:08:06Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 10,496 rows / 10,463 parsed. The job remains in the final stretch with normal checkpoint pacing.

## [2026-07-03T20:18:14Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,880 rows / 10,847 parsed. The final quarter continues to progress under the Vertex T4 worker.

## [2026-07-03T20:28:26Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,264 rows / 11,230 parsed. The shard has fewer than 1,600 outputs remaining before the 12,800-row target.

## [2026-07-03T20:38:31Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 11,520 rows / 11,486 parsed. The shard has 1,280 outputs remaining; the latest poll was a normal in-flight pause after the prior checkpoint.

## [2026-07-03T20:48:46Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,904 rows / 11,870 parsed. The shard has 896 outputs remaining and continues to checkpoint on Vertex.

## [2026-07-03T20:58:56Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,288 rows / 12,254 parsed. Four 128-row chunks remain before the 12,800-row target.

## [2026-07-03T21:09:10Z] P3/A-301-IIPR-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 12,544 rows / 12,510 parsed. Two 128-row chunks remain before the 12,800-row target.

## [2026-07-03T21:17:35Z] P3/A-301-IIPR-ALIAS-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/8686057205624995840` completed with `JOB_STATE_SUCCEEDED` at `2026-07-03T21:14:31Z`.
- Downloaded artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-iipr-alias-v1` into ignored local path `runs/p3/calib-2019-g1-iipr-alias-v1/`.
- Artifact QA: `requests.jsonl` 12,800 rows, `outputs.jsonl` 12,800 rows / 12,765 parsed, `sim.jsonl` 128 rows, worker `valid_json_rate=0.997265625`.
- Collector QA over the available P3 artifacts passed: G3 kill condition does not fire for the current IIPR named+alias artifact set.
- Budget actual recorded: 6.11 T4 spot wall hours at `$0.30/hr` = `$1.83`; cumulative ledger now `$4.59`, well below the `$85` R5 hard stop.

## [2026-07-03T21:19:13Z] P3/A-302-IGC-NAMED-LAUNCH
- Launched next calibration shard in configured order: `IGC` / `named`, run id `calib-2019-g1-igc-named-v1`.
- Vertex job `projects/987318647780/locations/us-central1/customJobs/37070043120402432`, display `agorasim-p3-igc-named-v1`; initial state `JOB_STATE_PENDING` with create time `2026-07-03T21:18:54.953014Z`.
- GCS output directory: `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-igc-named-v1`.
- Spec recorded at `docs/vertex_job_specs/agorasim-p3-igc-named-v1.json`; the launch keeps `--chunk-size 128`, `--gpu-memory-utilization 0.85`, and `--enforce-eager` so model weights/inference remain on Vertex.
- Budget state estimate advanced to `$6.29` cumulative, still below the `$85` R5 hard stop.

## [2026-07-03T21:29:47Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` is `JOB_STATE_RUNNING`, with Vertex start time `2026-07-03T21:21:55Z`.
- First checkpoints are healthy: `outputs.jsonl` advanced to 256 rows / 256 parsed for `calib-2019-g1-igc-named-v1`.

## [2026-07-03T21:39:58Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 640 rows / 640 parsed. The IGC named shard is checkpointing cleanly in the first Qwen tranche.

## [2026-07-03T21:50:06Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,024 rows / 1,024 parsed. Early IGC named outputs remain fully parse-valid.

## [2026-07-03T22:01:24Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,408 rows / 1,407 parsed. One non-parsed row has appeared, but the observed parse-valid rate remains high.

## [2026-07-03T22:12:18Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,792 rows / 1,788 parsed. Parse-valid rate remains high while the Qwen tranche continues.

## [2026-07-03T22:23:45Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,176 rows / 2,172 parsed after a transient GCS copy miss retried cleanly.

## [2026-07-03T22:34:13Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,560 rows / 2,555 parsed. The Qwen tranche is 40% complete for this shard.

## [2026-07-03T22:45:09Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 2,816 rows / 2,810 parsed. The latest interval was a normal in-flight pause after the prior checkpoint.

## [2026-07-03T22:55:29Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,200 rows / 3,192 parsed. The shard is halfway through the Qwen tranche.

## [2026-07-03T23:06:43Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 3,456 rows / 3,445 parsed. The latest interval was a normal in-flight pause after the prior checkpoint.

## [2026-07-03T23:16:54Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,840 rows / 3,828 parsed. The Qwen tranche remains stable and continues to checkpoint.

## [2026-07-03T23:27:21Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,096 rows / 4,082 parsed. The Qwen tranche is 64% complete for this shard.

## [2026-07-03T23:37:57Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 4,352 rows / 4,337 parsed. The latest interval was a normal in-flight pause after the prior checkpoint.

## [2026-07-03T23:48:24Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 4,608 rows / 4,592 parsed. The latest interval was a normal in-flight pause after the prior checkpoint.

## [2026-07-03T23:58:46Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,992 rows / 4,970 parsed. The Qwen tranche is approaching the final 1,408 outputs before model switch.

## [2026-07-04T00:09:10Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,248 rows / 5,224 parsed. UTC date rolled to `2026-07-04`; timestamps in this log remain authoritative UTC.

## [2026-07-04T00:19:26Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 5,504 rows / 5,475 parsed. The Qwen tranche is 896 outputs from the model switch.

## [2026-07-04T01:38:35Z] P3/A-302-IGC-NAMED-RESUME-POLL
- Resumed polling after an interactive handoff gap; no local heavy compute was run during the gap.
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,448 rows / 8,410 parsed. The Qwen tranche has completed and Phi outputs are checkpointing.
- PowerShell-safe Vertex log query for explicit Phi load lines returned no matching lines, so current status is based on Vertex job state plus GCS artifact counts.

## [2026-07-04T01:51:09Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,832 rows / 8,794 parsed. The Phi tranche continues to checkpoint after the model switch.

## [2026-07-04T02:01:56Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 9,088 rows / 9,050 parsed. Phi checkpointing continues with normal in-flight pauses.

## [2026-07-04T02:12:37Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 9,472 rows / 9,433 parsed. The latest interval was a normal in-flight pause after the prior checkpoint.

## [2026-07-04T02:23:22Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,856 rows / 9,816 parsed. The Phi tranche is over halfway complete.

## [2026-07-04T02:33:59Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,240 rows / 10,200 parsed. The shard has reached 80% of the full 12,800-output target.

## [2026-07-04T02:44:50Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 10,496 rows / 10,456 parsed. The latest interval was a normal in-flight pause after the prior checkpoint.

## [2026-07-04T02:59:03Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,008 rows / 10,964 parsed. A transient GCS copy miss retried cleanly during this interval.

## [2026-07-04T03:12:44Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 11,392 rows / 11,348 parsed. The shard has 1,408 outputs remaining before the 12,800-output target.

## [2026-07-04T03:23:53Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 11,776 rows / 11,732 parsed. The shard has 1,024 outputs remaining before the 12,800-output target.

## [2026-07-04T03:33:37Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,160 rows / 12,115 parsed. Five chunks remain, and a transient GCS copy miss retried cleanly.

## [2026-07-04T03:44:25Z] P3/A-302-IGC-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 12,416 rows / 12,371 parsed. Three chunks remain before the 12,800-output target.

## [2026-07-04T03:55:38Z] P3/A-302-IGC-NAMED-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/37070043120402432` completed with `JOB_STATE_SUCCEEDED` at `2026-07-04T03:53:01Z`.
- Downloaded artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-igc-named-v1` into ignored local path `runs/p3/calib-2019-g1-igc-named-v1/`.
- Artifact QA: `requests.jsonl` 12,800 rows, `outputs.jsonl` 12,800 rows / 12,755 parsed, `sim.jsonl` 128 rows, worker `valid_json_rate=0.996484375`.
- Collector QA over the available P3 artifacts passed: G3 kill condition does not fire for the current IIPR named+alias plus IGC named artifact set.
- Budget actual recorded: 6.57 T4 spot wall hours at `$0.30/hr` = `$1.97`; cumulative ledger now `$6.56`, well below the `$85` R5 hard stop.

## [2026-07-04T03:57:26Z] P3/A-303-IGC-ALIAS-LAUNCH
- Launched next calibration shard in configured order: `IGC` / `alias`, run id `calib-2019-g1-igc-alias-v1`.
- Vertex job `projects/987318647780/locations/us-central1/customJobs/6284292802004123648`, display `agorasim-p3-igc-alias-v1`; initial state `JOB_STATE_PENDING` with create time `2026-07-04T03:57:09.218398Z`.
- GCS output directory: `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-igc-alias-v1`.
- Spec recorded at `docs/vertex_job_specs/agorasim-p3-igc-alias-v1.json`; the launch keeps `--chunk-size 128`, `--gpu-memory-utilization 0.85`, and `--enforce-eager` so model weights/inference remain on Vertex.
- Budget state estimate advanced to `$8.53` cumulative, still below the `$85` R5 hard stop.

## [2026-07-04T04:10:42Z] P3/A-303-IGC-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6284292802004123648` is `JOB_STATE_RUNNING`, with Vertex start time `2026-07-04T04:01:00Z`.
- First checkpoints are healthy: `outputs.jsonl` advanced to 384 rows / 383 parsed for `calib-2019-g1-igc-alias-v1`.

## [2026-07-04T04:22:06Z] P3/A-303-IGC-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6284292802004123648` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 768 rows / 767 parsed. The latest interval was a normal in-flight pause after the prior checkpoint.

## [2026-07-04T04:33:14Z] P3/A-303-IGC-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6284292802004123648` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,280 rows / 1,278 parsed. Early IGC alias outputs are checkpointing normally.

## [2026-07-04T04:44:24Z] P3/A-303-IGC-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6284292802004123648` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,792 rows / 1,787 parsed. The Qwen tranche continues with a high parse-valid rate.

## [2026-07-04T04:55:12Z] P3/A-303-IGC-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6284292802004123648` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,176 rows / 2,171 parsed. The Qwen tranche continues to checkpoint normally.

## [2026-07-04T05:06:10Z] P3/A-303-IGC-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6284292802004123648` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,688 rows / 2,682 parsed. The Qwen tranche continues with normal checkpoint pacing.

## [2026-07-04T05:17:21Z] P3/A-303-IGC-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6284292802004123648` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,072 rows / 3,065 parsed. The Qwen tranche is approaching the halfway point.

## [2026-07-04T05:26:37Z] P3/A-303-IGC-ALIAS-SHUTDOWN-HANDOFF
- Preparing for local computer shutdown. No key computation is local: active model weights/inference are on Vertex job `projects/987318647780/locations/us-central1/customJobs/6284292802004123648`.
- Job state is `JOB_STATE_RUNNING`; display `agorasim-p3-igc-alias-v1`; create time `2026-07-04T03:57:09.218398Z`; start time `2026-07-04T04:01:00Z`.
- Active run id is `calib-2019-g1-igc-alias-v1`; GCS output directory is `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-igc-alias-v1`.
- Latest `outputs.jsonl` checkpoint before shutdown handoff: 3,328 rows / 3,319 parsed.
- Resume by checking the Vertex job state and GCS outputs, then continue polling or collect artifacts if the job has reached `JOB_STATE_SUCCEEDED`. Local app shutdown should not stop the Vertex job or remove GCS progress.

## [2026-07-04T13:06:35Z] P3/A-303-IGC-ALIAS-COMPLETE
- Resumed after local shutdown; Vertex job `projects/987318647780/locations/us-central1/customJobs/6284292802004123648` had completed with `JOB_STATE_SUCCEEDED` at `2026-07-04T09:50:06Z`.
- Downloaded artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-igc-alias-v1` into ignored local path `runs/p3/calib-2019-g1-igc-alias-v1/`.
- Artifact QA: `requests.jsonl` 12,800 rows, `outputs.jsonl` 12,800 rows / 12,755 parsed, `sim.jsonl` 128 rows, worker `valid_json_rate=0.996484375`.
- Collector QA over the available P3 artifacts passed: G3 kill condition does not fire for the current IIPR and IGC named+alias artifact set.
- Budget actual recorded: 5.88 T4 spot wall hours at `$0.30/hr` = `$1.76`; cumulative ledger now `$8.32`, well below the `$85` R5 hard stop.

## [2026-07-04T13:08:28Z] P3/A-304-GOLD-NAMED-LAUNCH
- Launched next calibration shard in configured order: `GOLD` / `named`, run id `calib-2019-g1-gold-named-v1`.
- Vertex job `projects/987318647780/locations/us-central1/customJobs/955074291383140352`, display `agorasim-p3-gold-named-v1`; initial state `JOB_STATE_PENDING` with create time `2026-07-04T13:08:10.531576Z`.
- GCS output directory: `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-gold-named-v1`.
- Spec recorded at `docs/vertex_job_specs/agorasim-p3-gold-named-v1.json`; the launch keeps `--chunk-size 128`, `--gpu-memory-utilization 0.85`, and `--enforce-eager` so model weights/inference remain on Vertex.
- Budget state estimate advanced to `$10.29` cumulative, still below the `$85` R5 hard stop.

## [2026-07-04T13:21:59Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` is `JOB_STATE_RUNNING`, with Vertex start time `2026-07-04T13:12:05Z`.
- First checkpoints are healthy: `outputs.jsonl` advanced to 256 rows / 255 parsed for `calib-2019-g1-gold-named-v1`.

## [2026-07-04T13:30:13Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- GCS checkpoint is healthy after a transient copy retry: `outputs.jsonl` is present with 640 rows / 639 parsed and object timestamp `2026-07-04T13:29:57Z`.

## [2026-07-04T13:41:24Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,024 rows / 1,023 parsed for `calib-2019-g1-gold-named-v1`; progress remains consistent with prior P3 calibration shards.

## [2026-07-04T13:52:06Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` is at 1,280 rows / 1,276 parsed, for a current valid JSON rate of `0.996875`.

## [2026-07-04T14:02:49Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,664 rows / 1,658 parsed, with current valid JSON rate `0.996394`.

## [2026-07-04T14:16:57Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,048 rows / 2,040 parsed, with current valid JSON rate `0.996094`.

## [2026-07-04T14:27:41Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,432 rows / 2,423 parsed, with current valid JSON rate `0.996299`.

## [2026-07-04T14:41:58Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,816 rows / 2,806 parsed, with current valid JSON rate `0.996449`.

## [2026-07-04T14:52:40Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,200 rows / 3,189 parsed, with current valid JSON rate `0.996562`.

## [2026-07-04T15:02:00Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,456 rows / 3,444 parsed, with current valid JSON rate `0.996528`.

## [2026-07-04T15:11:17Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,712 rows / 3,700 parsed, with current valid JSON rate `0.996767`.

## [2026-07-04T15:20:45Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,096 rows / 4,084 parsed, with current valid JSON rate `0.99707`.

## [2026-07-04T15:32:10Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,352 rows / 4,338 parsed, with current valid JSON rate `0.996783`.

## [2026-07-04T15:38:11Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- GCS verification after a transient copy miss shows `outputs.jsonl` at 4,608 rows / 4,594 parsed, with current valid JSON rate `0.996962`.

## [2026-07-04T15:49:45Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,864 rows / 4,850 parsed, with current valid JSON rate `0.997122`.

## [2026-07-04T16:01:10Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,248 rows / 5,231 parsed, with current valid JSON rate `0.996761`.

## [2026-07-04T16:12:44Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,632 rows / 5,613 parsed, with current valid JSON rate `0.996626`.

## [2026-07-04T16:24:17Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,016 rows / 5,995 parsed, with current valid JSON rate `0.996509`.

## [2026-07-04T16:35:37Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- Halfway checkpoint: `outputs.jsonl` advanced to 6,400 rows / 6,379 parsed, with current valid JSON rate `0.996719`.

## [2026-07-04T16:47:01Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,040 rows / 7,017 parsed, with current valid JSON rate `0.996733`.

## [2026-07-04T16:58:23Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,552 rows / 7,526 parsed, with current valid JSON rate `0.996557`.

## [2026-07-04T17:09:46Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,936 rows / 7,910 parsed, with current valid JSON rate `0.996724`.

## [2026-07-04T17:21:06Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,320 rows / 8,291 parsed, with current valid JSON rate `0.996514`.

## [2026-07-04T17:32:36Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,704 rows / 8,675 parsed, with current valid JSON rate `0.996668`.

## [2026-07-04T17:43:57Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,088 rows / 9,057 parsed, with current valid JSON rate `0.996589`.

## [2026-07-04T17:55:20Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,344 rows / 9,313 parsed, with current valid JSON rate `0.996682`.

## [2026-07-04T18:06:48Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,728 rows / 9,694 parsed, with current valid JSON rate `0.996505`.

## [2026-07-04T18:18:08Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,112 rows / 10,078 parsed, with current valid JSON rate `0.996638`.

## [2026-07-04T18:29:31Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,496 rows / 10,461 parsed, with current valid JSON rate `0.996665`.

## [2026-07-04T18:40:52Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,880 rows / 10,843 parsed, with current valid JSON rate `0.996599`.

## [2026-07-04T18:52:11Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,264 rows / 11,227 parsed, with current valid JSON rate `0.996715`.

## [2026-07-04T19:03:32Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,648 rows / 11,611 parsed, with current valid JSON rate `0.996823`.

## [2026-07-04T19:13:54Z] P3/A-304-GOLD-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,032 rows / 11,994 parsed, with current valid JSON rate `0.996842`.

## [2026-07-04T19:38:24Z] P3/A-304-GOLD-NAMED-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/955074291383140352` completed with `JOB_STATE_SUCCEEDED` at `2026-07-04T19:35:04Z`.
- Downloaded artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-gold-named-v1` into ignored local path `runs/p3/calib-2019-g1-gold-named-v1/`.
- Artifact QA: `requests.jsonl` 12,800 rows, `outputs.jsonl` 12,800 rows / 12,759 parsed, `sim.jsonl` 128 rows, worker `valid_json_rate=0.996796875`.
- Collector QA over the available P3 artifacts passed: G3 kill condition does not fire for the current IIPR, IGC, and GOLD named artifact set.
- Budget actual recorded: 6.45 T4 spot wall hours at `$0.30/hr` = `$1.93`; cumulative ledger now `$10.25`, well below the `$85` R5 hard stop.

## [2026-07-04T19:41:39Z] P3/A-305-GOLD-ALIAS-LAUNCH
- Launched next calibration shard in configured order: `GOLD` / `alias`, run id `calib-2019-g1-gold-alias-v1`.
- Vertex job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024`, display `agorasim-p3-gold-alias-v1`; initial state `JOB_STATE_PENDING` with create time `2026-07-04T19:41:39.657348Z`.
- GCS output directory: `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-gold-alias-v1`; pre-launch manifest is present in GCS.
- Spec recorded at `docs/vertex_job_specs/agorasim-p3-gold-alias-v1.json`; the launch keeps `--chunk-size 128`, `--gpu-memory-utilization 0.85`, and `--enforce-eager` so model weights/inference remain on Vertex.
- Budget state estimate advanced to `$12.18` cumulative, still below the `$85` R5 hard stop.

## [2026-07-04T19:53:22Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` is `JOB_STATE_RUNNING`, with Vertex start time `2026-07-04T19:45:14Z`.
- First checkpoints are healthy: `outputs.jsonl` advanced to 256 rows / 254 parsed for `calib-2019-g1-gold-alias-v1`.

## [2026-07-04T20:04:56Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 640 rows / 638 parsed, with current valid JSON rate `0.996875`.

## [2026-07-04T20:16:17Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,024 rows / 1,022 parsed, with current valid JSON rate `0.998047`.

## [2026-07-04T20:27:40Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,408 rows / 1,405 parsed, with current valid JSON rate `0.997869`.

## [2026-07-04T20:39:01Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,792 rows / 1,786 parsed, with current valid JSON rate `0.996652`.

## [2026-07-04T20:50:20Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,048 rows / 2,040 parsed, with current valid JSON rate `0.996094`.

## [2026-07-04T21:02:30Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,432 rows / 2,423 parsed, with current valid JSON rate `0.996299`.

## [2026-07-04T21:13:57Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,816 rows / 2,806 parsed, with current valid JSON rate `0.996449`.

## [2026-07-04T21:25:19Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,200 rows / 3,187 parsed, with current valid JSON rate `0.995938`.

## [2026-07-04T21:36:41Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,584 rows / 3,568 parsed, with current valid JSON rate `0.995536`.

## [2026-07-04T21:48:03Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,968 rows / 3,952 parsed, with current valid JSON rate `0.995968`.

## [2026-07-04T21:59:30Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- GCS verification after a transient copy miss shows `outputs.jsonl` at 4,352 rows / 4,334 parsed, with current valid JSON rate `0.995864`.

## [2026-07-04T22:11:06Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,608 rows / 4,590 parsed, with current valid JSON rate `0.996094`.

## [2026-07-04T22:22:28Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,992 rows / 4,970 parsed, with current valid JSON rate `0.995593`.

## [2026-07-04T22:33:54Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,376 rows / 5,352 parsed, with current valid JSON rate `0.995536`.

## [2026-07-04T22:45:21Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,760 rows / 5,734 parsed, with current valid JSON rate `0.995486`.

## [2026-07-04T23:07:39Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- Halfway checkpoint crossed: `outputs.jsonl` advanced to 6,528 rows / 6,500 parsed, with current valid JSON rate `0.995711`.

## [2026-07-04T23:19:09Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,168 rows / 7,137 parsed, with current valid JSON rate `0.995675`.

## [2026-07-04T23:31:36Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,680 rows / 7,648 parsed, with current valid JSON rate `0.995833`.

## [2026-07-04T23:48:35Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,192 rows / 8,157 parsed, with current valid JSON rate `0.995728`.

## [2026-07-05T00:00:01Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,576 rows / 8,539 parsed, with current valid JSON rate `0.995686`.

## [2026-07-05T00:11:48Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- GCS verification after a transient copy miss shows `outputs.jsonl` at 8,960 rows / 8,922 parsed, with current valid JSON rate `0.995759`.

## [2026-07-05T00:23:41Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,216 rows / 9,177 parsed, with current valid JSON rate `0.995768`.

## [2026-07-05T00:35:20Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,600 rows / 9,561 parsed, with current valid JSON rate `0.995938`.

## [2026-07-05T00:46:50Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,984 rows / 9,943 parsed, with current valid JSON rate `0.995893`.

## [2026-07-05T00:58:23Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,368 rows / 10,326 parsed, with current valid JSON rate `0.995949`.

## [2026-07-05T01:09:50Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,752 rows / 10,710 parsed, with current valid JSON rate `0.996094`.

## [2026-07-05T01:21:27Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,136 rows / 11,094 parsed, with current valid JSON rate `0.996228`.

## [2026-07-05T01:32:57Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,520 rows / 11,478 parsed, with current valid JSON rate `0.996354`.

## [2026-07-05T01:47:55Z] P3/A-305-GOLD-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,032 rows / 11,989 parsed, with current valid JSON rate `0.996426`.

## [2026-07-05T02:15:31Z] P3/A-305-GOLD-ALIAS-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/6483278018352513024` completed with `JOB_STATE_SUCCEEDED` at `2026-07-05T02:12:13Z`.
- Downloaded artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-gold-alias-v1` into ignored local path `runs/p3/calib-2019-g1-gold-alias-v1/`.
- Artifact QA: `requests.jsonl` 12,800 rows, `outputs.jsonl` 12,800 rows / 12,755 parsed, `sim.jsonl` 128 rows, worker `valid_json_rate=0.996484375`.
- Collector QA over the available P3 artifacts passed: G3 kill condition does not fire for the current IIPR, IGC, and GOLD named+alias artifact set.
- Budget actual recorded: 6.51 T4 spot wall hours at `$0.30/hr` = `$1.95`; cumulative ledger now `$12.20`, well below the `$85` R5 hard stop.

## [2026-07-05T02:17:00Z] P3/A-306-RIOT-NAMED-LAUNCH
- Launched next calibration shard in configured order: `RIOT` / `named`, run id `calib-2019-g1-riot-named-v1`.
- Vertex job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704`, display `agorasim-p3-riot-named-v1`; initial state `JOB_STATE_PENDING` with create time `2026-07-05T02:17:00.333112Z`.
- GCS output directory: `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-riot-named-v1`; pre-launch manifest is present in GCS.
- Spec recorded at `docs/vertex_job_specs/agorasim-p3-riot-named-v1.json`; the launch keeps `--chunk-size 128`, `--gpu-memory-utilization 0.85`, and `--enforce-eager` so model weights/inference remain on Vertex.
- Budget state estimate advanced to `$14.15` cumulative, still below the `$85` R5 hard stop.

## [2026-07-05T02:25:12Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` is `JOB_STATE_RUNNING`, with Vertex start time `2026-07-05T02:19:47Z`.
- First checkpoint is healthy: `outputs.jsonl` advanced to 128 rows / 128 parsed for `calib-2019-g1-riot-named-v1`.

## [2026-07-05T02:36:46Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 640 rows / 640 parsed, with current valid JSON rate `1.0`.

## [2026-07-05T02:48:15Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,024 rows / 1,024 parsed, with current valid JSON rate `1.0`.

## [2026-07-05T02:59:40Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,536 rows / 1,535 parsed, with current valid JSON rate `0.999349`.

## [2026-07-05T03:11:08Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,920 rows / 1,917 parsed, with current valid JSON rate `0.998438`.

## [2026-07-05T03:22:46Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,304 rows / 2,301 parsed, with current valid JSON rate `0.998698`.

## [2026-07-05T03:34:21Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,688 rows / 2,685 parsed, with current valid JSON rate `0.998884`.

## [2026-07-05T03:48:03Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,072 rows / 3,069 parsed, with current valid JSON rate `0.999023`.

## [2026-07-05T03:59:27Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,456 rows / 3,450 parsed, with current valid JSON rate `0.998264`.

## [2026-07-05T04:10:49Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,840 rows / 3,834 parsed, with current valid JSON rate `0.998438`.

## [2026-07-05T04:22:00Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,224 rows / 4,216 parsed, with current valid JSON rate `0.998106`.

## [2026-07-05T04:32:56Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,480 rows / 4,471 parsed, with current valid JSON rate `0.997991`.

## [2026-07-05T04:43:51Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,864 rows / 4,854 parsed, with current valid JSON rate `0.997944`.

## [2026-07-05T04:54:46Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,248 rows / 5,236 parsed, with current valid JSON rate `0.997713`.

## [2026-07-05T05:05:42Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,632 rows / 5,619 parsed, with current valid JSON rate `0.997692`.

## [2026-07-05T05:16:36Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,016 rows / 6,001 parsed, with current valid JSON rate `0.997507`.

## [2026-07-05T05:27:40Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` reached the 6,400-row midpoint / 6,385 parsed, with current valid JSON rate `0.997656`.

## [2026-07-05T05:38:40Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,168 rows / 7,153 parsed, with current valid JSON rate `0.997907`.

## [2026-07-05T05:49:38Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,552 rows / 7,537 parsed, with current valid JSON rate `0.998014`.

## [2026-07-05T06:00:33Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,936 rows / 7,921 parsed, with current valid JSON rate `0.998110`.

## [2026-07-05T06:11:28Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,320 rows / 8,305 parsed, with current valid JSON rate `0.998197`.

## [2026-07-05T06:23:03Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,704 rows / 8,689 parsed, with current valid JSON rate `0.998277`.

## [2026-07-05T06:33:59Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,088 rows / 9,073 parsed, with current valid JSON rate `0.998349`.

## [2026-07-05T06:45:00Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,472 rows / 9,457 parsed, with current valid JSON rate `0.998416`.

## [2026-07-05T06:56:06Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,856 rows / 9,841 parsed, with current valid JSON rate `0.998478`.

## [2026-07-05T07:07:08Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,240 rows / 10,225 parsed, with current valid JSON rate `0.998535`.

## [2026-07-05T07:18:10Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,624 rows / 10,609 parsed, with current valid JSON rate `0.998588`.

## [2026-07-05T07:29:25Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,008 rows / 10,991 parsed, with current valid JSON rate `0.998456`.

## [2026-07-05T07:40:26Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,392 rows / 11,375 parsed, with current valid JSON rate `0.998508`.

## [2026-07-05T07:51:23Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,776 rows / 11,759 parsed, with current valid JSON rate `0.998556`.

## [2026-07-05T08:02:19Z] P3/A-306-RIOT-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,160 rows / 12,143 parsed, with current valid JSON rate `0.998602`.

## [2026-07-05T08:22:58Z] P3/A-306-RIOT-NAMED-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/6728667023439560704` completed as `JOB_STATE_SUCCEEDED` at `2026-07-05T08:20:03Z`.
- Downloaded five expected artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-riot-named-v1/` into ignored local run storage for QA.
- Raw QA: `requests.jsonl` 12,800 rows; `outputs.jsonl` 12,800 rows / 12,783 parsed; valid JSON rate `0.998672`; `sim.jsonl` 128 rows.
- Collector QA: `scripts/p3_collect_calibration.py` completed on local `runs/p3`; RIOT named appears in RQ1/RQ2 summaries and G3 kill condition still does not fire on available P3 artifacts.
- Budget ledger updated with 6.05 wall hours at `$0.30/hr` (`$1.82`), bringing cumulative estimated spend to `$14.02`.

## [2026-07-05T08:26:23Z] P3/A-307-RIOT-ALIAS-LAUNCH
- Launched RIOT alias calibration shard on Vertex: `projects/987318647780/locations/us-central1/customJobs/130788016225517568` (`agorasim-p3-riot-alias-v1`), initial state `JOB_STATE_PENDING`.
- Run ID `calib-2019-g1-riot-alias-v1`; GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-riot-alias-v1`.
- Generated and retained Vertex job spec at `docs/vertex_job_specs/agorasim-p3-riot-alias-v1.json`.
- State now tracks RIOT alias as the only active job, with budget estimate set to `$15.97` pending actual completion cost.

## [2026-07-05T08:38:36Z] P3/A-307-RIOT-ALIAS-STARTUP
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` is `JOB_STATE_RUNNING`; worker start time `2026-07-05T08:29:40Z`.
- `requests.jsonl` is present in GCS and `outputs.jsonl` has started: 256 rows / 255 parsed, valid JSON rate `0.996094`.

## [2026-07-05T08:49:35Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 768 rows / 767 parsed, with current valid JSON rate `0.998698`.

## [2026-07-05T09:00:40Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,280 rows / 1,278 parsed, with current valid JSON rate `0.998438`.

## [2026-07-05T09:12:48Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,664 rows / 1,657 parsed, with current valid JSON rate `0.995793`.

## [2026-07-05T09:23:46Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,048 rows / 2,041 parsed, with current valid JSON rate `0.996582`.

## [2026-07-05T09:34:57Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,432 rows / 2,425 parsed, with current valid JSON rate `0.997122`.

## [2026-07-05T09:45:58Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,688 rows / 2,680 parsed, with current valid JSON rate `0.997024`.

## [2026-07-05T09:56:58Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,072 rows / 3,064 parsed, with current valid JSON rate `0.997396`.

## [2026-07-05T10:08:00Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,456 rows / 3,445 parsed, with current valid JSON rate `0.996817`.

## [2026-07-05T10:19:01Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,840 rows / 3,828 parsed, with current valid JSON rate `0.996875`.

## [2026-07-05T10:30:01Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,096 rows / 4,084 parsed, with current valid JSON rate `0.997070`.

## [2026-07-05T10:41:12Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,480 rows / 4,466 parsed, with current valid JSON rate `0.996875`.

## [2026-07-05T10:52:22Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,864 rows / 4,849 parsed, with current valid JSON rate `0.996916`.

## [2026-07-05T11:03:34Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,248 rows / 5,231 parsed, with current valid JSON rate `0.996761`.

## [2026-07-05T11:15:03Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,632 rows / 5,614 parsed, with current valid JSON rate `0.996804`.

## [2026-07-05T11:26:19Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,144 rows / 6,123 parsed, with current valid JSON rate `0.996582`.

## [2026-07-05T11:37:22Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` crossed the shard midpoint at 6,656 rows / 6,635 parsed, with current valid JSON rate `0.996845`.

## [2026-07-05T11:48:26Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,296 rows / 7,275 parsed, with current valid JSON rate `0.997122`.

## [2026-07-05T11:59:27Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,680 rows / 7,659 parsed, with current valid JSON rate `0.997266`.

## [2026-07-05T12:10:30Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,064 rows / 8,042 parsed, with current valid JSON rate `0.997272`.

## [2026-07-05T12:21:36Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,448 rows / 8,426 parsed, with current valid JSON rate `0.997396`.

## [2026-07-05T12:32:37Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,832 rows / 8,810 parsed, with current valid JSON rate `0.997509`.

## [2026-07-05T12:43:39Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,216 rows / 9,194 parsed, with current valid JSON rate `0.997613`.

## [2026-07-05T12:54:46Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,600 rows / 9,578 parsed, with current valid JSON rate `0.997708`.

## [2026-07-05T13:06:07Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,984 rows / 9,962 parsed, with current valid JSON rate `0.997796`.

## [2026-07-05T13:17:18Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,368 rows / 10,346 parsed, with current valid JSON rate `0.997878`.

## [2026-07-05T13:28:26Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,752 rows / 10,729 parsed, with current valid JSON rate `0.997861`.

## [2026-07-05T13:39:41Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,136 rows / 11,113 parsed, with current valid JSON rate `0.997935`.

## [2026-07-05T13:50:49Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,520 rows / 11,497 parsed, with current valid JSON rate `0.998003`.

## [2026-07-05T14:02:00Z] P3/A-307-RIOT-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,904 rows / 11,881 parsed, with current valid JSON rate `0.998068`.

## [2026-07-05T14:28:22Z] P3/A-307-RIOT-ALIAS-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/130788016225517568` completed as `JOB_STATE_SUCCEEDED` at `2026-07-05T14:28:06Z`.
- Downloaded five expected artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-riot-alias-v1/` into ignored local run storage for QA.
- Raw QA: `requests.jsonl` 12,800 rows; `outputs.jsonl` 12,800 rows / 12,777 parsed; valid JSON rate `0.998203`; `sim.jsonl` 128 rows.
- Collector QA: `scripts/p3_collect_calibration.py` completed on local `runs/p3`; RIOT alias appears in RQ1/RQ2 summaries and G3 kill condition still does not fire on available P3 artifacts.
- Budget ledger updated with 6.03 wall hours at `$0.30/hr` (`$1.81`), bringing cumulative estimated spend to `$15.83`.

## [2026-07-05T14:32:30Z] P3/A-308-CRBP-NAMED-LAUNCH
- Launched CRBP named calibration shard on Vertex: `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` (`agorasim-p3-crbp-named-v1`), initial state `JOB_STATE_PENDING`.
- Run ID `calib-2019-g1-crbp-named-v1`; GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-crbp-named-v1`.
- Generated and retained Vertex job spec at `docs/vertex_job_specs/agorasim-p3-crbp-named-v1.json`.
- State now tracks CRBP named as the only active job, with budget estimate set to `$17.78` pending actual completion cost.

## [2026-07-05T14:44:47Z] P3/A-308-CRBP-NAMED-STARTUP
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` is `JOB_STATE_RUNNING`; worker start time `2026-07-05T14:35:28Z`.
- `requests.jsonl` is present in GCS and `outputs.jsonl` has started: 256 rows / 256 parsed, valid JSON rate `1.000000`.

## [2026-07-05T14:55:52Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 768 rows / 768 parsed, with current valid JSON rate `1.000000`.

## [2026-07-05T15:07:03Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,280 rows / 1,278 parsed, with current valid JSON rate `0.998438`.

## [2026-07-05T15:18:10Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,664 rows / 1,658 parsed, with current valid JSON rate `0.996394`.

## [2026-07-05T15:29:16Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,048 rows / 2,041 parsed, with current valid JSON rate `0.996582`.

## [2026-07-05T15:40:20Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,432 rows / 2,423 parsed, with current valid JSON rate `0.996299`.

## [2026-07-05T15:51:26Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,816 rows / 2,807 parsed, with current valid JSON rate `0.996804`.

## [2026-07-05T16:02:30Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,200 rows / 3,189 parsed, with current valid JSON rate `0.996562`.

## [2026-07-05T16:13:38Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,584 rows / 3,572 parsed, with current valid JSON rate `0.996652`.

## [2026-07-05T16:25:21Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,968 rows / 3,956 parsed, with current valid JSON rate `0.996976`.

## [2026-07-05T16:36:20Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,352 rows / 4,338 parsed, with current valid JSON rate `0.996783`.

## [2026-07-05T16:47:28Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,736 rows / 4,719 parsed, with current valid JSON rate `0.996410`.

## [2026-07-05T16:58:30Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,120 rows / 5,103 parsed, with current valid JSON rate `0.996680`.

## [2026-07-05T17:09:39Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,376 rows / 5,358 parsed, with current valid JSON rate `0.996652`.

## [2026-07-05T17:20:40Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,760 rows / 5,742 parsed, with current valid JSON rate `0.996875`.

## [2026-07-05T17:31:43Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,144 rows / 6,125 parsed, with current valid JSON rate `0.996908`.

## [2026-07-05T17:42:46Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` crossed the shard midpoint at 6,784 rows / 6,760 parsed, with current valid JSON rate `0.996462`.

## [2026-07-05T17:53:52Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,424 rows / 7,397 parsed, with current valid JSON rate `0.996363`.

## [2026-07-05T18:05:28Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,808 rows / 7,780 parsed, with current valid JSON rate `0.996414`.

## [2026-07-05T18:16:31Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,192 rows / 8,163 parsed, with current valid JSON rate `0.996460`.

## [2026-07-05T18:27:36Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,576 rows / 8,547 parsed, with current valid JSON rate `0.996618`.

## [2026-07-05T18:38:40Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,960 rows / 8,930 parsed, with current valid JSON rate `0.996652`.

## [2026-07-05T18:49:41Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,216 rows / 9,185 parsed, with current valid JSON rate `0.996636`.

## [2026-07-05T19:00:47Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,600 rows / 9,569 parsed, with current valid JSON rate `0.996771`.

## [2026-07-05T19:11:56Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,984 rows / 9,953 parsed, with current valid JSON rate `0.996895`.

## [2026-07-05T19:22:59Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,368 rows / 10,337 parsed, with current valid JSON rate `0.997010`.

## [2026-07-05T19:34:04Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,752 rows / 10,720 parsed, with current valid JSON rate `0.997024`.

## [2026-07-05T19:45:06Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,008 rows / 10,975 parsed, with current valid JSON rate `0.997002`.

## [2026-07-05T19:56:07Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,392 rows / 11,359 parsed, with current valid JSON rate `0.997103`.

## [2026-07-05T20:07:15Z] P3/A-308-CRBP-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,776 rows / 11,743 parsed, with current valid JSON rate `0.997198`.

## [2026-07-05T20:41:04Z] P3/A-308-CRBP-NAMED-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/3986555392510394368` completed as `JOB_STATE_SUCCEEDED` at `2026-07-05T20:38:42Z`.
- Downloaded five expected artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-crbp-named-v1/` into ignored local run storage for QA.
- Raw QA: `requests.jsonl` 12,800 rows; `outputs.jsonl` 12,800 rows / 12,765 parsed; valid JSON rate `0.997266`; `sim.jsonl` 128 rows.
- Collector QA: `scripts/p3_collect_calibration.py` completed on local `runs/p3`; CRBP named appears in RQ1/RQ2 summaries and G3 kill condition still does not fire on available P3 artifacts.
- Budget ledger updated with 6.10 wall hours at `$0.30/hr` (`$1.83`), bringing cumulative estimated spend to `$17.66`.

## [2026-07-05T20:43:40Z] P3/A-309-CRBP-ALIAS-LAUNCH
- Launched CRBP alias calibration shard on Vertex: `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` (`agorasim-p3-crbp-alias-v1`), initial state `JOB_STATE_PENDING`.
- Run ID `calib-2019-g1-crbp-alias-v1`; GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-crbp-alias-v1`.
- Generated and retained Vertex job spec at `docs/vertex_job_specs/agorasim-p3-crbp-alias-v1.json`.
- State now tracks CRBP alias as the only active job, with budget estimate set to `$19.61` pending actual completion cost.

## [2026-07-05T20:55:52Z] P3/A-309-CRBP-ALIAS-STARTUP
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` is `JOB_STATE_RUNNING`; worker start time `2026-07-05T20:46:31Z`.
- `requests.jsonl` is present in GCS and `outputs.jsonl` has started: 256 rows / 255 parsed, valid JSON rate `0.996094`.

## [2026-07-05T21:06:57Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 768 rows / 767 parsed, with current valid JSON rate `0.998698`.

## [2026-07-05T21:18:19Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,280 rows / 1,277 parsed, with current valid JSON rate `0.997656`.

## [2026-07-05T21:29:22Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,664 rows / 1,657 parsed, with current valid JSON rate `0.995793`.

## [2026-07-05T21:40:19Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,176 rows / 2,167 parsed, with current valid JSON rate `0.995864`.

## [2026-07-05T21:51:13Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,560 rows / 2,551 parsed, with current valid JSON rate `0.996484`.

## [2026-07-05T22:02:06Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,944 rows / 2,932 parsed, with current valid JSON rate `0.995924`.

## [2026-07-05T22:13:02Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,328 rows / 3,314 parsed, with current valid JSON rate `0.995793`.

## [2026-07-05T22:23:56Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,712 rows / 3,697 parsed, with current valid JSON rate `0.995959`.

## [2026-07-05T22:34:56Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,968 rows / 3,953 parsed, with current valid JSON rate `0.996220`.

## [2026-07-05T22:45:55Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,352 rows / 4,335 parsed, with current valid JSON rate `0.996094`.

## [2026-07-05T22:56:50Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,736 rows / 4,715 parsed, with current valid JSON rate `0.995566`.

## [2026-07-05T23:07:46Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,120 rows / 5,098 parsed, with current valid JSON rate `0.995703`.

## [2026-07-05T23:18:46Z] P3/A-309-CRBP-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,504 rows / 5,481 parsed, with current valid JSON rate `0.995821`.

## [2026-07-06T14:52:19Z] P3/A-309-CRBP-ALIAS-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/4746150801536188416` completed as `JOB_STATE_SUCCEEDED` at `2026-07-06T02:40:56Z`.
- Downloaded five expected artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-crbp-alias-v1/` into ignored local run storage for QA.
- Raw QA: `requests.jsonl` 12,800 rows; `outputs.jsonl` 12,800 rows / 12,758 parsed; valid JSON rate `0.996719`; `sim.jsonl` 128 rows.
- Collector QA: `scripts/p3_collect_calibration.py` completed on local `runs/p3`; CRBP alias appears in RQ1/RQ2 summaries (`Spearman 0.154`, sign agreement `0.693`, mean entropy `1.072`) and G3 kill condition still does not fire on available P3 artifacts.
- Budget ledger updated with 5.95 wall hours at `$0.30/hr` (`$1.79`), bringing cumulative estimated spend to `$19.45`.

## [2026-07-06T14:53:53Z] P3/A-310-BLNK-NAMED-LAUNCH
- Launched BLNK named calibration shard on Vertex: `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` (`agorasim-p3-blnk-named-v1`), initial state `JOB_STATE_PENDING`.
- Run ID `calib-2019-g1-blnk-named-v1`; GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-blnk-named-v1`.
- Generated and retained Vertex job spec at `docs/vertex_job_specs/agorasim-p3-blnk-named-v1.json`.
- State now tracks BLNK named as the only active job, with budget estimate set to `$21.40` pending actual completion cost.

## [2026-07-06T15:03:05Z] P3/A-310-BLNK-NAMED-STARTUP
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` is `JOB_STATE_RUNNING`; worker start time `2026-07-06T14:57:36Z`.
- `requests.jsonl` is present in GCS and `outputs.jsonl` has started: 128 rows / 127 parsed, valid JSON rate `0.992188`.

## [2026-07-06T15:14:31Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 640 rows / 639 parsed, with current valid JSON rate `0.998438`.

## [2026-07-06T15:25:30Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,152 rows / 1,151 parsed, with current valid JSON rate `0.999132`.

## [2026-07-06T15:36:39Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,536 rows / 1,533 parsed, with current valid JSON rate `0.998047`.

## [2026-07-06T15:47:42Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,792 rows / 1,787 parsed, with current valid JSON rate `0.997210`.

## [2026-07-06T15:58:42Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,176 rows / 2,171 parsed, with current valid JSON rate `0.997702`.

## [2026-07-06T16:09:48Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,560 rows / 2,554 parsed, with current valid JSON rate `0.997656`.

## [2026-07-06T16:21:51Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,944 rows / 2,938 parsed, with current valid JSON rate `0.997962`.

## [2026-07-06T16:32:53Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,328 rows / 3,316 parsed, with current valid JSON rate `0.996394`.

## [2026-07-06T16:43:51Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,712 rows / 3,698 parsed, with current valid JSON rate `0.996228`.

## [2026-07-06T16:54:50Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,968 rows / 3,954 parsed, with current valid JSON rate `0.996472`.

## [2026-07-06T17:05:47Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,352 rows / 4,334 parsed, with current valid JSON rate `0.995864`.

## [2026-07-06T17:16:48Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,736 rows / 4,716 parsed, with current valid JSON rate `0.995777`.

## [2026-07-06T17:27:57Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,120 rows / 5,099 parsed, with current valid JSON rate `0.995898`.

## [2026-07-06T17:38:58Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,504 rows / 5,483 parsed, with current valid JSON rate `0.996185`.

## [2026-07-06T17:50:01Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,888 rows / 5,866 parsed, with current valid JSON rate `0.996264`.

## [2026-07-06T18:00:59Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,272 rows / 6,249 parsed, with current valid JSON rate `0.996333`.

## [2026-07-06T18:11:58Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,912 rows / 6,886 parsed, with current valid JSON rate `0.996238`.

## [2026-07-06T18:23:02Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,552 rows / 7,524 parsed, with current valid JSON rate `0.996292`.

## [2026-07-06T18:34:07Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,936 rows / 7,907 parsed, with current valid JSON rate `0.996346`.

## [2026-07-06T18:45:06Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,320 rows / 8,291 parsed, with current valid JSON rate `0.996514`.

## [2026-07-06T18:56:05Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,704 rows / 8,675 parsed, with current valid JSON rate `0.996668`.

## [2026-07-06T19:07:03Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,088 rows / 9,058 parsed, with current valid JSON rate `0.996699`.

## [2026-07-06T19:18:02Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,472 rows / 9,441 parsed, with current valid JSON rate `0.996727`.

## [2026-07-06T19:29:01Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,856 rows / 9,825 parsed, with current valid JSON rate `0.996855`.

## [2026-07-06T19:40:02Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,240 rows / 10,209 parsed, with current valid JSON rate `0.996973`.

## [2026-07-06T19:51:05Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,624 rows / 10,593 parsed, with current valid JSON rate `0.997082`.

## [2026-07-06T20:02:05Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,008 rows / 10,976 parsed, with current valid JSON rate `0.997093`.

## [2026-07-06T20:13:10Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,392 rows / 11,359 parsed, with current valid JSON rate `0.997103`.

## [2026-07-06T20:24:12Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,776 rows / 11,742 parsed, with current valid JSON rate `0.997113`.

## [2026-07-06T20:35:16Z] P3/A-310-BLNK-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,160 rows / 12,126 parsed, with current valid JSON rate `0.997204`.

## [2026-07-06T21:00:04Z] P3/A-310-BLNK-NAMED-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/2104974338036858880` completed as `JOB_STATE_SUCCEEDED` at `2026-07-06T20:53:56Z`.
- Downloaded five expected artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-blnk-named-v1/` into ignored local run storage for QA.
- Raw QA: `requests.jsonl` 12,800 rows; `outputs.jsonl` 12,800 rows / 12,766 parsed; valid JSON rate `0.997344`; `sim.jsonl` 128 rows.
- Collector QA: `scripts/p3_collect_calibration.py` completed on local `runs/p3`; BLNK named appears in RQ1/RQ2 summaries (`Spearman 0.153`, sign agreement `0.535`, mean entropy `1.076`) and G3 kill condition still does not fire on available P3 artifacts.
- Budget ledger updated with 6.00 wall hours at `$0.30/hr` (`$1.80`), bringing cumulative estimated spend to `$21.25`.

## [2026-07-06T21:01:26Z] P3/A-311-BLNK-ALIAS-LAUNCH
- Launched BLNK alias calibration shard on Vertex: `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` (`agorasim-p3-blnk-alias-v1`), initial state `JOB_STATE_PENDING`.
- Run ID `calib-2019-g1-blnk-alias-v1`; GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-blnk-alias-v1`.
- Generated and retained Vertex job spec at `docs/vertex_job_specs/agorasim-p3-blnk-alias-v1.json`.
- State now tracks BLNK alias as the only active job, with budget estimate set to `$23.20` pending actual completion cost.

## [2026-07-06T21:10:16Z] P3/A-311-BLNK-ALIAS-STARTUP
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` is `JOB_STATE_RUNNING`; worker start time `2026-07-06T21:04:39Z`.
- `requests.jsonl` is present in GCS and `outputs.jsonl` has started: 128 rows / 128 parsed, valid JSON rate `1.000000`.

## [2026-07-06T21:26:59Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 768 rows / 768 parsed, with current valid JSON rate `1.000000`.

## [2026-07-06T21:37:58Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,152 rows / 1,152 parsed, with current valid JSON rate `1.000000`.

## [2026-07-06T21:48:55Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,536 rows / 1,533 parsed, with current valid JSON rate `0.998047`.

## [2026-07-06T21:59:53Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,792 rows / 1,787 parsed, with current valid JSON rate `0.997210`.

## [2026-07-06T22:11:01Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,176 rows / 2,171 parsed, with current valid JSON rate `0.997702`.

## [2026-07-06T22:22:03Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,560 rows / 2,554 parsed, with current valid JSON rate `0.997656`.

## [2026-07-06T22:33:05Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,816 rows / 2,810 parsed, with current valid JSON rate `0.997869`.

## [2026-07-06T22:44:05Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,200 rows / 3,193 parsed, with current valid JSON rate `0.997812`.

## [2026-07-06T22:55:06Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,584 rows / 3,570 parsed, with current valid JSON rate `0.996094`.

## [2026-07-06T23:06:11Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,840 rows / 3,826 parsed, with current valid JSON rate `0.996354`.

## [2026-07-06T23:17:15Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,224 rows / 4,208 parsed, with current valid JSON rate `0.996212`.

## [2026-07-06T23:28:19Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,608 rows / 4,588 parsed, with current valid JSON rate `0.995660`.

## [2026-07-06T23:39:22Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,992 rows / 4,971 parsed, with current valid JSON rate `0.995793`.

## [2026-07-06T23:50:22Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,376 rows / 5,355 parsed, with current valid JSON rate `0.996094`.

## [2026-07-07T00:01:25Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,760 rows / 5,738 parsed, with current valid JSON rate `0.996181`.

## [2026-07-07T00:12:39Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,144 rows / 6,121 parsed, with current valid JSON rate `0.996257`.

## [2026-07-07T00:23:43Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,656 rows / 6,629 parsed, with current valid JSON rate `0.995944`.

## [2026-07-07T00:34:48Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,296 rows / 7,269 parsed, with current valid JSON rate `0.996299`.

## [2026-07-07T00:45:55Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,680 rows / 7,652 parsed, with current valid JSON rate `0.996354`.

## [2026-07-07T00:57:01Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,064 rows / 8,035 parsed, with current valid JSON rate `0.996404`.

## [2026-07-07T01:08:09Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,448 rows / 8,419 parsed, with current valid JSON rate `0.996567`.

## [2026-07-07T01:19:20Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,832 rows / 8,802 parsed, with current valid JSON rate `0.996603`.

## [2026-07-07T01:30:26Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,216 rows / 9,185 parsed, with current valid JSON rate `0.996636`.

## [2026-07-07T01:41:34Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,600 rows / 9,569 parsed, with current valid JSON rate `0.996771`.

## [2026-07-07T01:53:05Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,984 rows / 9,953 parsed, with current valid JSON rate `0.996895`.

## [2026-07-07T02:04:21Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,240 rows / 10,209 parsed, with current valid JSON rate `0.996973`.

## [2026-07-07T02:15:56Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,624 rows / 10,593 parsed, with current valid JSON rate `0.997082`.

## [2026-07-07T02:27:19Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,008 rows / 10,976 parsed, with current valid JSON rate `0.997093`.

## [2026-07-07T02:38:29Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,392 rows / 11,359 parsed, with current valid JSON rate `0.997103`.

## [2026-07-07T02:49:41Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,776 rows / 11,742 parsed, with current valid JSON rate `0.997113`.

## [2026-07-07T03:00:58Z] P3/A-311-BLNK-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,160 rows / 12,126 parsed, with current valid JSON rate `0.997204`.

## [2026-07-07T03:24:18Z] P3/A-311-BLNK-ALIAS-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/2952389939796377600` completed as `JOB_STATE_SUCCEEDED` at `2026-07-07T03:20:00Z`.
- Downloaded five expected artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-blnk-alias-v1/` into ignored local run storage for QA.
- Raw QA: `requests.jsonl` 12,800 rows; `outputs.jsonl` 12,800 rows / 12,766 parsed; valid JSON rate `0.997344`; `sim.jsonl` 128 rows.
- Collector QA: `scripts/p3_collect_calibration.py` completed on local `runs/p3`; BLNK alias appears in RQ1/RQ2 summaries (`Spearman 0.160`, sign agreement `0.535`, mean entropy `1.085`) and G3 kill condition still does not fire on available P3 artifacts.
- Budget ledger updated with 6.31 wall hours at `$0.30/hr` (`$1.89`), bringing cumulative estimated spend to `$23.14`.

## [2026-07-07T03:25:50Z] P3/A-312-PLUG-NAMED-LAUNCH
- Launched PLUG named calibration shard on Vertex: `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` (`agorasim-p3-plug-named-v1`), initial state `JOB_STATE_PENDING`.
- Run ID `calib-2019-g1-plug-named-v1`; GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-plug-named-v1`.
- Generated and retained Vertex job spec at `docs/vertex_job_specs/agorasim-p3-plug-named-v1.json`.
- State now tracks PLUG named as the only active job, with budget estimate set to `$25.09` pending actual completion cost.

## [2026-07-07T03:35:30Z] P3/A-312-PLUG-NAMED-STARTUP
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` is `JOB_STATE_RUNNING`; worker start time `2026-07-07T03:29:21Z`.
- `requests.jsonl` is present in GCS and `outputs.jsonl` has started: 128 rows / 128 parsed, valid JSON rate `1.000000`.

## [2026-07-07T03:57:54Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,024 rows / 1,021 parsed, with current valid JSON rate `0.997070`.

## [2026-07-07T04:19:18Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,792 rows / 1,784 parsed, with current valid JSON rate `0.995536`.

## [2026-07-07T04:30:31Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,176 rows / 2,166 parsed, with current valid JSON rate `0.995404`.

## [2026-07-07T04:43:19Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,560 rows / 2,550 parsed, with current valid JSON rate `0.996094`.

## [2026-07-07T04:54:12Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,944 rows / 2,933 parsed, with current valid JSON rate `0.996264`.

## [2026-07-07T05:04:59Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,328 rows / 3,314 parsed, with current valid JSON rate `0.995793`.

## [2026-07-07T05:15:56Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,712 rows / 3,697 parsed, with current valid JSON rate `0.995959`.

## [2026-07-07T05:26:42Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,968 rows / 3,953 parsed, with current valid JSON rate `0.996220`.

## [2026-07-07T05:37:31Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,224 rows / 4,208 parsed, with current valid JSON rate `0.996212`.

## [2026-07-07T05:48:26Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,608 rows / 4,588 parsed, with current valid JSON rate `0.995660`.

## [2026-07-07T05:59:20Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,992 rows / 4,971 parsed, with current valid JSON rate `0.995793`.

## [2026-07-07T06:10:08Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,376 rows / 5,355 parsed, with current valid JSON rate `0.996094`.

## [2026-07-07T06:20:57Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,760 rows / 5,736 parsed, with current valid JSON rate `0.995833`.

## [2026-07-07T06:31:47Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,016 rows / 5,991 parsed, with current valid JSON rate `0.995844`.

## [2026-07-07T06:42:35Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,400 rows / 6,375 parsed, with current valid JSON rate `0.996094`.

## [2026-07-07T06:53:23Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,040 rows / 7,013 parsed, with current valid JSON rate `0.996165`.

## [2026-07-07T07:04:09Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,552 rows / 7,525 parsed, with current valid JSON rate `0.996425`.

## [2026-07-07T07:14:58Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,936 rows / 7,909 parsed, with current valid JSON rate `0.996598`.

## [2026-07-07T07:25:53Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,320 rows / 8,293 parsed, with current valid JSON rate `0.996755`.

## [2026-07-07T07:36:58Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,704 rows / 8,677 parsed, with current valid JSON rate `0.996898`.

## [2026-07-07T07:47:52Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,088 rows / 9,060 parsed, with current valid JSON rate `0.996919`.

## [2026-07-07T07:58:46Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,472 rows / 9,443 parsed, with current valid JSON rate `0.996938`.

## [2026-07-07T08:10:05Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,856 rows / 9,826 parsed, with current valid JSON rate `0.996956`.

## [2026-07-07T08:21:26Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,240 rows / 10,209 parsed, with current valid JSON rate `0.996973`.

## [2026-07-07T08:32:38Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,496 rows / 10,462 parsed, with current valid JSON rate `0.996761`.

## [2026-07-07T08:43:51Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,880 rows / 10,844 parsed, with current valid JSON rate `0.996691`.

## [2026-07-07T08:55:02Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,264 rows / 11,226 parsed, with current valid JSON rate `0.996626`.

## [2026-07-07T09:06:24Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,648 rows / 11,610 parsed, with current valid JSON rate `0.996738`.

## [2026-07-07T09:17:32Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,032 rows / 11,992 parsed, with current valid JSON rate `0.996676`.

## [2026-07-07T09:28:47Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,416 rows / 12,374 parsed, with current valid JSON rate `0.996617`.

## [2026-07-07T09:34:53Z] P3/A-312-PLUG-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,672 rows / 12,629 parsed, with current valid JSON rate `0.996607`.

## [2026-07-07T09:39:51Z] P3/A-312-PLUG-NAMED-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/6427692757766111232` completed as `JOB_STATE_SUCCEEDED` at `2026-07-07T09:38:17Z`.
- Downloaded five expected artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-plug-named-v1/` into ignored local run storage for QA.
- Raw QA: `requests.jsonl` 12,800 rows; `outputs.jsonl` 12,800 rows / 12,756 parsed; valid JSON rate `0.996562`; `sim.jsonl` 128 rows.
- Worker summary: 128 days, 100 agents, models `Qwen/Qwen2.5-1.5B-Instruct` and `microsoft/Phi-3.5-mini-instruct`, temperatures `0.7` and `1.0`, elapsed worker seconds `22118.020`.
- Collector QA: `scripts/p3_collect_calibration.py` completed on local `runs/p3`; PLUG named appears in RQ1/RQ2 summaries (`Spearman -0.020`, sign agreement `0.638`, mean entropy `0.975`) and G3 kill condition still does not fire on available P3 artifacts.
- Budget ledger updated with 6.21 wall hours at `$0.30/hr` (`$1.86`), bringing cumulative estimated spend to `$25.00`.

## [2026-07-07T09:42:13Z] P3/A-313-PLUG-ALIAS-LAUNCH
- Launched PLUG alias calibration shard on Vertex: `projects/987318647780/locations/us-central1/customJobs/876531228008775680` (`agorasim-p3-plug-alias-v1`), initial state `JOB_STATE_PENDING`.
- Run ID `calib-2019-g1-plug-alias-v1`; GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-plug-alias-v1`.
- Generated and retained Vertex job spec at `docs/vertex_job_specs/agorasim-p3-plug-alias-v1.json`; spec passes model IDs and `--gcs-model-root` to the Vertex worker and contains no environment secrets.
- State now tracks PLUG alias as the only active job, with budget estimate set to `$26.95` pending actual completion cost.

## [2026-07-07T09:46:26Z] P3/A-313-PLUG-ALIAS-STARTUP
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` is `JOB_STATE_RUNNING`; worker start time `2026-07-07T09:45:24Z`.
- `requests.jsonl` is present in GCS; `outputs.jsonl` had not been emitted yet at this startup check.

## [2026-07-07T09:52:34Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 256 rows / 256 parsed, with current valid JSON rate `1.000000`.

## [2026-07-07T10:03:27Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 768 rows / 767 parsed, with current valid JSON rate `0.998698`.

## [2026-07-07T10:14:21Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,152 rows / 1,150 parsed, with current valid JSON rate `0.998264`.

## [2026-07-07T10:25:13Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,536 rows / 1,533 parsed, with current valid JSON rate `0.998047`.

## [2026-07-07T10:36:06Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,048 rows / 2,042 parsed, with current valid JSON rate `0.997070`.

## [2026-07-07T10:46:55Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,432 rows / 2,425 parsed, with current valid JSON rate `0.997122`.

## [2026-07-07T10:57:45Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,816 rows / 2,808 parsed, with current valid JSON rate `0.997159`.

## [2026-07-07T11:08:36Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,200 rows / 3,189 parsed, with current valid JSON rate `0.996562`.

## [2026-07-07T11:19:29Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,456 rows / 3,441 parsed, with current valid JSON rate `0.995660`.

## [2026-07-07T11:30:22Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,840 rows / 3,825 parsed, with current valid JSON rate `0.996094`.

## [2026-07-07T11:41:15Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,224 rows / 4,207 parsed, with current valid JSON rate `0.995975`.

## [2026-07-07T11:52:08Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,480 rows / 4,458 parsed, with current valid JSON rate `0.995089`.

## [2026-07-07T12:03:02Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,992 rows / 4,970 parsed, with current valid JSON rate `0.995593`.

## [2026-07-07T12:13:54Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,376 rows / 5,354 parsed, with current valid JSON rate `0.995908`.

## [2026-07-07T12:24:44Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,760 rows / 5,735 parsed, with current valid JSON rate `0.995660`.

## [2026-07-07T12:35:40Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,144 rows / 6,117 parsed, with current valid JSON rate `0.995605`.

## [2026-07-07T12:46:29Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,656 rows / 6,627 parsed, with current valid JSON rate `0.995643`.

## [2026-07-07T12:57:19Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,296 rows / 7,267 parsed, with current valid JSON rate `0.996025`.

## [2026-07-07T13:08:09Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,680 rows / 7,651 parsed, with current valid JSON rate `0.996224`.

## [2026-07-07T13:19:05Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,064 rows / 8,035 parsed, with current valid JSON rate `0.996404`.

## [2026-07-07T13:29:56Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,448 rows / 8,419 parsed, with current valid JSON rate `0.996567`.

## [2026-07-07T13:40:52Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,832 rows / 8,803 parsed, with current valid JSON rate `0.996716`.

## [2026-07-07T13:51:48Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,216 rows / 9,186 parsed, with current valid JSON rate `0.996745`.

## [2026-07-07T14:02:41Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,472 rows / 9,442 parsed, with current valid JSON rate `0.996833`.

## [2026-07-07T14:13:44Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,856 rows / 9,825 parsed, with current valid JSON rate `0.996855`.

## [2026-07-07T14:24:42Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,240 rows / 10,207 parsed, with current valid JSON rate `0.996777`.

## [2026-07-07T14:35:45Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,624 rows / 10,587 parsed, with current valid JSON rate `0.996517`.

## [2026-07-07T14:46:43Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,008 rows / 10,969 parsed, with current valid JSON rate `0.996457`.

## [2026-07-07T14:57:42Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,392 rows / 11,352 parsed, with current valid JSON rate `0.996489`.

## [2026-07-07T15:08:35Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,776 rows / 11,734 parsed, with current valid JSON rate `0.996433`.

## [2026-07-07T15:19:32Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,032 rows / 11,987 parsed, with current valid JSON rate `0.996260`.

## [2026-07-07T15:30:28Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,416 rows / 12,369 parsed, with current valid JSON rate `0.996215`.

## [2026-07-07T15:36:30Z] P3/A-313-PLUG-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,672 rows / 12,624 parsed, with current valid JSON rate `0.996212`.

## [2026-07-07T15:41:33Z] P3/A-313-PLUG-ALIAS-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/876531228008775680` completed as `JOB_STATE_SUCCEEDED` at `2026-07-07T15:39:16Z`.
- Downloaded five expected artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-plug-alias-v1/` into ignored local run storage for QA.
- Raw QA: `requests.jsonl` 12,800 rows; `outputs.jsonl` 12,800 rows / 12,751 parsed; valid JSON rate `0.996172`; `sim.jsonl` 128 rows.
- Worker summary: 128 days, 100 agents, models `Qwen/Qwen2.5-1.5B-Instruct` and `microsoft/Phi-3.5-mini-instruct`, temperatures `0.7` and `1.0`, elapsed worker seconds `21223.676`.
- Collector QA: `scripts/p3_collect_calibration.py` completed on local `runs/p3`; PLUG alias appears in RQ1/RQ2 summaries (`Spearman 0.050`, sign agreement `0.638`, mean entropy `0.995`) and G3 kill condition still does not fire on available P3 artifacts.
- Budget ledger updated with 5.95 wall hours at `$0.30/hr` (`$1.79`), bringing cumulative estimated spend to `$26.79`.

## [2026-07-07T15:44:14Z] P3/A-314-XXII-NAMED-LAUNCH
- Launched XXII named calibration shard on Vertex: `projects/987318647780/locations/us-central1/customJobs/419028837737693184` (`agorasim-p3-xxii-named-v1`), initial state `JOB_STATE_PENDING`.
- Run ID `calib-2019-g1-xxii-named-v1`; GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-xxii-named-v1`.
- Generated and retained Vertex job spec at `docs/vertex_job_specs/agorasim-p3-xxii-named-v1.json`; spec passes model IDs and `--gcs-model-root` to the Vertex worker and contains no environment secrets.
- State now tracks XXII named as the only active job, with budget estimate set to `$28.74` pending actual completion cost.

## [2026-07-07T15:48:35Z] P3/A-314-XXII-NAMED-STARTUP
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` is `JOB_STATE_RUNNING`; worker start time `2026-07-07T15:47:09Z`.
- `requests.jsonl` is present in GCS; `outputs.jsonl` had not been emitted yet at this startup check.

## [2026-07-07T15:54:48Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 256 rows / 256 parsed, with current valid JSON rate `1.000000`.

## [2026-07-07T16:05:44Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 768 rows / 767 parsed, with current valid JSON rate `0.998698`.

## [2026-07-07T16:16:45Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,152 rows / 1,151 parsed, with current valid JSON rate `0.999132`.

## [2026-07-07T16:27:44Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,536 rows / 1,532 parsed, with current valid JSON rate `0.997396`.

## [2026-07-07T16:38:39Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 1,920 rows / 1,913 parsed, with current valid JSON rate `0.996354`.

## [2026-07-07T16:49:38Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,304 rows / 2,295 parsed, with current valid JSON rate `0.996094`.

## [2026-07-07T17:00:48Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 2,688 rows / 2,679 parsed, with current valid JSON rate `0.996652`.

## [2026-07-07T17:11:42Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,072 rows / 3,061 parsed, with current valid JSON rate `0.996419`.

## [2026-07-07T17:22:36Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,456 rows / 3,443 parsed, with current valid JSON rate `0.996238`.

## [2026-07-07T17:33:29Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 3,840 rows / 3,826 parsed, with current valid JSON rate `0.996354`.

## [2026-07-07T17:44:23Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,224 rows / 4,207 parsed, with current valid JSON rate `0.995975`.

## [2026-07-07T17:55:20Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,608 rows / 4,590 parsed, with current valid JSON rate `0.996094`.

## [2026-07-07T18:06:12Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 4,992 rows / 4,971 parsed, with current valid JSON rate `0.995793`.

## [2026-07-07T18:17:06Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,248 rows / 5,222 parsed, with current valid JSON rate `0.995046`.

## [2026-07-07T18:28:03Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 5,632 rows / 5,601 parsed, with current valid JSON rate `0.994496`.

## [2026-07-07T18:38:59Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,016 rows / 5,980 parsed, with current valid JSON rate `0.994016`.

## [2026-07-07T18:49:56Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 6,400 rows / 6,363 parsed, with current valid JSON rate `0.994219`.

## [2026-07-07T19:00:55Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,168 rows / 7,130 parsed, with current valid JSON rate `0.994699`.

## [2026-07-07T19:12:03Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,552 rows / 7,514 parsed, with current valid JSON rate `0.994968`.

## [2026-07-07T19:22:57Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 7,936 rows / 7,897 parsed, with current valid JSON rate `0.995086`.

## [2026-07-07T19:34:04Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,320 rows / 8,280 parsed, with current valid JSON rate `0.995192`.

## [2026-07-07T19:44:59Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 8,704 rows / 8,664 parsed, with current valid JSON rate `0.995404`.

## [2026-07-07T19:56:03Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,088 rows / 9,048 parsed, with current valid JSON rate `0.995599`.

## [2026-07-07T20:06:58Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,472 rows / 9,431 parsed, with current valid JSON rate `0.995671`.

## [2026-07-07T20:18:00Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 9,856 rows / 9,815 parsed, with current valid JSON rate `0.995840`.

## [2026-07-07T20:28:55Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,112 rows / 10,071 parsed, with current valid JSON rate `0.995945`.

## [2026-07-07T20:39:48Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,496 rows / 10,455 parsed, with current valid JSON rate `0.996094`.

## [2026-07-07T20:50:48Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 10,880 rows / 10,839 parsed, with current valid JSON rate `0.996232`.

## [2026-07-07T21:01:45Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,264 rows / 11,223 parsed, with current valid JSON rate `0.996360`.

## [2026-07-07T21:12:41Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 11,648 rows / 11,607 parsed, with current valid JSON rate `0.996480`.

## [2026-07-07T21:23:42Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,032 rows / 11,991 parsed, with current valid JSON rate `0.996592`.

## [2026-07-07T21:29:40Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,160 rows / 12,119 parsed, with current valid JSON rate `0.996628`.

## [2026-07-07T21:35:34Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,416 rows / 12,374 parsed, with current valid JSON rate `0.996617`.

## [2026-07-07T21:41:28Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,544 rows / 12,501 parsed, with current valid JSON rate `0.996572`.

## [2026-07-07T21:46:25Z] P3/A-314-XXII-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to 12,800 rows / 12,757 parsed, with current valid JSON rate `0.996641`.

## [2026-07-07T21:50:19Z] P3/A-314-XXII-NAMED-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/419028837737693184` completed as `JOB_STATE_SUCCEEDED` at `2026-07-07T21:46:34Z`.
- Downloaded five expected artifacts from `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-xxii-named-v1/` into ignored local run storage for QA.
- Raw QA: `requests.jsonl` 12,800 rows; `outputs.jsonl` 12,800 rows / 12,757 parsed; valid JSON rate `0.996641`; `sim.jsonl` 128 rows.
- Worker summary: 128 days, 100 agents, models `Qwen/Qwen2.5-1.5B-Instruct` and `microsoft/Phi-3.5-mini-instruct`, temperatures `0.7` and `1.0`, elapsed worker seconds `21554.301`.
- Collector QA: `scripts/p3_collect_calibration.py` completed on local `runs/p3`; XXII named appears in RQ1/RQ2 summaries (`Spearman -0.059`, sign agreement `0.346`, mean entropy `1.048`) and G3 kill condition still does not fire on available P3 artifacts.
- Budget ledger updated with 6.04 wall hours at `$0.30/hr` (`$1.81`), bringing cumulative estimated spend to `$28.60`.

## [2026-07-07T21:52:38Z] P3/A-315-XXII-ALIAS-LAUNCH
- Launched XXII alias calibration shard on Vertex: `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` (`agorasim-p3-xxii-alias-v1`), initial state `JOB_STATE_PENDING`.
- Run ID `calib-2019-g1-xxii-alias-v1`; GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-xxii-alias-v1`.
- Generated and retained Vertex job spec at `docs/vertex_job_specs/agorasim-p3-xxii-alias-v1.json`; spec passes model IDs and `--gcs-model-root` to the Vertex worker and contains no environment secrets.
- State now tracks XXII alias as the only active job, with budget estimate set to `$30.55` pending actual completion cost.

## [2026-07-07T21:58:52Z] P3/A-315-XXII-ALIAS-STARTUP
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` is `JOB_STATE_RUNNING`; Vertex worker start time `2026-07-07T21:56:02Z`.
- `requests.jsonl` is present in GCS with `12,800` planned requests; `outputs.jsonl` had not been emitted yet at this startup check.

## [2026-07-07T22:05:01Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `256` rows / `256` parsed, with current valid JSON rate `1.000000`.

## [2026-07-07T22:15:48Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `640` rows / `640` parsed, with current valid JSON rate `1.000000`.

## [2026-07-07T22:31:36Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `1,280` rows / `1,278` parsed, with current valid JSON rate `0.998438`.

## [2026-07-07T22:52:21Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `1,920` rows / `1,916` parsed, with current valid JSON rate `0.997917`.

## [2026-07-07T23:23:06Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `2,944` rows / `2,937` parsed, with current valid JSON rate `0.997622`.

## [2026-07-07T23:54:17Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- Verified GCS run directory after one transient copy miss; `outputs.jsonl` is present and advanced to `3,968` rows / `3,958` parsed, with current valid JSON rate `0.997480`.

## [2026-07-08T00:25:05Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `4,992` rows / `4,975` parsed, with current valid JSON rate `0.996595`.

## [2026-07-08T00:55:57Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `5,888` rows / `5,859` parsed, with current valid JSON rate `0.995075`; continue monitoring parse-rate trend.

## [2026-07-08T01:26:46Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `7,296` rows / `7,262` parsed, with current valid JSON rate `0.995340`.

## [2026-07-08T01:57:41Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `8,320` rows / `8,283` parsed, with current valid JSON rate `0.995553`.

## [2026-07-08T02:28:30Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `9,344` rows / `9,307` parsed, with current valid JSON rate `0.996040`.

## [2026-07-08T02:59:21Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `10,368` rows / `10,330` parsed, with current valid JSON rate `0.996335`.

## [2026-07-08T03:20:18Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `11,008` rows / `10,970` parsed, with current valid JSON rate `0.996548`.

## [2026-07-08T03:36:08Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `11,520` rows / `11,482` parsed, with current valid JSON rate `0.996701`.

## [2026-07-08T03:46:57Z] P3/A-315-XXII-ALIAS-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `11,904` rows / `11,866` parsed, with current valid JSON rate `0.996808`.

## [2026-07-08T04:16:14Z] P3/A-315-XXII-ALIAS-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/3766566755292413952` completed successfully at `2026-07-08T04:14:23Z`; final `outputs.jsonl` has `12,800` rows / `12,760` parsed, valid JSON rate `0.996875`, and `sim.jsonl` has `128` rows.
- Downloaded completed run artifacts from GCS to ignored local path `runs/p3/calib-2019-g1-xxii-alias-v1/`, including `sim.jsonl` and `worker_summary.json`.
- Worker summary: 128 days, 100 agents, models `Qwen/Qwen2.5-1.5B-Instruct` and `microsoft/Phi-3.5-mini-instruct`, temperatures `0.7` and `1.0`, elapsed worker seconds `22703.532`.
- Collector QA: `scripts/p3_collect_calibration.py` completed on local `runs/p3`; XXII alias appears in RQ1/RQ2 summaries (`Spearman -0.103`, sign agreement `0.346`, mean entropy `1.037`) and G3 kill condition still does not fire on available P3 artifacts.
- Budget ledger updated with 6.36 wall hours at `$0.30/hr` (`$1.91`), bringing cumulative estimated spend to `$30.51`.

## [2026-07-08T04:19:53Z] P3/A-316-LEVI-NAMED-LAUNCH
- Launched LEVI named calibration shard on Vertex: `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` (`agorasim-p3-levi-named-v1`), initial state `JOB_STATE_PENDING`.
- Run ID `calib-2019-g1-levi-named-v1`; GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-levi-named-v1`.
- Generated and retained Vertex job spec at `docs/vertex_job_specs/agorasim-p3-levi-named-v1.json`; spec passes model IDs and `--gcs-model-root` to the Vertex worker and contains no environment secrets.
- State now tracks LEVI named as the only active job, with budget estimate set to `$32.46` pending actual completion cost.

## [2026-07-08T04:24:00Z] P3/A-316-LEVI-NAMED-STARTUP
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` is `JOB_STATE_RUNNING`; Vertex worker start time `2026-07-08T04:23:00Z`.
- `requests.jsonl` is present in GCS with `12,800` planned requests; `outputs.jsonl` had not been emitted yet at this startup check.

## [2026-07-08T04:30:04Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `128` rows / `128` parsed, with current valid JSON rate `1.000000`.

## [2026-07-08T04:45:55Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `768` rows / `768` parsed, with current valid JSON rate `1.000000`.

## [2026-07-08T05:16:57Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `1,664` rows / `1,658` parsed, with current valid JSON rate `0.996394`.

## [2026-07-08T05:47:49Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `2,560` rows / `2,552` parsed, with current valid JSON rate `0.996875`.

## [2026-07-08T06:18:41Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `3,456` rows / `3,442` parsed, with current valid JSON rate `0.995949`.

## [2026-07-08T06:49:36Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `4,480` rows / `4,461` parsed, with current valid JSON rate `0.995759`.

## [2026-07-08T07:20:34Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `5,504` rows / `5,481` parsed, with current valid JSON rate `0.995821`.

## [2026-07-08T07:51:31Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `6,656` rows / `6,630` parsed, with current valid JSON rate `0.996094`.

## [2026-07-08T08:22:36Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `7,808` rows / `7,777` parsed, with current valid JSON rate `0.996030`.

## [2026-07-08T08:53:30Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `8,832` rows / `8,799` parsed, with current valid JSON rate `0.996264`.

## [2026-07-08T09:24:27Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `9,728` rows / `9,692` parsed, with current valid JSON rate `0.996299`.

## [2026-07-08T09:55:43Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `10,752` rows / `10,714` parsed, with current valid JSON rate `0.996466`.

## [2026-07-08T10:16:52Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `11,392` rows / `11,353` parsed, with current valid JSON rate `0.996577`.

## [2026-07-08T10:32:51Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `11,904` rows / `11,864` parsed, with current valid JSON rate `0.996640`.

## [2026-07-08T10:43:54Z] P3/A-316-LEVI-NAMED-POLL
- Job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` remains `JOB_STATE_RUNNING`.
- `outputs.jsonl` advanced to `12,288` rows / `12,247` parsed, with current valid JSON rate `0.996663`.

## [2026-07-08T10:45:39Z] P3/PARALLEL-SHARD-LAUNCH
- Submitted the remaining P3 shards as separate Vertex jobs so Vertex can run them concurrently if T4 quota/capacity allows; all initial states are `JOB_STATE_PENDING`.
- A-317 LEVI alias: `projects/987318647780/locations/us-central1/customJobs/3715707745438007296`, run ID `calib-2019-g1-levi-alias-v1`, GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-levi-alias-v1`.
- A-318 VKTX named: `projects/987318647780/locations/us-central1/customJobs/2035865084428812288`, run ID `calib-2019-g1-vktx-named-v1`, GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-vktx-named-v1`.
- A-319 VKTX alias: `projects/987318647780/locations/us-central1/customJobs/4859622050790113280`, run ID `calib-2019-g1-vktx-alias-v1`, GCS output `gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs/p3/calib-2019-g1-vktx-alias-v1`.
- Generated and retained Vertex job specs at `docs/vertex_job_specs/agorasim-p3-levi-alias-v1.json`, `docs/vertex_job_specs/agorasim-p3-vktx-named-v1.json`, and `docs/vertex_job_specs/agorasim-p3-vktx-alias-v1.json`; specs pass model IDs and `--gcs-model-root` to Vertex workers and contain no environment secrets.
- State now tracks four active P3 jobs: LEVI named running plus LEVI alias, VKTX named, and VKTX alias pending; budget reservation updated to `$38.31` pending actual completion costs.

## [2026-07-08T10:47:12Z] P3/PARALLEL-STARTUP-POLL
- Vertex concurrency confirmed: A-318 VKTX named is `JOB_STATE_RUNNING` with worker start `2026-07-08T10:47:44Z`, and A-319 VKTX alias is `JOB_STATE_RUNNING` with worker start `2026-07-08T10:47:58Z`; both have `requests.jsonl` present with `12,800` planned requests and no `outputs.jsonl` yet.
- A-316 LEVI named remains `JOB_STATE_RUNNING`; `outputs.jsonl` advanced to `12,416` rows / `12,375` parsed, with current valid JSON rate `0.996698`.
- A-317 LEVI alias remains `JOB_STATE_PENDING`; no request/output artifacts emitted yet.

## [2026-07-08T10:56:50Z] P3/PARALLEL-POLL
- All four active P3 jobs are now `JOB_STATE_RUNNING`; A-317 LEVI alias started at `2026-07-08T10:47:51Z`.
- A-316 LEVI named advanced to `12,672` rows / `12,629` parsed, with current valid JSON rate `0.996607`.
- A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias each advanced to `256` rows / `256` parsed, with current valid JSON rate `1.000000`.

## [2026-07-08T11:04:23Z] P3/A-316-LEVI-NAMED-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/3346289430691315712` completed successfully at `2026-07-08T10:58:34Z`; final `outputs.jsonl` has `12,800` rows / `12,757` parsed, valid JSON rate `0.996641`, and `sim.jsonl` has `128` rows.
- Downloaded completed run artifacts from GCS to ignored local path `runs/p3/calib-2019-g1-levi-named-v1/`, including `sim.jsonl` and `worker_summary.json`.
- Worker summary: 128 days, 100 agents, models `Qwen/Qwen2.5-1.5B-Instruct` and `microsoft/Phi-3.5-mini-instruct`, temperatures `0.7` and `1.0`, elapsed worker seconds `23699.937`.
- Collector QA: `scripts/p3_collect_calibration.py` completed on local `runs/p3`; LEVI named appears in RQ1/RQ2 summaries (`Spearman 0.157`, sign agreement `0.354`, mean entropy `1.084`) and G3 kill condition still does not fire on available P3 artifacts.
- Budget ledger updated with 6.65 wall hours at `$0.30/hr` (`$1.99`), bringing cumulative estimated actual spend to `$32.50`; state budget reservation is `$38.35` including the three remaining active P3 jobs.

## [2026-07-08T11:07:17Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias are all `JOB_STATE_RUNNING`.
- Each remaining shard has `requests.jsonl` present and `outputs.jsonl` advanced to `640` rows / `640` parsed, with current valid JSON rate `1.000000`.

## [2026-07-08T11:38:50Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias remain `JOB_STATE_RUNNING`.
- A-317 LEVI alias advanced to `1,408` rows / `1,405` parsed, valid JSON rate `0.997869`.
- A-318 VKTX named advanced to `1,792` rows / `1,787` parsed, valid JSON rate `0.997210`; A-319 VKTX alias advanced to `1,664` rows / `1,659` parsed, valid JSON rate `0.996995`.

## [2026-07-08T12:10:13Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias remain `JOB_STATE_RUNNING`.
- A-317 LEVI alias advanced to `2,432` rows / `2,424` parsed, valid JSON rate `0.996711`.
- A-318 VKTX named advanced to `2,816` rows / `2,811` parsed, valid JSON rate `0.998224`; A-319 VKTX alias advanced to `2,688` rows / `2,680` parsed, valid JSON rate `0.997024`.

## [2026-07-08T12:41:29Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias remain `JOB_STATE_RUNNING`.
- A-317 LEVI alias advanced to `3,328` rows / `3,313` parsed, valid JSON rate `0.995493`; continue monitoring parse-rate trend.
- A-318 VKTX named advanced to `3,712` rows / `3,703` parsed, valid JSON rate `0.997575`; A-319 VKTX alias advanced to `3,712` rows / `3,698` parsed, valid JSON rate `0.996228`.

## [2026-07-08T13:12:56Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias remain `JOB_STATE_RUNNING`.
- A-317 LEVI alias advanced to `4,352` rows / `4,332` parsed, valid JSON rate `0.995404`; continue monitoring parse-rate trend.
- A-318 VKTX named advanced to `4,608` rows / `4,594` parsed, valid JSON rate `0.996962`; A-319 VKTX alias advanced to `4,608` rows / `4,589` parsed, valid JSON rate `0.995877`.

## [2026-07-08T13:44:18Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias remain `JOB_STATE_RUNNING`.
- A-317 LEVI alias advanced to `5,248` rows / `5,223` parsed, valid JSON rate `0.995236`; continue monitoring parse-rate trend.
- A-318 VKTX named and A-319 VKTX alias each advanced to `5,504` rows / `5,481` parsed, valid JSON rate `0.995821`.

## [2026-07-08T14:16:37Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias remain `JOB_STATE_RUNNING`.
- A-317 LEVI alias advanced to `6,272` rows / `6,245` parsed, valid JSON rate `0.995695`; A-318 VKTX named advanced to `6,528` rows / `6,499` parsed, valid JSON rate `0.995558`.
- Verified A-319 VKTX alias GCS run directory after one transient copy miss; `outputs.jsonl` is present and advanced to `6,656` rows / `6,626` parsed, valid JSON rate `0.995493`.

## [2026-07-08T14:47:47Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias remain `JOB_STATE_RUNNING`.
- A-317 LEVI alias advanced to `7,680` rows / `7,643` parsed, valid JSON rate `0.995182`; continue monitoring parse-rate trend.
- A-318 VKTX named advanced to `7,936` rows / `7,905` parsed, valid JSON rate `0.996094`; A-319 VKTX alias advanced to `8,064` rows / `8,032` parsed, valid JSON rate `0.996032`.

## [2026-07-08T15:19:15Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias remain `JOB_STATE_RUNNING`.
- A-317 LEVI alias advanced to `8,704` rows / `8,663` parsed, valid JSON rate `0.995290`; continue monitoring parse-rate trend.
- A-318 VKTX named advanced to `8,960` rows / `8,928` parsed, valid JSON rate `0.996429`; A-319 VKTX alias advanced to `9,088` rows / `9,054` parsed, valid JSON rate `0.996259`.

## [2026-07-08T15:50:35Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias remain `JOB_STATE_RUNNING`.
- A-317 LEVI alias advanced to `9,600` rows / `9,557` parsed, valid JSON rate `0.995521`.
- A-318 VKTX named advanced to `9,856` rows / `9,821` parsed, valid JSON rate `0.996449`; A-319 VKTX alias advanced to `10,240` rows / `10,204` parsed, valid JSON rate `0.996484`.

## [2026-07-08T16:11:59Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias remain `JOB_STATE_RUNNING`.
- A-317 LEVI alias advanced to `10,240` rows / `10,193` parsed, valid JSON rate `0.995410`.
- A-318 VKTX named advanced to `10,624` rows / `10,588` parsed, valid JSON rate `0.996611`; A-319 VKTX alias advanced to `10,880` rows / `10,841` parsed, valid JSON rate `0.996415`.

## [2026-07-08T16:28:24Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias remain `JOB_STATE_RUNNING`.
- A-317 LEVI alias advanced to `10,752` rows / `10,702` parsed, valid JSON rate `0.995350`.
- A-318 VKTX named advanced to `11,136` rows / `11,099` parsed, valid JSON rate `0.996677`; A-319 VKTX alias advanced to `11,520` rows / `11,481` parsed, valid JSON rate `0.996615`.

## [2026-07-08T16:44:48Z] P3/PARALLEL-POLL
- Remaining active jobs A-317 LEVI alias, A-318 VKTX named, and A-319 VKTX alias remain `JOB_STATE_RUNNING`.
- A-317 LEVI alias advanced to `11,264` rows / `11,213` parsed, valid JSON rate `0.995472`.
- A-318 VKTX named advanced to `11,648` rows / `11,611` parsed, valid JSON rate `0.996823`; A-319 VKTX alias advanced to `11,776` rows / `11,736` parsed, valid JSON rate `0.996603`.

## [2026-07-08T17:18:00Z] P3/A-319-VKTX-ALIAS-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/4859622050790113280` completed successfully at `2026-07-08T17:16:31Z`; final `outputs.jsonl` has `12,800` rows / `12,758` parsed, valid JSON rate `0.996719`, and `sim.jsonl` has `128` rows.
- Downloaded completed run artifacts from GCS to ignored local path `runs/p3/calib-2019-g1-vktx-alias-v1/`, including `sim.jsonl` and `worker_summary.json`.
- Worker summary: 128 days, 100 agents, models `Qwen/Qwen2.5-1.5B-Instruct` and `microsoft/Phi-3.5-mini-instruct`, temperatures `0.7` and `1.0`, elapsed worker seconds `2511.578`.
- Collector QA: `scripts/p3_collect_calibration.py` completed on local `runs/p3`; VKTX alias appears in RQ1/RQ2 summaries (`Spearman 0.119`, sign agreement `0.827`, mean entropy `1.069`) and G3 kill condition still does not fire on available P3 artifacts.
- Budget ledger updated with 6.51 wall hours at `$0.30/hr` (`$1.95`), bringing cumulative estimated actual spend to `$34.45`; state budget reservation remains `$38.35` including A-317 LEVI alias and A-318 VKTX named.

## [2026-07-08T17:27:44Z] P3/A-318-VKTX-NAMED-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/2035865084428812288` completed successfully at `2026-07-08T17:21:26Z`; final `outputs.jsonl` has `12,800` rows / `12,761` parsed, valid JSON rate `0.996953`, and `sim.jsonl` has `128` rows.
- Downloaded completed run artifacts from GCS to ignored local path `runs/p3/calib-2019-g1-vktx-named-v1/`, including `sim.jsonl` and `worker_summary.json`.
- Worker summary: 128 days, 100 agents, models `Qwen/Qwen2.5-1.5B-Instruct` and `microsoft/Phi-3.5-mini-instruct`, temperatures `0.7` and `1.0`, elapsed worker seconds `23608.218`.
- Collector QA: VKTX named appears in RQ1/RQ2 summaries (`Spearman 0.142`, sign agreement `0.827`, mean entropy `1.073`) and G3 kill condition still does not fire.
- Budget ledger updated with 6.60 wall hours at `$0.30/hr` (`$1.98`).

## [2026-07-08T17:29:28Z] P3/A-317-LEVI-ALIAS-COMPLETE
- Vertex job `projects/987318647780/locations/us-central1/customJobs/3715707745438007296` completed successfully at `2026-07-08T17:29:05Z`; final `outputs.jsonl` has `12,800` rows / `12,744` parsed, valid JSON rate `0.995625`, and `sim.jsonl` has `128` rows.
- Downloaded completed run artifacts from GCS to ignored local path `runs/p3/calib-2019-g1-levi-alias-v1/`, including `sim.jsonl` and `worker_summary.json`.
- Worker summary: 128 days, 100 agents, models `Qwen/Qwen2.5-1.5B-Instruct` and `microsoft/Phi-3.5-mini-instruct`, temperatures `0.7` and `1.0`, elapsed worker seconds `21315.639`.
- Collector QA: LEVI alias appears in RQ1/RQ2 summaries (`Spearman 0.111`, sign agreement `0.354`, mean entropy `1.073`) and G3 kill condition still does not fire.
- Budget ledger updated with 6.73 wall hours at `$0.30/hr` (`$2.02`), bringing cumulative estimated actual spend for P0-P3 to `$38.45`.

## [2026-07-08T17:31:00Z] P3/G3-PASS
- P3 calibration completed across 10 tickers, two anonymization arms, 20 Vertex shards, `256,000` requests, and `256,000` outputs; weighted valid JSON rate is `0.996898`.
- Committed final reports to `docs/RQ1_REPORT.md` and `docs/RQ2_REPORT.md`, with 20 event-window figures under `docs/figures/p3/`.
- Final pooled RQ2 metrics: alias Spearman `0.044`, sign agreement `0.524`, mean entropy `1.041`; named Spearman `0.036`, sign agreement `0.524`, mean entropy `1.041`.
- Named-vs-alias gaps are small: sign agreement `-0.001`, Spearman `-0.008`.
- G3 kill condition does not fire because sign agreement is above `0.52` in both arms and stylized-fact artifacts are not qualitatively absent. State advances to P4 with no active Vertex jobs.

## [2026-07-08T17:45:00Z] P4/A-401-MAIN-FREEZE
- Reconciled the stale OOS config with registered A-401: froze the main run to 10 OOS tickers, alias arm, 200 agents per ticker, and the first 125 common trading days (`2025-01-02` through `2025-07-03`) for exactly `250,000` planned decisions.
- Recorded G1 universe freeze commit `d77cdad401622404c0ce75c6fc44e82376b34555` in `configs/sim_oos_2025.yaml`; OOS ticker order remains unchanged.
- Updated `docs/TRIALS.md` before inference with the exact main-run window for weighted crowd flow, unweighted flow, single-model baseline, and mandatory momentum/AR(1)/logistic baselines.
- Added `scripts/p4_oos_worker.py` and `launch-oos-main` orchestration. The Vertex worker reads OOS snapshots and GCS-cached model weights, emits raw decisions, daily crowd/per-model flows, past-only momentum features, and next-day real-return targets.
- QA: dry-run Vertex spec uses `n1-standard-8` + spot T4, model IDs and `--gcs-model-root` are worker arguments, environment is empty, scripts compile, secret scan is clean, and `pytest -q` passes `44/44`.

## [2026-07-08T17:54:00Z] P4/A-401-G4-HALF-LAUNCH
- Cloud Build `10706cbb-2731-41ca-b062-996881710337` published the P4 worker image successfully with digest `sha256:6c09c1dff4454c939c43d013eccf5cd89002547307259861cd64e3030d041b72`.
- Launched the first five main-run tickers concurrently for the mandatory 50% G4 checkpoint: NVNI `4599024600867667968`, TLRY `703410923192188928`, EDIT `1872657976448253952`, CHPT `4450968763117862912`, and BLNK `2500347174513016832`.
- Each spot Vertex T4 job is frozen to the alias arm, 200 agents, 125 trading days, and exactly 25,000 requests. All model weights are read from the Vertex-populated GCS cache; job specs contain no secret environment variables.
- Reserved budget is `$18.43` for 125,000 decisions based on the observed P3 rate, bringing the tracked estimate to `$56.88`. The remaining five tickers stay paused until G4 compares actual P4 spend per decision with the G0 baseline.

## [2026-07-08T18:05:00Z] P4/A-501-ANALYSIS-PREP
- Added `scripts/p4_collect_oos.py` for leakage-safe RQ3/P5 analysis: per-ticker and pooled IC/hit rate, date-level portfolio Sharpe, date-aggregated DM tests, moving-block bootstrap intervals, registered-trial DSR, and entropy diagnostics.
- Mandatory baselines are explicit: per-model Qwen crowd flow, momentum 1/5/20, expanding-window AR(1), and expanding-window logistic regression over market features available by the decision date.
- Added `scripts/p4_gate_budget.py`; G4 is computed from archived worker summaries against the G0 baseline of 4,747 decisions/hour at `$0.30/hour`, with the registered 30% pause threshold.
- Live QA confirmed four concurrent workers loaded Qwen weights from `/tmp` after GCS download and checkpointed their first 128-output batches. CHPT remains queued for available capacity.
- Local QA: `pytest -q` passes `53/53`, scripts compile, diff check passes, and the repository secret scan remains clean.

## [2026-07-08T18:10:00Z] P4/A-402-A-403-PREP
- Froze the two-ticker follow-up surface to NVNI/TLRY and their first 60 shared sessions, `2025-01-02` through `2025-03-31`, with scaling sizes `[50, 100, 300, 1000]` and 100-agent ablations.
- Extended the OOS launcher with collision-free experiment paths for `scaling`, `news-off`, and `personas-off`; no follow-up trial was registered or submitted before G4.
- Implemented actual ablation semantics in the Vertex worker: news-off renders an empty headline block, while personas-off uses one deterministic homogeneous persona repeated across agents.
- Centralized homogeneous-persona construction and hashing so the run manifest hashes the exact persona content rendered into prompts.
- QA: isolated worker/launcher tests and the full suite pass (`56/56`), scripts compile, the 60-day config parses, diff check passes, and the secret scan is clean.

## [2026-07-10T08:17:28Z] P4/RESUME-G4-QUOTA
- Resumed after Vertex migration; non-negotiable project rule is now enforced as `jjjsresearch@gmail.com` / `project-82d97cf9-5889-43a4-850` for all future heavy computation and LLM inference. The old project is not polled or used for new compute; only transferred GCS artifacts are read from the new bucket.
- Reconciled stale `STATE.json` active jobs from the old project by syncing transferred P4 main artifacts from `gs://project-82d97cf9-5889-43a4-850-agorasim/agorasim/runs/p4/main/`.
- G4 checkpoint artifacts validated for `BLNK`, `CHPT`, `EDIT`, `NVNI`, and `TLRY`: each run has `25,000` requests, `25,000` outputs, and `125` sim rows. `docs/G4_REPORT.md` decision is `PASS`: 125,000/125,000 outputs, 32.200 worker hours, `$9.66` estimated checkpoint spend, and cost/decision 22.3% over G0 versus the 30% pause threshold.
- Submitted T4 quota preferences on the new project for `us-central1`, preferred value `6`: Vertex custom training preemptible T4 (`granted=1`), Vertex custom training regular T4 (`granted=0`), Compute preemptible T4 (`granted=1`), and Compute regular T4 (`granted=1`). All four quota preferences are reconciling.
- Optimized `scripts/p4_collect_oos.py` block bootstrap so the 1,000-repetition RQ3 checkpoint report finishes locally in about 21 seconds instead of timing out; local stats remain CPU-only and no LLM inference is local.
- QA: `python -m pytest -q` passes `57/57`; `docs/RQ3_REPORT.md` generated from the five completed checkpoint runs; `BUDGET.md` cumulative estimate updated to `$48.11`; `STATE.json` cleared stale active jobs and records `A-401-G4-PASS`.

## [2026-07-10T08:23:00Z] P4/A-401-REMAINING-LAUNCH
- Patched Vertex launcher safety before launch: REST access tokens and manifest uploads now use explicit `agorasim-new` gcloud configuration by default, preventing accidental use of the old active CLI account.
- QA before launch: dry-run specs for `FRSX`, `TPET`, `OGI`, `CCO`, and `ICCM` point only to `project-82d97cf9-5889-43a4-850`, `gs://project-82d97cf9-5889-43a4-850-agorasim`, and the new Artifact Registry image; env arrays are empty; `python -m pytest -q` passes `58/58`; secret scan clean.
- Launched remaining P4 main alias shards on the new project only: FRSX `projects/423678956768/locations/us-central1/customJobs/8106482086635896832`, TPET `6057344256182321152`, OGI `2974630311247216640`, CCO `6174437846493954048`, ICCM `1112385268259749888`.
- All five jobs were accepted as `JOB_STATE_PENDING` in `us-central1`. Quota preferences now show Vertex custom training preemptible T4 `granted=6/preferred=6`, Vertex custom training regular T4 `granted=6/preferred=6`, Compute regular T4 `granted=1/preferred=6`, and Compute preemptible T4 `granted=4/preferred=6`.
- Reserved an additional `$9.66` based on the completed G4 half-run cost, bringing `STATE.json` budget estimate to `$57.77`, still below the `$85` launch stop threshold.

## [2026-07-10T08:28:41Z] P4/POLL
- New-project jobs FRSX, TPET, OGI, CCO, and ICCM remain `JOB_STATE_PENDING` in `project-82d97cf9-5889-43a4-850`; no worker error logs are present for inspected job FRSX.
- GCS run directories contain manifests only; `outputs.jsonl` is not present yet for any of the five remaining shards.
- Quota preferences are granted for Vertex custom training T4 at preferred value `6`; pending state is treated as Vertex spot capacity/provisioning wait, not a configuration failure.

## [2026-07-10T08:39:58Z] P4/POLL
- All five remaining P4 main shards are `JOB_STATE_RUNNING` on `project-82d97cf9-5889-43a4-850`; no job is using the old Vertex account.
- GCS output checkpoints are present in the new bucket: FRSX `128`, TPET `128`, OGI `128`, CCO `128`, and ICCM `256` rows in `outputs.jsonl`.
- This confirms the workers pulled the new Artifact Registry image, loaded model weights from the migrated GCS cache, and began Vertex-only inference.

## [2026-07-10T08:52:20Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `640`, TPET `640`, OGI `640`, CCO `640`, ICCM `640` rows.
- Lightweight parse QA on the previous checkpoint was `1.000000` valid for all five shards; continue polling.

## [2026-07-10T09:14:19Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on `project-82d97cf9-5889-43a4-850`.
- Output progress in the new bucket: FRSX `1,408`, TPET `1,408`, OGI `1,408`, CCO `1,408`, ICCM `1,536` rows.
- Switched polling counts from full GCS downloads to streamed line counts after a local copy command timed out; no Vertex job failure was observed.

## [2026-07-10T09:26:27Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `1,792`, TPET `1,792`, OGI `1,920`, CCO `1,792`, ICCM `1,920` rows.
- One streamed count briefly returned `0` for OGI while the job was running; direct GCS recheck found `outputs.jsonl` present and at `1,920` rows, so this was a transient read/count miss.

## [2026-07-10T09:38:52Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `2,176`, TPET `2,176`, OGI `2,304`, CCO `2,304`, ICCM `2,432` rows.
- No failures or old-project activity observed; continue polling.

## [2026-07-10T09:50:38Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `2,560`, TPET `2,688`, OGI `2,688`, CCO `2,688`, ICCM `2,816` rows.
- Parse QA over streamed current outputs remains `1.000000` valid for all five shards.

## [2026-07-10T10:02:59Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `2,816`, TPET `2,944`, OGI `3,072`, CCO `3,072`, ICCM `3,200` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T10:14:16Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `3,200`, TPET `3,328`, OGI `3,456`, CCO `3,328`, ICCM `3,584` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T10:27:12Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `3,456`, TPET `3,584`, OGI `3,840`, CCO `3,712`, ICCM `3,968` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T10:39:22Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `3,840`, TPET `3,968`, OGI `4,096`, CCO `3,968`, ICCM `4,352` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T10:52:07Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `4,224`, TPET `4,352`, OGI `4,480`, CCO `4,352`, ICCM `4,736` rows.
- Parse QA over streamed current outputs remains `1.000000` valid for all five shards.

## [2026-07-10T11:03:39Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `4,480`, TPET `4,736`, OGI `4,864`, CCO `4,736`, ICCM `4,992` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T11:15:40Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `4,864`, TPET `5,120`, OGI `5,120`, CCO `4,992`, ICCM `5,376` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T11:27:00Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `5,120`, TPET `5,376`, OGI `5,504`, CCO `5,376`, ICCM `5,632` rows.
- Parse QA over streamed current outputs remains `1.000000` valid for all five shards.

## [2026-07-10T11:38:57Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `5,376`, TPET `5,760`, OGI `5,760`, CCO `5,632`, ICCM `5,760` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T11:50:19Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `5,760`, TPET `6,144`, OGI `6,144`, CCO `6,016`, ICCM `6,016` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T12:01:19Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `6,016`, TPET `6,400`, OGI `6,400`, CCO `6,272`, ICCM `6,400` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T12:12:21Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `6,400`, TPET `6,784`, OGI `6,784`, CCO `6,656`, ICCM `6,656` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T12:23:27Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `6,656`, TPET `7,040`, OGI `7,168`, CCO `6,912`, ICCM `7,040` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T12:34:23Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `7,040`, TPET `7,296`, OGI `7,424`, CCO `7,168`, ICCM `7,296` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T12:45:21Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `7,296`, TPET `7,680`, OGI `7,808`, CCO `7,552`, ICCM `7,552` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T12:56:16Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `7,680`, TPET `8,064`, OGI `8,192`, CCO `7,808`, ICCM `7,936` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T13:07:26Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `8,064`, TPET `8,320`, OGI `8,576`, CCO `8,064`, ICCM `8,320` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T13:18:37Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `8,320`, TPET `8,704`, OGI `8,960`, CCO `8,448`, ICCM `8,704` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T13:29:51Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `8,704`, TPET `9,088`, OGI `9,344`, CCO `8,832`, ICCM `8,960` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T13:40:55Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `9,088`, TPET `9,472`, OGI `9,856`, CCO `9,216`, ICCM `9,344` rows.
- Parse QA over streamed current outputs remains `1.000000` valid for all five shards.

## [2026-07-10T13:52:21Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `9,344`, TPET `9,856`, OGI `10,112`, CCO `9,472`, ICCM `9,728` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T14:03:28Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `9,728`, TPET `10,240`, OGI `10,496`, CCO `9,856`, ICCM `9,984` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T14:14:53Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `9,984`, TPET `10,496`, OGI `10,752`, CCO `10,240`, ICCM `10,368` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T14:25:57Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `10,368`, TPET `10,880`, OGI `11,136`, CCO `10,496`, ICCM `10,624` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T14:37:38Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `10,752`, TPET `11,264`, OGI `11,520`, CCO `10,880`, ICCM `11,008` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T14:49:01Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `11,008`, TPET `11,648`, OGI `11,776`, CCO `11,264`, ICCM `11,392` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T15:00:13Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `11,264`, TPET `12,032`, OGI `12,160`, CCO `11,648`, ICCM `11,776` rows.
- No failures or preemptions observed; continue polling.

## [2026-07-10T15:11:26Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `11,648`, TPET `12,416`, OGI `12,500`, CCO `12,032`, ICCM `12,160` rows.
- Halfway parse QA over streamed current outputs remains `1.000000` valid for all five shards.

## [2026-07-10T15:23:30Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `11,904`, TPET `13,012`, OGI `13,268`, CCO `12,416`, ICCM `12,628` rows.
- Counts were read while workers were writing and may include non-chunk boundary totals; no failures or preemptions observed.

## [2026-07-10T15:34:34Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `12,288`, TPET `13,780`, OGI `13,908`, CCO `13,012`, ICCM `13,396` rows.
- Counts were read while workers were writing and may include non-chunk boundary totals; no failures or preemptions observed.

## [2026-07-10T15:45:53Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `12,628`, TPET `14,292`, OGI `14,420`, CCO `13,780`, ICCM `14,036` rows.
- Counts were read while workers were writing and may include non-chunk boundary totals; no failures or preemptions observed.

## [2026-07-10T15:56:55Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `13,396`, TPET `14,804`, OGI `14,932`, CCO `14,292`, ICCM `14,548` rows.
- Counts were read while workers were writing and may include non-chunk boundary totals; no failures or preemptions observed.

## [2026-07-10T16:08:05Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `13,908`, TPET `15,188`, OGI `15,316`, CCO `14,676`, ICCM `14,932` rows.
- Counts were read while workers were writing and may include non-chunk boundary totals; no failures or preemptions observed.

## [2026-07-10T16:20:54Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `14,420`, TPET `15,572`, OGI `15,700`, CCO `15,188`, ICCM `15,444` rows.
- Counts were read while workers were writing and may include non-chunk boundary totals; no failures or preemptions observed.

## [2026-07-10T16:32:11Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `14,804`, TPET `16,084`, OGI `16,084`, CCO `15,572`, ICCM `15,828` rows.
- Counts were read while workers were writing and may include non-chunk boundary totals; no failures or preemptions observed.

## [2026-07-10T16:43:17Z] P4/POLL
- Remaining P4 main shards are all still `JOB_STATE_RUNNING` on the new project.
- Output progress in the new bucket: FRSX `15,188`, TPET `16,468`, OGI `16,468`, CCO `15,956`, ICCM `16,212` rows.
- Counts were read while workers were writing and may include non-chunk boundary totals; no failures or preemptions observed.
