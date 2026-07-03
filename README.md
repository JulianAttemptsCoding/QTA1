# AgoraSim

**A digital twin of a retail crowd.** Hundreds of small open-weight LLM agents,
spanning model families, personas, temperatures, and seeds, each read only
point-in-time public information about a retail-heavy small-cap stock and file one
buy/sell/hold decision per day. We test three registered questions: does the
simulated market look statistically real, does the simulated crowd move like the
measured Robinhood crowd did in Robintrack, and does simulated flow imbalance carry
incremental information about real next-day returns in a strictly
post-model-cutoff window? A clean null on prediction with positive realism or
fidelity is still the product: a validated retail-crowd simulator for event
studies and counterfactuals. Nothing here is investment advice.

## Status - gates

| Gate | Meaning | Status |
|---|---|---|
| G0 | Data + throughput reality checks (`scripts/p0_gate_*.py`) | **PASS** (`docs/G0_REPORT.md`, `docs/G0_THROUGHPUT.md`) |
| G1 | Universes + point-in-time snapshots frozen and hashed | not started |
| G2 | >=99% valid-JSON agent decisions; smoke sim | stub smoke PASS; real-model smoke pending |
| G3 | Calibration-era fidelity (kill: sign-agreement <=52% both arms) | not started |
| G4 | OOS budget checkpoint | not started |
| G5 | Full reproducibility from manifests | not started |

Local test suite: `pytest -q` - 26/26 passing. Stub smoke:
`python scripts/p2_smoke_sim.py --config configs/sim_smoke.yaml` - PASS
(parse-valid 0.995, auction price dynamics exercised).

## Quickstart

```bash
conda env create -f environment.yml && conda activate agorasim
pip install -e ".[dev]"
pytest -q
python scripts/p2_smoke_sim.py --config configs/sim_smoke.yaml
cp .env.example .env   # add Alpaca/FRED/GCP values as needed
python scripts/p0_gate_data.py
```

Heavy inference never runs locally. Build the worker image, push it to Artifact
Registry, and launch Vertex AI custom jobs on spot T4s through
`scripts/vertex_submit.py` / `src/agorasim/infra/vertex_launch.py`. Model weights
are downloaded and cached by Vertex jobs in GCS, not by the local workstation.

## Repo map

```text
PLAN.md                  phases P0-P6, gates, kill criteria, failure modes
DECISION_MEMO.md         why Idea 1 first; Idea 2 parked
FEASIBILITY.md           data audit and measured G0 compute/cost model
SOURCES.md               annotated bibliography
QC_AUDIT.md              10-pass pre-registration audit of this plan
docs/G0_REPORT.md        G0 data gate evidence
docs/G0_THROUGHPUT.md    G0 Vertex throughput evidence
docs/FEASIBILITY_ADDENDUM.md  G0 kill-criteria decision and budget update
docs/MODEL_SHAS.md       Vertex-cached model manifest and revisions
docs/TRIALS.md           registered trial count
configs/                 smoke / calibration / OOS experiment configs
prompts/                 agent system+user templates, contamination probes
src/agorasim/
  schemas.py             pydantic AgentDecision + robust LLM-JSON parsing
  agents/                persona bank, point-in-time prompt builder, vLLM harness
  market/                flow-imbalance signal + uniform-price call auction
  evals/                 stylized facts, IC / DM / Deflated Sharpe, contamination
  data/                  Alpaca bars+news, Robintrack, universe rules
  infra/                 run manifests, Vertex launcher
scripts/                 gate G0 checks, Vertex submitter, smoke sim
tests/                   unit tests for schemas, auction, stats, infra, gates
```

## Honest expectations

RQ3 prediction will most likely be null or tiny. The plan is built so the project
can still succeed as a proof of concept on realism and behavioral fidelity, and so
a null RQ3 is a credible, well-controlled measurement rather than an absence of
evidence.
