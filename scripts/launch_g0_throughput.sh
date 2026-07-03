#!/usr/bin/env bash
# GATE G0 (compute) launcher: submit ONE throughput-probe Vertex job per cached model.
# Serial (T4 quota == 1). Reads the set of successfully-cached models from the GCS cache
# manifest so gated models that model_cache skipped are not probed. No secrets: the probe
# loads weights from the GCS cache written by model_cache (P-17); no HF_TOKEN needed.
#
# Usage:
#   scripts/launch_g0_throughput.sh <BASE_GS> <IMAGE_URI> [N]
# Example:
#   scripts/launch_g0_throughput.sh \
#     gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim \
#     us-central1-docker.pkg.dev/project-c779f701-1a49-4a58-b54/agorasim/worker:v1 512
set -euo pipefail

BASE="${1:?BASE_GS required}"
IMAGE="${2:?IMAGE_URI required}"
N="${3:-512}"
REGION="us-central1"

# Model dirs under {BASE}/models/ each hold a sanitized model id (org__name). Recover the
# original id by turning the first '__' back into '/'.
mapfile -t DIRS < <(gcloud storage ls "${BASE}/models/" | sed -E 's#/$##; s#.*/##' | grep -v '^$')

for SAN in "${DIRS[@]}"; do
  MODEL="${SAN/__//}"
  echo "=== throughput probe: ${MODEL} (dir ${SAN}) ==="
  YAML="$(mktemp)"
  cat > "$YAML" <<EOF
workerPoolSpecs:
  machineSpec:
    machineType: n1-standard-8
    acceleratorType: NVIDIA_TESLA_T4
    acceleratorCount: 1
  replicaCount: 1
  diskSpec:
    bootDiskType: pd-ssd
    bootDiskSizeGb: 200
  containerSpec:
    imageUri: ${IMAGE}
    command: ["python", "-m", "agorasim.infra.throughput_probe"]
    args: ["--base", "${BASE}", "--model", "${MODEL}", "--n", "${N}"]
scheduling:
  strategy: SPOT
EOF
  NAME="$(gcloud ai custom-jobs create --region="${REGION}" \
      --display-name="agorasim-g0-thru-${SAN}" --config="$YAML" \
      --format='value(name)' 2>/dev/null | tail -1)"
  rm -f "$YAML"
  echo "submitted: ${NAME}"
  # Serial: wait for terminal state before next model (T4 quota == 1).
  while true; do
    S="$(gcloud ai custom-jobs describe "${NAME}" --region="${REGION}" --format='value(state)')"
    case "$S" in
      *SUCCEEDED*) echo "done: ${MODEL} -> ${S}"; break;;
      *FAILED*|*CANCELLED*|*EXPIRED*) echo "FAIL: ${MODEL} -> ${S}"; break;;
    esac
    sleep 90
  done
done
echo "ALL_THROUGHPUT_JOBS_DONE"
