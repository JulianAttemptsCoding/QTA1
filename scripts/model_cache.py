"""Vertex-only model cache job.

Downloads configured Hugging Face model snapshots inside Vertex, uploads them to
GCS, and writes MODEL_SHAS.md. Do not run locally: it downloads LLM weights.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import yaml
from google.cloud import storage
from huggingface_hub import HfApi, snapshot_download


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOW = [
    "*.json",
    "*.model",
    "*.safetensors",
    "*.txt",
    "*.py",
    "tokenizer.*",
    "chat_template*",
]
DEFAULT_IGNORE = ["original/*", "*.gguf", "*.onnx", "*.h5", "*.msgpack"]


def safe_model_id(model_id: str) -> str:
    return model_id.replace("/", "__")


def parse_gs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"Expected gs:// URI, got {uri}")
    bucket, _, prefix = uri[5:].partition("/")
    return bucket, prefix.strip("/")


def upload_dir(local_dir: Path, gcs_uri: str) -> None:
    bucket_name, prefix = parse_gs_uri(gcs_uri)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    for path in local_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(local_dir).as_posix()
            blob = bucket.blob(f"{prefix}/{rel}" if prefix else rel)
            blob.upload_from_filename(path)


def upload_file(path: Path, gcs_uri: str) -> None:
    bucket_name, prefix = parse_gs_uri(gcs_uri)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    bucket.blob(prefix).upload_from_filename(path)


def configured_models(config_path: Path, include_gated: bool) -> list[str]:
    data = yaml.safe_load(config_path.read_text())
    models = []
    for item in data.get("models", []):
        if item.get("enabled", True) is False:
            continue
        if item.get("requires_hf_token") and not include_gated:
            continue
        models.append(item["id"])
    return models


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/models.yaml")
    parser.add_argument("--gcs-model-root", required=True)
    parser.add_argument("--gcs-sha-uri", required=True)
    parser.add_argument("--local-root", default="/tmp/agorasim-models")
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN")
    models = configured_models(Path(args.config), include_gated=bool(token))
    api = HfApi(token=token)
    local_root = Path(args.local_root)
    local_root.mkdir(parents=True, exist_ok=True)

    lines = [
        "# MODEL_SHAS.md",
        "",
        "| Model | Revision SHA | GCS URI |",
        "|---|---|---|",
    ]
    for model_id in models:
        safe_id = safe_model_id(model_id)
        local_dir = local_root / safe_id
        info = api.model_info(model_id, token=token)
        snapshot_download(
            repo_id=model_id,
            token=token,
            local_dir=local_dir,
            allow_patterns=DEFAULT_ALLOW,
            ignore_patterns=DEFAULT_IGNORE,
        )
        gcs_uri = f"{args.gcs_model_root.rstrip('/')}/{safe_id}"
        upload_dir(local_dir, gcs_uri)
        lines.append(f"| {model_id} | {info.sha} | {gcs_uri} |")
        print(f"CACHED {model_id} {info.sha} {gcs_uri}", flush=True)

    sha_path = Path("/tmp/MODEL_SHAS.md")
    sha_path.write_text("\n".join(lines) + "\n")
    upload_file(sha_path, args.gcs_sha_uri)
    print(f"WROTE {args.gcs_sha_uri}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
