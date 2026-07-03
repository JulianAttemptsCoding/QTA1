# PLAN.md - AgoraSim (Idea 1: LLM-agent retail crowd simulation)

Status: G0 PASS. Data and throughput reports are in `docs/`; P1 may begin.

## 0. Objective (30-second version)

Build a "digital twin" of a retail crowd: hundreds of heterogeneous, small,
open-weight LLM agents, each given only point-in-time public information about a
retail-heavy small-cap stock, each making one buy/sell/hold decision per day.
Test three registered research questions:

- **RQ1 Realism** — does the endogenous simulated market (agents + call auction)
  reproduce the standard stylized facts of returns (heavy tails, volatility
  clustering, no raw autocorrelation, volume–volatility correlation)?
- **RQ2 Behavioral fidelity** — in the 2018–2020 Robintrack era, does simulated
  aggregate agent flow track the *sign and relative magnitude* of measured
  Robinhood holder-count changes around news and price moves?
- **RQ3 Incremental information** — in a strictly post-model-cutoff window, does
  simulated flow imbalance add predictive information about real next-day returns
  over strong cheap baselines (single strong LLM on the same inputs, momentum,
  AR(1), logistic on the same features)?

A clean **null on RQ3 with positive RQ1/RQ2 is still a fundable proof of concept**
(a validated retail-crowd simulator is useful for scenario analysis, event studies,
and counterfactuals even if it prints no alpha). RQ3 positive at small effect size
would be the stretch outcome. This document assumes neither.

## 1. Non-goals and honesty box

- Not expected: deployable alpha, "beating SPY", or anything tradeable. Documented
  LLM return predictability (Lopez-Lira & Tang) is small, decays with adoption, and
  concentrates in hard-to-trade small caps; our small models are weaker than the
  models in that literature.
- Not built: live trading, order routing, anything touching real money.
- Not a claim: that simulated agents "are" retail investors. Claims are limited to
  measured realism/fidelity/information metrics.
- Nothing in this repo is investment advice.

## 2. Hard constraints

| ID  | Constraint | Consequence |
|-----|------------|-------------|
| K-1 | All heavy compute on Vertex AI (T4, spot preferred) | vLLM lives only in the worker image; local = tests + smoke |
| K-2 | Free/public data only (Alpaca free, FRED, SEC EDGAR, Robintrack archive) | No TAQ, no paid retail-flow feeds; retail proxies are rule-based |
| K-3 | Novelty from the idea, not the execution | Component whitelist: vLLM, pydantic schemas, uniform-price call auction, Cont-style stylized facts, IC/DM/DSR. Anything "clever" is out of scope |
| K-4 | Single GCP billing account | Multi-account free-credit farming violates Google Cloud ToS and is excluded from all budget math. Legit expansions: GCP research credits program, academic credits, TPU Research Cloud |
| K-5 | Budget ≈ $100 credits | Every phase has a cost line and a kill criterion (Section 4) |

## 3. Locked design decisions

| ID   | Decision | Rationale |
|------|----------|-----------|
| D-01 | Two-track market layer: `flow_imbalance` (prediction signal) and `call_auction` (realism track). The simulated price never needs to track the real price. | Conflating the two is the classic failure of "simulate the market to predict it". RQ3 tests information in flow, not sim-price tracking. |
| D-02 | Daily decision frequency (one decision/agent/ticker/day). | Minute frequency is compute-infeasible on budget (Section 6) and small caps on free feeds are sparse intraday. Hourly is a stretch goal after G4. |
| D-03 | Crowd unit = N agents per ticker (agents do not span tickers). | Matches the retail attention model; keeps prompts short and per-ticker flow interpretable. |
| D-04 | Post-cutoff OOS window: starts strictly after max(training cutoff) across all models used; concrete dates frozen at G1. | Look-ahead/memorization is the #1 validity threat for LLM backtests (Glasserman & Lin 2023; memorization literature). |
| D-05 | Robintrack era (2018-05→2020-08) used ONLY for RQ2 calibration/fidelity, never for return-prediction claims. | That era is inside every candidate model's training data. |
| D-06 | Anonymization A/B in every experiment arm (named vs stable alias for ticker/company). | Separates reasoning from memorization; quantifies contamination instead of assuming it away. |
| D-07 | Agent diversity = model family × persona × temperature × seed. **MC-dropout is dropped.** | Inference stacks (vLLM) run with dropout disabled; enabling it is nonstandard hackery, which violates K-3 and adds no proven diversity benefit over temperature/persona mixing. |
| D-08 | Models: 1.5B–4B instruct models (Qwen2.5-1.5B/3B, Llama-3.2-3B, Phi-3.5-mini, Gemma-2-2B), fp16 or 4-bit, on T4-16GB. Cutoffs verified from model cards at G0. | "Good enough for basic logic" per project spec; fits T4; multiple families for diversity. |
| D-09 | Baselines (mandatory): (a) single strong-ish LLM sentiment score on identical inputs, (b) momentum 1/5/20d, (c) AR(1), (d) logistic regression on engineered features of the same inputs. | The crowd must beat the *single-model* baseline to claim the crowd matters at all — this is the core scientific control. |
| D-10 | Universe rules frozen before any inference (`src/agorasim/data/universe.py`); OOS tickers selected point-in-time; delistings retained. | Survivorship and selection-after-peeking are the cheap ways to fool ourselves. |
| D-11 | Every trained/evaluated configuration is a registered trial in `docs/TRIALS.md`; DSR computed against the registered count. | Same discipline as GMDA/TACTIC-MoB; prevents backtest-overfitting theater. |
| D-12 | Raw agent outputs (every token) logged as JSONL and synced to GCS; run invalid without a manifest. | Backup-first; enables post-hoc audits of rationales, herding, entropy. |

## 4. Phases, gates, kill criteria

### P0 — Environment and reality checks (local + one tiny Vertex job) — est. $1–3
- A-001 DONE: Fill `.env` from `.env.example`; run `make test` (must stay green).
- A-002 DONE: Run `scripts/p0_gate_data.py` with real keys → `docs/G0_REPORT.md`.
  Must record: which Alpaca `feed` values the free keys accept for *historical* bars;
  earliest minute/daily bar for one liquid + one small-cap ticker; Alpaca news
  earliest date; Robintrack archive row counts; EDGAR/FRED reachability.
- A-003 DONE: Build worker image (python 3.11 + vllm) → Artifact Registry; launch one spot
  T4 job running `scripts/p0_gate_throughput.py` → `docs/G0_THROUGHPUT.md`
  (tokens/s, decisions/hour, valid-JSON rate per model).
- A-004 DONE: Update FEASIBILITY.md cost table with measured numbers.
- **GATE G0 (kill criteria):** any of — no workable historical bar feed for small
  caps; news history unusable; measured throughput < 2,000 decisions/hour on the
  best model; valid-JSON rate < 90% even after one prompt iteration → STOP, write
  postmortem, reconsider scope before spending further.

### P1 — Universes and point-in-time datasets — est. $0 (CPU)
- A-101 CALIB-2019 universe per rules U-C1..U-C4 (10 tickers, selection 2019-06-28).
- A-102 OOS universe per U-O1..U-O3; freeze exact retail-proxy formula and the OOS
  window start date (must be > max model cutoff from G0) in a signed commit.
- A-103 Snapshot bars + news + Robintrack per ticker into `data/snapshots/`,
  SHA-256 each file, record in a snapshot manifest.
- **GATE G1:** both universes frozen; every snapshot hashed; a leakage spot-check
  (10 random prompts rendered, human-verified no post-asof content) passes.

### P2 — Agent + engine bring-up — est. $2–5
- A-201 Prompt iteration on the worker until valid-JSON ≥ 99% per model (log every
  iteration; prompts are hashed into manifests).
- A-202 Contamination probes (C-2) per model × OOS ticker → exclusion matrix.
- A-203 `make smoke` (already passing with the stub) rerun against real models on a
  20-agent × 10-day slice of one CALIB ticker.
- **GATE G2 (kill):** valid-JSON < 99% after 3 prompt iterations on ≥ 2 model
  families → drop failing families; if < 2 families survive, STOP.

### P3 — Calibration era (RQ1 + RQ2) — est. $10–18
- A-301 Run CALIB-2019: 10 tickers × 100 agents × ~126 trading days × {named, alias}
  ≈ 252k decisions.
- A-302 Stylized-fact report on auction-track paths (RQ1).
- A-303 Fidelity: corr and sign-agreement of daily sim imbalance vs Robintrack
  Δholders; event-window plots around top news days (RQ2).
- A-304 Named-vs-alias gap quantified → contamination writeup.
- **GATE G3 (kill):** RQ2 sign agreement ≤ 52% in BOTH arms AND stylized facts
  qualitatively absent → the crowd is noise; STOP and publish the negative result
  writeup instead of burning P4 budget.

### P4 — OOS experiments (RQ3) — est. $30–45
- A-401 Main run: 10 tickers × 200 agents × ~125 trading days (extend to 250 only if
  budget allows) with agents stratified across surviving model families; alias arm
  only (named arm optional at 2 tickers for reporting).
- A-402 Scaling curve: 2 tickers × N ∈ {50, 100, 300, 1000} × 60 days.
- A-403 Ablations: news-off, personas-off (2 tickers × 100 × 60 each); baselines D-09
  computed over the identical window.
- **GATE G4:** budget checkpoint at 50% of P4 spend — if spend/decision exceeds the
  G0-measured rate by >30%, pause and re-plan.

### P5 — Statistics and writeup inputs — est. $0 (CPU)
- A-501 IC, hit rate, DM vs each baseline, per-ticker and pooled; block bootstrap CIs.
- A-502 DSR against registered trial count (docs/TRIALS.md).
- A-503 Herding/entropy diagnostics (decision entropy per day; F-06).
- **GATE G5:** every reported number reproducible from manifests by a clean rerun of
  the stats scripts on the archived JSONL.

### P6 — PoC packaging — est. $0
- A-601 Results report (ICAIF-style structure) + investor one-pager + demo notebook
  replaying one meme-y event window with agent rationales.
- A-602 Public repo hygiene pass (no keys, no raw redistributable data).

## 5. Leakage controls
- L-01 Prompts contain only information timestamped strictly before the decision
  timestamp (enforced in `prompt_builder`, spot-checked at G1).
- L-02 Alias mode replaces ticker/company with a stable random string.
- L-03 Prompts never contain evaluation targets or post-asof data.
- L-04 OOS ticker list frozen before any OOS inference; commit hash recorded.

## 6. Compute model (planning numbers — replaced by G0 measurements)
- Prompt ≈ 900 tokens in / ≤ 160 out. Planning throughput on one spot T4 with a
  1.5–3B model under vLLM: **~5,000 decisions/hour** (conservative; measure at G0).
- Spot n1-standard-8 + T4 planning price ≈ **$0.30/hour** (on-demand fallback ≈ $0.75).
- Decision budget: P2 ≈ 5k; P3 ≈ 252k; P4 ≈ 250k (main) + 174k (scaling) + 24k
  (ablations) ⇒ ≈ 705k decisions ≈ 141 T4-hours ≈ **$42 spot** + P0/P2 jobs + 30%
  contingency ⇒ **≈ $60–75 total**, inside the $100 envelope. If G0 measures ≤ half
  the planning throughput, cut OOS to 5 tickers before cutting days.

## 7. Failure modes
| ID | Failure | Mitigation |
|----|---------|------------|
| F-01 | Spot preemption mid-run | request_id ledger + chunked JSONL sync (agents/vllm_batch.py); rerun is idempotent |
| F-02 | Partial output loss | GCS sync every chunk; a lost chunk ≤ 2048 decisions |
| F-03 | Small-cap bars sparse on IEX-only feed | G0 feed matrix; prefer delayed-SIP historical; if unavailable, restrict universe to names with ≥95% daily bar coverage |
| F-04 | News API history too shallow | fall back to EDGAR 8-K/press-release text for the event feed; decided at G0 |
| F-05 | Model card cutoff wrong/undocumented | C-2 recall probes are the operative test; cards are advisory |
| F-06 | Degenerate consensus (all agents same answer → zero-variance signal) | decision-entropy metric; if median daily entropy < threshold, raise temperature/persona spread; report as a finding, not a bug |
| F-07 | Cost overrun | G4 checkpoint; per-run cost printed from job metadata |
| F-08 | Robintrack ticker mismatches / dual-class gaps | follow Welch-style cleaning; drop unmatched tickers at U-C stage |

## 8. Reproducibility spec
Every run: `RunManifest` (config SHA, persona bank hash, prompt hashes, model IDs,
seed, data snapshot hashes) written before launch; raw generations JSONL; stats
scripts pure functions of archived artifacts. GCS layout:
`gs://<bucket>/agorasim/{snapshots,runs/<run_id>/{manifest,requests,outputs,stats}}`.

## 9. Notes for Claude Code / IDE agents executing this plan
Each task A-xxx should be run with a self-contained prompt that includes: this file's
relevant section, the exact input/output paths, the gate criteria, and the failure
modes table. Backup-first: never overwrite a snapshot or run directory; new run_id
per attempt. Expected outputs and PASS/FAIL conditions are stated per gate above; do
not proceed past a failing gate.
