# Vertex AI — general notes (condensed from old vertex/ folder)

Heavy compute (GPU/large-CPU: neural-expert HPO, multi-seed training, CPCV path sweeps) runs on
Vertex AI custom-jobs. Light work (ingestion, diagnostics, accounting, report building) runs
locally.

## Config pattern

Config read from `configs/v1.yaml[vertex]` via a `VertexConfig` loader, env-overridable
(`.env` / `load_dotenv()`). Typical fields:

| key | example |
|-----|---------|
| project_id | `project-c779f701-1a49-4a58-b54` |
| region | `us-central1` |
| account | (gcloud auth account email) |
| bucket | `gs://<bucket>-uscentral1` |
| fallback bucket | `gs://<bucket>-uscentral1-<user>` |
| machine (full) | `n1-standard-16` |
| machine (smoke) | `n1-standard-4` |
| image cpu/smoke | `us-docker.pkg.dev/vertex-ai/training/xgboost-cpu.2-1:latest` |
| image gpu | `us-docker.pkg.dev/vertex-ai/training/pytorch-xla.2-4.py310:latest` |

## One-time auth

```
gcloud auth login <account>
gcloud config set project <project_id>
gcloud config set ai/region <region>
```

## Submit pattern (generic job)

Build sdist -> upload to `gs://<bucket>/packages/` -> `gcloud ai custom-jobs create` with
`--worker-pool-spec=machine-type=...,replica-count=1,executor-image-uri=...,python-module=...`.

```
python -m pip install -q build
python -m build --sdist --outdir vertex/dist   # or wherever
gcloud storage cp <sdist> gs://<bucket>/packages/<name>.tar.gz

gcloud ai custom-jobs create \
  --region=<region> --project=<project_id> \
  --display-name=<name> \
  --python-package-uris=gs://<bucket>/packages/<name>.tar.gz \
  --worker-pool-spec=machine-type=<machine>,replica-count=1,executor-image-uri=<image>,python-module=<entry_module> \
  --args=<comma-separated key=value list>
```

- `--smoke` flag pattern: use small machine (`n1-standard-4`) + cpu image for quick sanity job.
- `--gpu` flag pattern: switch to pytorch-xla GPU image for full/heavy job.
- No Docker build needed for the default path — prebuilt Google images + sdist. Dockerfile only
  needed if extra system deps required (`FROM <base image>`, `pip install .`, custom entrypoint).

## Data/training job pattern

For jobs needing an input panel (parquet files etc.):
1. Upload local data dir -> `gs://<bucket>/repo_inputs/<run_id>/` (skip if reusing `--data_uri`).
2. Upload config yaml alongside data.
3. Build+upload sdist -> `gs://<bucket>/packages/`.
4. Submit custom job with `--args=--data_uri=...,--out_uri=gs://<bucket>/runs/<run_id>,...`.
5. Artifacts land at `gs://<bucket>/runs/<run_id>/`.
6. Poll: `gcloud ai custom-jobs list --region=<region> --project=<project_id> --filter='displayName:<prefix>*' --format="json(displayName,state,name)"`.
   Terminal states: `JOB_STATE_SUCCEEDED/FAILED/CANCELLED/EXPIRED`. Loop with cooldown until all
   matched jobs terminal.
7. After success, download run dir locally (`gcloud storage cp gs://<bucket>/runs/<run_id>/... local/`)
   and do light post-processing (aggregation, report build) locally — don't do that on Vertex.

## Sharded/parallel jobs

Can shard a big sweep (e.g. CV folds) across multiple custom-jobs sharing one `--run_id` /
`--data_uri`, each job handling a fold range (`--fold_start/--fold_end`), all writing under the
same `gs://<bucket>/runs/<run_id>/` prefix. Stagger launches if queue priority matters (launch
next batch only after previous batch confirmed RUNNING).

## Vizier HPO spec pattern

`vizier_spec.yaml`-style config for hyperparam search:
```yaml
displayName: <study-name>
studySpec:
  algorithm: ALGORITHM_UNSPECIFIED   # Vizier default Bayesian/GP
  metrics:
    - metricId: <metric>
      goal: MINIMIZE   # or MAXIMIZE
  parameters:
    - parameterId: <name>
      doubleValueSpec: { minValue: ..., maxValue: ... }
      scaleType: UNIT_LOG_SCALE   # or UNIT_LINEAR_SCALE
    - parameterId: <name>
      discreteValueSpec: { values: [...] }
```
Cap trial budget per sweep; log each trial to a local/central registry for tracking.

## Key lessons / gotchas

- On Windows, shell out with `shell=True` and quote args containing spaces/backslashes — gcloud/
  gsutil ship as `.cmd` shims that need shell resolution.
- Separate "submit" step (cheap, fast, on Vertex) from "finish/report" step (heavy local
  aggregation + plotting) — don't run report-building on Vertex compute.
- Support a `--data_uri` passthrough to skip re-uploading panel data when resubmitting/sharding
  against already-uploaded data.
