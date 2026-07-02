"""Vertex AI custom-job launcher SKELETON (heavy compute lives here per project rule).

Intended shape (verify flags against current gcloud docs at P0; do not trust from memory):

  gcloud ai custom-jobs create \
    --region=us-central1 \
    --display-name=agorasim-<phase>-<run_id> \
    --worker-pool-spec=machine-type=n1-standard-8,accelerator-type=NVIDIA_TESLA_T4,\
accelerator-count=1,replica-count=1,container-image-uri=<REGION>-docker.pkg.dev/<PROJECT>/agorasim/worker:latest

Policies:
- Spot/preemptible where offered; jobs are resume-safe (see agents/vllm_batch.py ledger).
- Every job downloads its manifest + inputs from GCS, appends outputs as JSONL chunks,
  and syncs to GCS at least every chunk (F-02).
- One GCP project, one billing account. Do NOT farm free-trial credits across multiple
  accounts: it violates Google Cloud ToS. Legitimate expansions: GCP research credits,
  academic programs, TPU Research Cloud (vLLM has TPU support).
"""
