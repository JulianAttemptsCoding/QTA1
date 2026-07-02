"""Vertex CPU job (P-17): download models from Hugging Face INSIDE Vertex and cache them
in GCS at {base}/models/<sanitized_id>/. Records the resolved commit SHA per model.

Gated repos the token cannot access are SKIPPED (not fatal) so the surviving ungated set
still caches (P-05). HF_TOKEN is read from the environment (set only on this job).

Run: python -m agorasim.infra.model_cache --base gs://BUCKET/agorasim --models a,b,c
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile

from huggingface_hub import HfApi, snapshot_download

from agorasim.infra.gcs import upload_dir, upload_file

# weights we never need for vLLM inference (save space + time)
IGNORE = ["*.pth", "*.msgpack", "*.h5", "original/*", "*.gguf", "*.onnx"]


def sanitize(model_id: str) -> str:
    return model_id.replace("/", "__")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="gs://BUCKET/agorasim")
    ap.add_argument("--models", required=True, help="comma-separated HF repo ids")
    args = ap.parse_args()

    token = os.getenv("HF_TOKEN") or None
    api = HfApi(token=token)
    results: dict[str, dict] = {}

    for mid in [m.strip() for m in args.models.split(",") if m.strip()]:
        rec: dict = {"model_id": mid}
        try:
            sha = api.model_info(mid).sha
            with tempfile.TemporaryDirectory() as td:
                snapshot_download(mid, local_dir=td, token=token,
                                  ignore_patterns=IGNORE)
                dest = f"{args.base}/models/{sanitize(mid)}"
                n = upload_dir(td, dest)
            rec.update(status="OK", revision=sha, files=n, gcs=dest)
        except Exception as e:  # noqa: BLE001 — gated/network failures are non-fatal
            rec.update(status="SKIP", error=f"{type(e).__name__}: {str(e)[:200]}")
        results[mid] = rec
        print("MODEL_REC", json.dumps(rec), flush=True)

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(results, tf, indent=2)
        tmp = tf.name
    upload_file(tmp, f"{args.base}/models/_cache_manifest.json")
    summary = {k: v["status"] for k, v in results.items()}
    print("MODEL_CACHE_DONE", json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
