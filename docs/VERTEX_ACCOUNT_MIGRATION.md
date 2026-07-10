# Vertex Account Migration Runbook

Target account: `jjjsresearch@gmail.com`  
Target project: `project-82d97cf9-5889-43a4-850`  
Region: `us-central1`

## Current State

- The old CLI account is `juliansjuan08@gmail.com`.
- The old project is `project-c779f701-1a49-4a58-b54`.
- The old bucket is `gs://project-c779f701-1a49-4a58-b54-agorasim`.
- The new gcloud configuration has been created locally as `agorasim-new`.
- The new account is not authenticated locally yet, so the transfer cannot complete until the user signs in.

## One User Step Required

Run this exact command in PowerShell and complete the browser login as `jjjsresearch@gmail.com`:

```powershell
gcloud auth login jjjsresearch@gmail.com --configuration=agorasim-new --update-adc
```

Then rerun:

```powershell
.\scripts\migrate_vertex_project.ps1
```

## What The Script Does

1. Verifies/sets the separate `agorasim-new` gcloud configuration.
2. Enables required APIs in the new project.
3. Creates `gs://project-82d97cf9-5889-43a4-850-agorasim` if needed.
4. Creates the `agorasim` Artifact Registry Docker repository if needed.
5. Grants `jjjsresearch@gmail.com` read access to the old bucket.
6. Copies all preserved artifacts:
   - snapshots
   - model weight cache
   - P0/P2/P3/P4 run artifacts
   - completed P4 halfway outputs
7. Rewrites the copied snapshot manifest and model cache manifest so Vertex workers read from the new bucket.
8. Grants the new project's runtime service accounts access to the new bucket and worker image.
9. Builds and pushes the worker image to:

```text
us-central1-docker.pkg.dev/project-82d97cf9-5889-43a4-850/agorasim/worker:latest
```

10. Updates local launch defaults so all future Vertex jobs use the new project/bucket/image.

## Post-Migration Verification

Run:

```powershell
python -m pytest -q
gcloud storage ls gs://project-82d97cf9-5889-43a4-850-agorasim/agorasim/snapshots/g1/manifest.json --configuration=agorasim-new
gcloud storage ls gs://project-82d97cf9-5889-43a4-850-agorasim/agorasim/models/_cache_manifest.json --configuration=agorasim-new
gcloud artifacts docker images list us-central1-docker.pkg.dev/project-82d97cf9-5889-43a4-850/agorasim --project=project-82d97cf9-5889-43a4-850 --configuration=agorasim-new
```

## Continuing P4 After Migration

Do not launch until G4 is documented. Once ready, the remaining main OOS jobs should use the new defaults:

```powershell
python scripts\run_sim_phase.py --project project-82d97cf9-5889-43a4-850 --image-uri us-central1-docker.pkg.dev/project-82d97cf9-5889-43a4-850/agorasim/worker:latest launch-oos-main --ticker FRSX --arm alias --attempt v1 --chunk-size 128 --gpu-memory-utilization 0.85 --enforce-eager
```

Repeat for `TPET`, `OGI`, `CCO`, and `ICCM`.

The already-completed P4 halfway outputs remain preserved and copied; they must not be rerun unless a validation failure is found.
