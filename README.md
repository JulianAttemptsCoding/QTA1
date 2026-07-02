# AgoraSim

**A digital twin of a retail crowd.** Hundreds of small open-weight LLM agents —
different model families, personas, temperatures — each read only point-in-time
public information about a retail-heavy small-cap stock and file one buy/sell/hold
decision per day. We test three registered questions: does the simulated market
look statistically real (stylized facts)? does the simulated crowd move like the
*measured* Robinhood crowd did (Robintrack, 2018–20)? and does simulated flow
imbalance carry any incremental information about real next-day returns in a
strictly post-model-cutoff window, against baselines including a single strong LLM
on identical inputs? A clean null on prediction with positive realism/fidelity is
still the product: a validated retail-crowd simulator for event studies and
counterfactuals. Nothing here is investment advice.

## Status — gates

| Gate | Meaning | Status |
|---|---|---|
| G0 | Data + throughput reality checks (`scripts/p0_gate_*.py`) | **NOT RUN — blocks everything** |
| G1 | Universes + point-in-time snapshots frozen and hashed | not started |
| G2 | ≥99% valid-JSON agent decisions; smoke sim | **stub smoke PASS** (real-model smoke pending) |
| G3 | Calibration-era fidelity (kill: sign-agreement ≤52% both arms) | not started |
| G4 | OOS budget checkpoint | not started |
| G5 | Full reproducibility from manifests | not started |

Local test suite: `pytest` — 14/14 passing. Stub smoke: `make smoke` — PASS
(parse-valid 0.995, auction price dynamics exercised).

## Quickstart

```bash
conda env create -f environment.yml && conda activate agorasim
pip install -e ".[dev]"
make test          # unit tests, no network
make smoke         # end-to-end tiny sim with a stub model, no GPU/network
cp .env.example .env   # add Alpaca keys, GCP project
make gate-data     # GATE G0 part 1 (requires real keys; currently intentionally failing)
```

Heavy inference never runs locally: build the worker image (python 3.11 + vllm),
push to Artifact Registry, launch Vertex custom jobs on spot T4s
(`src/agorasim/infra/vertex_launch.py`). Runs are resume-safe via the request-id
ledger in `src/agorasim/agents/vllm_batch.py`.

## Repo map

```
PLAN.md                  phases P0–P6, gates, kill criteria, failure modes  ← start here
DECISION_MEMO.md         why Idea 1 first; Idea 2 parked (+ its falsification protocol)
FEASIBILITY.md           data audit, model shortlist, cost model (~$60–75 of $100)
SOURCES.md               annotated bibliography (24 entries)
QC_AUDIT.md              10-pass pre-registration audit of this plan
docs/TRIALS.md           registered trial count (feeds Deflated Sharpe)
docs/IDEA2_FALSIFICATION.md  cheap CPU protocol Idea 2 must pass to be revived
configs/                 smoke / calibration-2019 / OOS experiment configs
prompts/                 agent system+user templates, contamination probes
src/agorasim/
  schemas.py             pydantic AgentDecision + robust LLM-JSON parsing
  agents/                persona bank, point-in-time prompt builder, vLLM harness
  market/                flow-imbalance signal + uniform-price call auction
  evals/                 stylized facts, IC / DM / Deflated Sharpe, contamination
  data/                  Alpaca bars+news, Robintrack, universe rules
  infra/                 run manifests, Vertex launcher
scripts/                 gate G0 checks, smoke sim
tests/                   14 unit tests (schemas, auction, stats, reproducibility)
```

## Honest expectations

RQ3 (prediction) will most likely be a null or a tiny, untradeable effect — the
literature that finds LLM text-based predictability finds it small and
concentrated in hard-to-trade names, and our agents are 1.5–3B models. The plan is
built so the project succeeds as a PoC on RQ1+RQ2 regardless, and so a null RQ3 is
a credible, well-controlled measurement rather than an absence of evidence.
