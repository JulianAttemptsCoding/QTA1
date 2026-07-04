# AgoraSim — Execution Thought Log (APPEND-ONLY, R2)

## [2026-07-02T22:03:37Z] P0/START
- Mission: execute AgoraSim plan (PLAN.md) end-to-end, autonomous. ALL heavy compute + ALL LLM download/inference on Vertex AI. Deliverable committed to github.com/JulianAttemptsCoding/QTA1 (empty, public).
- Repo layout: working dir = `.../currect QR/claude` (agorasim). Surrounding git root = `.../currect QR` = SEPARATE QTA0/TACTIC-MoB project (origin=QTA0.git, branches run0/run1/run2...). `claude/` is UNTRACKED by that parent repo.
  - DECISION/ASSUMPTION: init a DEDICATED git repo inside `claude/`, remote -> QTA1, commit here. Do NOT touch parent QTA0 repo or its branches (user's prior work).
- Environment probe:
  - gcloud: AUTHENTICATED (active juliansjuan08@gmail.com; also bubgaming3, hellotherestarwar). project=project-c779f701-1a49-4a58-b54, region us-central1. Billing ENABLED.
  - .env PRESENT, var names only: APCA_API_KEY_ID, APCA_API_SECRET_KEY, FRED_API_KEY, SEC_USER_AGENT. ASSUMPTION: plan says SEC_API_USER_AGENT but repo uses SEC_USER_AGENT -> treat SEC_USER_AGENT as EDGAR UA. HF_TOKEN absent from .env; supplied at runtime by user, used ONLY as Vertex env var on model_cache job (P-17), never written to any file.
  - python local = 3.12.12 (miniforge base). Worker image = python 3.11 + vllm on Vertex.
  - gh: authenticated as JulianAttemptsCoding (scopes repo, workflow). QTA1 exists, EMPTY, PUBLIC.
- HARD BLOCKER probes (§12): B1 auth OK; B2 billing OK; B4 APCA keys PRESENT (validate in A-002). B3 GPU quota: us-central1 Compute Engine NVIDIA_T4_GPUS limit=1, PREEMPTIBLE_NVIDIA_T4_GPUS limit=1 -> N_workers=1 (serial). Not zero -> NOT blocked. Vertex custom-training T4 quota to be confirmed by 1-replica probe (P-04). No hard blockers.
- Security: user pasted HF token in plaintext in prompt -> flagged compromised to user, advised rotation. QTA1 PUBLIC -> never commit .env/keys/HF token/raw vendor data. .env confirmed in .gitignore.
- Pinned params locked: P-01 region us-central1; P-02 bucket gs://project-c779f701-1a49-4a58-b54-agorasim; P-03 worker n1-standard-8 + 1x T4 spot, disk>=100GB; P-04 N_workers=1 pending probe; P-05 models = ungated four (Qwen2.5-1.5B/3B, Phi-3.5-mini, SmolLM2-1.7B) + gated two (Llama-3.2-3B, Gemma-2-2B) IF HF licenses accepted.
- Next: local env (pytest 14/14, make smoke=PASS); code inventory; backup commit + push QTA1; A-002 data gate.

## [2026-07-02T22:13:04Z] P0/A-000+A-001 — local gates + backup
- Local env: `pip install -e ".[dev]"` exit 0; `pytest -q` = 14/14; `python scripts/p2_smoke_sim.py --config configs/sim_smoke.yaml` -> `GATE G2 SMOKE: PASS` (parse-valid 0.995). (`make` not used on Windows; ran targets directly.)
- Code inventory (Explore): COMPLETE = schemas, personas, prompt_builder, run_manifest, clearing, evals/{contamination,prediction,stylized_facts}, alpaca_bars, robintrack, p2_smoke_sim, all tests, all prompts. STUB (I must implement) = infra/vertex_launch.py, data/universe.py, data/alpaca_news.py, scripts/p0_gate_data.py, scripts/p0_gate_throughput.py. MISSING (must create) = scripts/run_sim_phase.py. vllm_batch.run_offline is implemented (Vertex-only).
- Backup: git init -b main inside claude/, remote origin=github.com/JulianAttemptsCoding/QTA1.git, initial commit a4b50b3, pushed (new branch main). .env NOT tracked (verified). QTA1 PUBLIC.

## [2026-07-02T22:13:04Z] P0/A-002 — data reality gate = PASS
- Implemented data/alpaca_news.py (iter_news, paginated) + scripts/p0_gate_data.py (6 checks, writes docs/G0_REPORT.md, self-loads .env, sanitizes FRED key from errors). Added tests/test_data_loaders.py (2 tests) -> pytest 16/16.
- Results (docs/G0_REPORT.md):
  - alpaca_bars_liquid PASS (AAPL sip, earliest-in-window 2016-01-04).
  - FEED MATRIX (smallcap GPRO/SGMO/PLUG daily bar counts): iex/2019H2=0, iex/recent=60; sip/2019H2=128, sip/recent=60; default==sip. DECISION: use feed="sip" for ALL historical snapshots (IEX has no pre-2020 small-cap history) -> resolves F-03. Small-cap coverage adequate.
  - alpaca_news_depth PASS (earliest 2015-01-01; 60d smallcap counts GPRO 10/SGMO 9/PLUG 39 — sparse but usable).
  - edgar_ping PASS (Apple Inc companyfacts); fred_ping PASS (GDP series).
  - robintrack_archive SOFT-BLOCK: no local export at data/raw/robintrack/popularity_export/; robintrack.net + github/Ameobea pages return 200 but no bulk data fetched yet. Per PLAN section 4: CONTINUE all non-Robintrack (OOS) work; revisit before P3. Real bulk-download attempt deferred to P3-prep.
- **GATE G0 (data) = PASS.** (G0 full gate still needs A-003 throughput on Vertex.)
- SOFT BLOCKER (user action, non-halting): if Robintrack bulk download keeps failing at P3-prep, download Kaggle "Robinhood Stock Popularity History" and extract to data/raw/robintrack/popularity_export/ as <TICKER>.csv (cols timestamp,users_holding), then continue.
- Next: A-003 = build worker image (Cloud Build -> Artifact Registry), create GCS bucket, model_cache job (P-17), throughput probe (P-14). First Vertex spend.

## [2026-07-02T22:25:31Z] P0/A-003 -- worker image build + Vertex job scaffolding
- Committed A-003 scaffolding (commit e8611f3, pushed QTA1): docker/Dockerfile.worker, cloudbuild.yaml, .dockerignore, infra/gcs.py, infra/model_cache.py (P-17), infra/throughput_probe.py (G0 compute), scripts/p0_gate_throughput.py, configs/models.yaml (P-05 six models).
- Cloud Build launched: build id daaf6fdf-cbac-4d17-b023-6387c063d692, target image us-central1-docker.pkg.dev/project-c779f701-1a49-4a58-b54/agorasim/worker:v1. Status WORKING (polling per P-14).
- GCS base = gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim.
- Next (blocked on image SUCCESS): launch model_cache Vertex job (HF_TOKEN via temp job YAML, never committed) -> download six models to GCS + record SHAs (docs/MODEL_SHAS.md); then throughput probe (T4 spot) per cached model -> assemble docs/G0_THROUGHPUT.md -> evaluate full GATE G0.

## [2026-07-03T03:25:59Z] P0/A-003 -- git rebranch + model_cache Vertex job launched
- Repo restructure (user request): renamed branch main -> claude; pushed claude; set claude as GitHub default; DELETED remote main. Only branch on QTA1 now = claude. Local branch claude matches working folder (.env gitignored, untracked).
- Worker image build SUCCESS; tags [v1, latest] in us-central1-docker.pkg.dev/project-c779f701-1a49-4a58-b54/agorasim/worker.
- P-17 model_cache Vertex job LAUNCHED (first Vertex spend): job_id 2444747620275453952, region us-central1, n1-standard-8 (no GPU, on-demand), bootDisk 200GB pd-ssd. HF_TOKEN passed via temp job YAML (/tmp/mc_job.yaml) -> job submitted -> temp YAML DELETED (never committed, R4). Models: 4 ungated + 2 gated (gated skipped non-fatal if license not accepted).
- Polling per P-14 (120s). Will not end while job RUNNING (R: never end with active Vertex job).
- Next: on SUCCESS, read docs/MODEL_SHAS.md from GCS manifest -> then throughput probe (T4 spot) per cached model -> docs/G0_THROUGHPUT.md -> full GATE G0 decision.

## [2026-07-03T03:47:42Z] P0/A-003 -- model_cache SUCCEEDED + GATE G0 throughput launched
- model_cache job 2444747620275453952 = JOB_STATE_SUCCEEDED (wall ~8min, est $0.05). Manifest gs://.../models/_cache_manifest.json:
  - OK (weights in GCS): Qwen/Qwen2.5-1.5B-Instruct (sha 989aa79, 21 files), Qwen/Qwen2.5-3B-Instruct (aa8e725, 25), microsoft/Phi-3.5-mini-instruct (2fe1924, 41), HuggingFaceTB/SmolLM2-1.7B-Instruct (31b70e2, 41).
  - SKIP: meta-llama/Llama-3.2-3B-Instruct + google/gemma-2-2b-it = GatedRepoError 403 (HF token license not accepted). Non-fatal per P-05. Proceeding with 4 ungated (>= min models needed).
- SHAs recorded docs/MODEL_SHAS.md; configs/models.yaml revisions pinned; corrected MODEL_SHAS.md uploaded to GCS (stale copy had wrong --dash URIs).
- Housekeeping: deleted stale --dash model dirs (from pre-compaction attempt, 22:58Z) left in GCS; kept current __underscore dirs (03:29Z, match sanitize()). Verified all 4 __ dirs have safetensors shards (2/6/6/2).
- GATE G0 throughput LAUNCHED via scripts/launch_g0_throughput.sh (background task b89g58r10): 4 jobs, ONE per model, SERIAL (T4 quota==1), n1-standard-8 + 1x T4 SPOT, --n 512. First job agorasim-g0-thru-Qwen__Qwen2.5-1.5B-Instruct = PENDING. Each writes gs://.../runs/g0_throughput/<model>.json (decisions_per_hour + valid_json_rate).
- G0 kill criteria (PLAN): throughput < 2000 dec/hr OR valid-JSON < 90%. Polling per P-14; will not end while jobs run.
- Next: on ALL_THROUGHPUT_JOBS_DONE -> assemble docs/G0_THROUGHPUT.md -> full GATE G0 decision + docs/FEASIBILITY_ADDENDUM.md (A-004).

## [2026-07-03T04:19:12Z] P0/A-003 -- GATE G0 throughput jobs FAILED (fixed, rebuilding v2)
- All 4 g0-throughput jobs = JOB_STATE_FAILED. Root cause (logs): `WARNING _custom_ops.py Failed to import from vllm._C with ImportError('libcuda.so.1: cannot open shared object file')` -> `RuntimeError: Failed to infer device type`. vLLM could not find the GPU driver.
- Diagnosis: worker image FROM python:3.11-slim. Vertex nvidia-container-runtime mounts the driver (libcuda.so.1) into /usr/local/nvidia/lib64, but slim base does not include that dir on LD_LIBRARY_PATH, so the loader cannot find it. (model_cache job was CPU-only -> unaffected, which is why it passed.)
- Idea source: peeked codex/docker/Dockerfile.worker (sibling project, same task) which sets LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/cuda/lib64 + NVIDIA_VISIBLE_DEVICES + NVIDIA_DRIVER_CAPABILITIES. Applied same ENV fix (did not copy code). Commit ade5714.
- Rebuilding worker image as :v2 (Cloud Build, background b2fnc5s7x). On SUCCESS -> re-run scripts/launch_g0_throughput.sh with :v2 image.
- No result files written; NOT a G0 kill (kill = throughput<2000 OR valid-JSON<90% on a WORKING run; this was an infra fault, not a model-capability fault). Retry after image fix.
- Failed job ids: 5857209500427091968, 7381677974292004864, 8302664098089271296, 5366880090997129216 (all ~1-2 min, spot; negligible cost, no GPU-seconds billed on early crash).

## [2026-07-03T04:43:53Z] P0/A-003 -- GPU fix confirmed; valid-JSON diagnosis + guided decoding
- v2 image (GPU driver fix) WORKS: validation job 6457877100727631872 = SUCCEEDED. Result Qwen2.5-1.5B: decisions_per_hour=10353 (>2000 OK), valid_json_rate=0.2246 (22% -- FAR below 90% G0 threshold).
- Diagnosis: throughput was fine, JSON validity was not. Free-form generation lets small models loop/ramble (e.g. "100 shares at 20.41, 100 shares at 20.41, ...") until max_tokens=160 -> truncated invalid JSON.
- Idea source: codex/runs/g0-throughput/*.json (sibling project) show guided_decoding:true -> valid_json_rate 1.0 (Qwen1.5B/3B/Phi), 0.988 (SmolLM2), and their invalid_examples show the exact loop/truncation failure mode. Applied same MECHANISM (vLLM guided JSON decoding to the AgentDecision schema); did not copy code.
- Fix (commit): throughput_probe now uses SamplingParams(guided_decoding=GuidedDecodingParams(json=AgentDecision.model_json_schema())) + records up to 3 invalid_examples. This is the same constrained-decoding the real sim needs for G2 (>=99%). NOTE: wire the same into agents/vllm_batch.run_offline at P2.
- Rebuilding worker:v3 (Cloud Build bhn6w055f). On SUCCESS -> re-validate Qwen1.5B (expect ~100% valid) -> run all 4 -> docs/G0_THROUGHPUT.md -> GATE G0.
- NOT a G0 kill: the 22% was a probe/decoding artifact (infra), not a working-run model-capability measurement.

## [2026-07-03T05:20:00Z] P0/A-003 -- guided-decoding stack fixed (v3->v7); rationale-truncation root cause
- v3 FAILED: `ModuleNotFoundError: No module named 'pyairports'` -- default `outlines` guided backend pulls a broken pyairports dep on vllm 0.6.3.post1. Pinning pyairports (v4) did not help (pip resolved a 3.1kB stub).
- v4->v5: switched GuidedDecodingParams backend to "lm-format-enforcer" (vLLM's other bundled JSON decoder, no outlines chain). v5 FAILED: `ImportError: cannot import name 'LogitsWarper' from transformers.generation.logits_process` -- lm-format-enforcer's transformers integration imports LogitsWarper, removed in transformers >=4.48.
- v5->v6: pinned transformers==4.46.3 (still has LogitsWarper). v6 guided decoding RUNS (job 8758660157430300672 SUCCEEDED, no crash). BUT valid_json_rate=0.2344 (23%), still < 90% G0. decisions_per_hour=2709 (>2000 OK).
- Root cause of the 23%: invalid_examples were all truncated mid-rationale (e.g. "...Limited risk appetite and medium-term<cut>"). The probe passed AgentDecision.model_json_schema() to the decoder, which leaves rationale at max_length=2000; the decoder generated a rationale far longer than the max_tokens=160 budget, so the JSON never closed.
- Idea source: peeked codex/scripts/p0_gate_throughput.py (sibling project). They pass a HAND-BUILT schema with `rationale maxLength: 240` (~60-80 tokens) + `additionalProperties:False` + all-required, and sample at temperature=0.0. A tight rationale cap lets the whole object close within 160 tokens. Applied same mechanism (did not copy code).
- Fix (v7): throughput_probe now uses module-level DECISION_JSON_SCHEMA (rationale maxLength 240, additionalProperties False, all required) instead of the pydantic schema, and SamplingParams(temperature=0.0). Rebuilding worker:v7 (Cloud Build).
- On SUCCESS -> re-validate Qwen1.5B (expect >=0.90 valid) -> run all 4 via launcher -> docs/G0_THROUGHPUT.md -> GATE G0.
- NONE of v3-v6 were G0 kills: all were probe/decoding infra faults, not working-run model-capability measurements.

## [2026-07-03T06:55:00Z] P0/A-003 -- maxLength not enforced on vllm 0.6.3 -> bump to 0.6.4.post1
- v7 (hand-built schema + additionalProperties:False) FAILED: `AttributeError: 'bool' object has no attribute 'get'` in lm-format-enforcer's jsonschemaobject parser -- the lmfe bundled with vllm 0.6.3.post1 treats additionalProperties:False as a sub-schema and calls .get() on the bool. Removed additionalProperties (v8): guided decoding already restricts output to listed props, so it was redundant.
- v8 (validate Qwen1.5B) SUCCEEDED but valid_json_rate=0.1777 (18%), dec/hr=4164. invalid_examples STILL truncated mid-rationale ("...strong buy signal from the<cut>"). So the rationale maxLength:240 was NOT being enforced by the lmfe bundled with vllm 0.6.3.post1 -- the model rambled a long rationale and hit max_tokens=160.
- Root cause: vllm 0.6.3.post1 bundles an older lm-format-enforcer that ignores JSON-schema string maxLength. codex (sibling) uses the SAME hand-built schema (rationale maxLength 240) + temperature 0.0 + max_tokens 160 and gets valid_json_rate 1.0 -- because their image pins vllm==0.6.4.post1, whose newer lmfe DOES enforce maxLength.
- Fix (v9): bumped Dockerfile vllm 0.6.3.post1 -> 0.6.4.post1; pin torch==2.5.1+cu121 first (T4 sm_75) so vllm reuses it (matches codex's proven stack). transformers stays 4.46.3. Idea source: codex/docker/Dockerfile.worker (did not copy).
- Rebuilding worker:v9 (Cloud Build b3wtauiv7). On SUCCESS -> re-validate Qwen1.5B (expect >=0.90) -> full 4-model launcher -> docs/G0_THROUGHPUT.md -> GATE G0.
- Cost note: v7 (crash at chat, ~model-load only) + v8 (full run 443s) validation jobs = extra T4 spot minutes (~0.15-0.2 GPU-hr total, ~$0.05). Under budget.

## [2026-07-03T09:35:00Z] P0/A-003 -- valid-JSON SOLVED (1.0); 4-model G0 run launched + T4 quota bump
- ROOT CAUSE of the valid-JSON failures was NOT the decoder/schema/vllm version. v9 (vllm 0.6.4.post1) gave byte-identical output to v8 (0.6.3) -> greedy determinism proved the REQUEST was the variable, not the decoder. Two deltas vs codex's proven-1.0 setup:
  1. I used llm.chat([{system},{user}]) -> applies the Qwen chat template -> instruct model answers in verbose "assistant" mode with multi-clause rationales that overflow max_tokens=160 and truncate the JSON. codex uses llm.generate(f"{system}\n\n{user}") = RAW completion -> terse rationales that close.
  2. max_model_len=2048 (mine) vs 4096 (codex); long personas ate into the generation budget.
- Fix (v10, commit 12f7e5b): build_prompts returns raw "system\n\nuser" strings; main() uses llm.generate + max_model_len=4096. Idea source: codex/scripts/p0_gate_throughput.py (representative_prompts appends f"{system}\n\n{user}"; llm.generate). Did not copy code.
- v10 validation (Qwen1.5B, job 5855597616380772352) = SUCCEEDED: valid_json_rate=1.0, decisions_per_hour=3782, 0 invalid_examples. G0 valid-JSON gate (>=90%) CLEARED for Qwen1.5B; throughput 3782 >> 2000.
- Full 4-model G0 run LAUNCHED (worker:v10), 4 INDEPENDENT jobs (not the serial launcher) so they parallelize if quota grants: Qwen1.5B=4250768036664967168, Qwen3B=688420731414904832, Phi-3.5=4890279183751577600, SmolLM2=500958396925607936. Background poll task b1es3xtl8. Each writes runs/g0_throughput/<model>.json.
- SHARED PROJECT: GCP project + GCS bucket are shared with the sibling 'codex' project. A codex P3 calibration job (4048387528410005504, scripts/p3_calibration_worker.py -- a script that does NOT exist in the claude repo) was RUNNING on the shared single T4 as of ~09:23Z. NOT launched by claude; left it alone. It holds the T4, so claude's g0 jobs queue behind it (user approved "queue behind codex").
- T4 QUOTA: per user request, filed Cloud Quotas preference agorasim-t4-spot-uscentral1 to raise CustomModelTrainingPreemptibleT4GPUsPerProjectPerRegion in us-central1 from 1 -> 4 (parallelism). State: reconciling (Google may auto-approve small spot bumps or route to review). If granted, the 4 g0 jobs run in parallel; if not, serial after codex.
- Cost: ~5 single-model T4 validation runs during the v7->v10 debug (~0.5-0.7 GPU-hr spot, ~$0.15-0.20) + upcoming 4-model run (~0.5 GPU-hr, ~$0.15). budget_est ~ $0.55 cumulative. Far under $85.
- Next: on ALL_G0_TERMINAL -> read 4 result JSONs -> docs/G0_THROUGHPUT.md -> GATE G0 decision + docs/FEASIBILITY_ADDENDUM.md (A-004).

## [2026-07-03T10:05:00Z] P0/A-003 -- GATE G0 (compute) PASS + SHUTDOWN CHECKPOINT
- SHUTDOWN-SAFE: local machine going down for hours. NO local key processes -- per R1 all heavy compute + LLM inference runs on Vertex (cloud), unaffected by local shutdown. All G0 Vertex jobs already reached SUCCEEDED before shutdown; results are durable in GCS. Local background poll tasks were watchers only -> safe to lose. Repo committed + pushed to github JulianAttemptsCoding/QTA1 branch 'claude'.
- FINAL G0 4-model results (worker:v11, T4 spot, n=512, guided decoding, ran in PARALLEL after T4 spot quota granted 1->4 in us-central1):
  - Qwen/Qwen2.5-1.5B-Instruct: valid_json_rate 1.0, 3885 dec/hr -> VIABLE
  - Qwen/Qwen2.5-3B-Instruct: valid_json_rate 1.0, 3034 dec/hr -> VIABLE
  - HuggingFaceTB/SmolLM2-1.7B-Instruct: valid_json_rate 0.9961 (2/512 invalid), 4859 dec/hr -> VIABLE
  - microsoft/Phi-3.5-mini-instruct: valid_json_rate 1.0, 1985 dec/hr -> MARGINAL (throughput 0.75% under the 2000 bar; kept optional/deprioritized)
- GATE G0 (compute) = PASS: 3/4 models clear both bars (valid-JSON >=0.90 AND thruput >=2000), valid-JSON fully solved (all >=0.996). Combined with G0 (data) PASS (docs/G0_REPORT.md) -> GATE G0 cleared. Wrote docs/G0_THROUGHPUT.md.
- Viable roster for the sim: Qwen2.5-1.5B, Qwen2.5-3B, SmolLM2-1.7B (spans size tiers for scaling/ablation arms). Phi-3.5 optional.
- Job ids (us-central1): Qwen1.5B 1439756609092845568, Qwen3B 6894741657745358848, Phi-3.5 4645193643873796096, SmolLM2 2339350634660102144 (all SUCCEEDED).
- SHARED PROJECT reminder: GCP project + bucket shared with sibling 'codex'. Codex jobs (agorasim-p3-*, scripts/p3_calibration_worker.py -- not in claude repo) may appear in `gcloud ai custom-jobs list` and use the shared T4 quota. Do NOT kill them.
- RESUME POINT (next session): A-004 = write docs/FEASIBILITY_ADDENDUM.md (synthesize G0 data+compute), git tag gate-g0, then begin P1: universe.py -> freeze universes -> snapshots + manifest + leakage checks -> GATE G1. See STATE.json next_task.

## [2026-07-04T00:00:00Z] P0->P1 -- A-004 done; P1 universes: OOS freeze now, CALIB deferred (Robintrack)
- A-004 (commit 5ff8280): folded measured G0 throughput (1985-4859 dec/hr, valid-JSON >=0.996) into FEASIBILITY.md; re-costed phase table at blended 3000/hr (~$90-100 full plan) with budget levers; noted gated->SmolLM2 roster swap. GATE G0 fully cleared (data + compute), tag gate-g0 pushed.
- P1 implementation (my own code; ideas only from codex/scripts/p1_freeze_universes.py per user rule):
  - src/agorasim/data/universe.py: was docstring-only; now the PURE ranking core (no network/pandas) -- frozen constants (CALIB 2019-06-28/2019-07..12; OOS selection 2024-12-20, window 2025-01-02..2026-06-30), zscore, cap/price/common-name filters, close_on_or_before (point-in-time), shares_outstanding_asof (SEC dei), dollar_volume_spike, rank_calib (holders/shares), rank_oos (z(news60)+z(dv_spike)+0.5*z(1/price)).
  - tests/test_universe.py: 14 unit tests (TDD) on the pure logic -> all green; full suite 30 passed.
  - scripts/p1_freeze_universes.py: I/O orchestration (Alpaca assets/bars/news + SEC companyfacts, cached under gitignored data/raw/), snapshot bars+news(+Robintrack for CALIB) to data/snapshots/g1/, SHA-256 manifest (docs/G1_SNAPSHOT_MANIFEST.json), leakage spot-check (docs/G1_LEAKAGE_SPOTCHECK.md), docs/G1_UNIVERSES.md. --track oos|calib|both.
- ROBINTRACK DECISION: robintrack.net is a defunct JS SPA; no working bulk-download URL found via quick probes (page/GitHub/bucket guesses). Per PLAN section 4 ("CONTINUE all non-Robintrack OOS work now; revisit Robintrack before P3") CALIB freeze is DEFERRED to P3-prep. Freezing OOS now (Alpaca+SEC only, fully unblocked -- this is the P4 prediction track, the scientifically-critical one). CALIB code is complete + tested, just needs the popularity_export CSVs at data/raw/robintrack/popularity_export/ then `--track calib`.
- GATE G1 will be a documented PARTIAL: OOS frozen + snapshot-hashed + leakage-PASS; CALIB code-complete/data-pending. Alpaca keys verified (5420 active common US-equity symbols). OOS freeze running now.

## [2026-07-04T13:25:00Z] P1 -- OOS universe FROZEN; GATE G1 (OOS) PASS
- Ran scripts/p1_freeze_universes.py --track oos against live Alpaca+SEC (5420 active common US-equity symbols scanned).
- OOS-2025 universe frozen (selection 2024-12-20, window 2025-01-02..2026-06-30), top 10 by z(news60)+z(dv_spike)+0.5*z(1/price) after price/cap/common filters: NVNI, TLRY, EDIT, CHPT, BLNK, FRSX, TPET, OGI, CCO, ICCM.
- CONVERGENCE CHECK: my independent implementation produced the SAME 10 tickers as codex's (docs cross-checked). Expected -- identical frozen rules + same public data + deterministic ranking. Validates correctness; not copying (my code is a separate pure-core + I/O design, 14 own unit tests).
- Snapshots: 20 files (10 tkr x bars_1d.jsonl + news.jsonl) in gitignored data/snapshots/g1/oos/, SHA-256'd into committed docs/G1_SNAPSHOT_MANIFEST.json, uploaded to gs://.../snapshots/g1/oos/ for Vertex P3/P4.
- Leakage spot-check (docs/G1_LEAKAGE_SPOTCHECK.md): 7 deterministic ticker/date renders via production prompt templates; every check post_asof=0 (max included bar == as-of, max news <= as-of). Result PASS (L-01 point-in-time enforced).
- GATE G1: OOS side COMPLETE (frozen + hashed + leakage PASS). CALIB side PENDING Robintrack (deferred per PLAN section 4). Not tagging gate-g1 as fully passed until CALIB frozen; OOS is sufficient to proceed with P2 (contamination probes + smoke run on OOS tickers) which is the next Vertex-heavy phase.
- Next: P2 agent bring-up (A-201/202/203) on OOS tickers, OR acquire Robintrack to close CALIB. Leaning P2 (OOS is the prediction track; Robintrack revisit stays scheduled for P3-prep).

## [2026-07-04T14:10:00Z] P2 -- GATE G2 PASS (real-model valid-JSON); SmolLM2 dropped
- A-201 (commit 7a052f6): guided decoding + T4 settings wired into production agents/vllm_batch.run_offline; canonical DECISION_JSON_SCHEMA in schemas.py shared with throughput_probe. A-203 (commit 93ea6d6): scripts/p2_gate_real_model.py + agents/sim_prompts.py (point-in-time L-01 request assembly, L-02 alias arm); 38 unit tests green.
- G2 smoke: 4 models x TLRY (frozen OOS), 20 personas x 10 point-in-time days = 200 real decisions each, guided decoding, worker:v12, run in PARALLEL (T4 spot, quota=4).
  - Qwen2.5-1.5B: valid 1.0 ; Qwen2.5-3B: valid 1.0 ; Phi-3.5-mini: valid 1.0 ; SmolLM2-1.7B: valid 0.96.
- GATE G2 = PASS: 2 model families (Qwen, Phi) at 1.0 valid-JSON >= 0.99. SmolLM2 DROPPED (8/200 invalid = genuine model-quality failures under guided decoding: negative qty, malformed object, and prompt regurgitation -- NOT prompt-fixable; declined to game the metric by coercing negative share counts).
- Post-G2 roster: Qwen2.5-1.5B (3885/hr), Qwen2.5-3B (3034/hr), Phi-3.5-mini (1985/hr, marginal thruput but 1.0 valid -> family diversity). docs/G2_REPORT.md written.
- C-1 contamination control satisfied by construction (OOS 2025-01-02.. strictly post every enabled-model cutoff). C-3 alias arm wired in sim_prompts. Next: A-202 C-2 recall probes -> exclusion matrix, then P4 OOS main run (RQ3). P3 CALIB still gated on Robintrack.

## [2026-07-04T14:40:00Z] P2 COMPLETE -- A-202 contamination: no exclusions
- Ran scripts/p2_contamination.py (worker:v13) for the roster (Qwen1.5B, Qwen3B, Phi-3.5) x 5 OOS tickers (TLRY,CHPT,NVNI,BLNK,OGI) x 10 post-cutoff dates x {named,alias} = 100 recall probes/model, 3 jobs in PARALLEL (spot; brief PENDING while codex held 1 T4, then scheduled).
- Result: named_recall = alias_recall = gap = 0.0 for EVERY (model,ticker). NO exclusions. docs/G2_CONTAMINATION.md written.
- Interpretation: models cannot recall these small caps' 2025-2026 closing prices -> OOS window is empirically post-cutoff (C-1 confirmed), no memorization (C-2), zero named-vs-alias advantage (C-3). Full roster proceeds to P4 on all 10 OOS tickers; alias arm primary for RQ3.
- P2 done (A-201 guided decoding in prod path; A-202 contamination; A-203 real-model smoke; GATE G2 PASS, tag gate-g2). Budget est ~$1.5 cumulative (many short spot T4 jobs), far under $85.
- NEXT = P4 OOS main (RQ3). Gap: scripts/run_sim_phase.py does NOT exist -- must build the sim-engine runner (agents x tickers x days -> run_offline -> parse -> market/clearing.py flow_imbalance + call_auction per day -> JSONL + RunManifest -> GCS). Then register trials (docs/TRIALS.md) and launch the Vertex OOS run. P3 CALIB still gated on Robintrack (revisit).

## [2026-07-05T00:00:00Z] P4 -- sim engine built + validated; host-OOM fixed; throughput finding
- Built the sim engine (commits fe5fc7d, 94bbb44): scripts/run_sim_phase.py = per-model Vertex worker (renders one model's sub-crowd over tickers x point-in-time days via sim_prompts, runs guided-decoding run_offline, ships tagged raw decisions + RunManifest to GCS; one model/job -> parallel). scripts/collect_sim_phase.py = CPU aggregator (pools every model's raw decisions per (ticker,day) -> flow_imbalance + call_auction -> signals.jsonl). 4 aggregation tests; 45 total green.
- BUG found by pilot v1 (oos-pilot-v1): host-RAM OOM ("Replicas low on memory") -- run_offline handed vLLM all ~1200 requests at once; scheduler queued every sequence + spilled KV to CPU swap, exhausting the ~30GiB n1-standard-8 host. FIX (94bbb44): feed 256 prompts/generate() call (was 2048) + swap_space=2. Pilot v2 (worker:v15) then ran without OOM (CPU blocks 9362->4681).
- THROUGHPUT finding (important for full P4): real prompts (~30 bars + 5 news ~= 900-1000 tok) are slow to prefill on T4 -- ~256 decisions per ~8 min, with minor KV preemption at max_model_len=4096 (only ~78 concurrent 4096-tok seqs fit the 8.5GiB KV cache). 1200 decisions/job ~= 40-60 min. At this rate the full P4 (250k decisions) is too slow/expensive. LEVERS for the full run: trim prompt (20 bars / 3 news), max_model_len 2048 (2x KV concurrency), chunk ~512 (G0 ran 512 in one batch with no OOM). Apply before launching the full OOS main run.
- Pilot v2 jobs (alias arm, run-id oos-pilot-v2): Qwen1.5B 3949756937351987200, Qwen3B 5179028529391599616, Phi 2524367655289225216. On completion: collect_sim_phase --run-id oos-pilot-v2 -> verify signals non-degenerate, then optimize + launch full P4.
- Budget est ~$2-3 cumulative (many short T4 jobs + the ~1hr pilot). Far under $85.

## [2026-07-05T00:20:00Z] P4 -- sim engine VALIDATED end-to-end (oos-pilot-v2 collected)
- All 3 pilot jobs SUCCEEDED (~45-60 min each; Qwen1.5B straggled, likely spot preempt). Collected via gcloud-cp + local aggregate (Python GCS client 403 on local ADC -- see collector_auth_note).
- RESULT: 3600 decisions, valid_rate 0.9994 (real-prompt >=99% confirmed at scale), 40 ticker-days (2 tkr x 20 d, ~90-agent crowd each). flow_imbalance non-degenerate: min -0.308, max +0.978, mean +0.523 (crowd net-bullish -> LLM optimism bias, a real herding finding for P5). call_auction crosses on all 40 days. signals.jsonl uploaded to gs://.../runs/oos-pilot-v2/. docs/P4_PILOT.md written.
- FINDINGS for the full P4 run: (1) throughput ~1900/hr on real ~900-tok prompts -> trim prompt (20 bars/3 news) + max_model_len 2048 + chunk ~512 before the 250k-decision run; (2) alias arm hides the ticker LABEL but news headlines still name the company (Phi rationale said 'tilray') -> named-vs-alias measures label memorization only (A-202 already showed 0 post-cutoff price recall, so RQ3 leakage risk low); (3) collector needs Vertex-side run or ADC login; (4) Git-Bash /tmp != Windows C:\tmp gotcha.
- Engine components all committed/tested (45 tests). This is a clean P4-validated checkpoint. NEXT: apply throughput levers, register RQ3 trials (docs/TRIALS.md), launch full OOS main run, then P5 stats (evals/prediction.py IC/DM/DSR + block bootstrap vs D-09 baselines). P3 CALIB still gated on Robintrack.
