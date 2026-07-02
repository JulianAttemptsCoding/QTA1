"""Minimal GCS helpers used INSIDE Vertex worker jobs (never needed locally).

google-cloud-storage is installed only in the worker image; importing this module
locally will fail on the `from google.cloud import storage` line — that is intentional.
"""
from __future__ import annotations

from pathlib import Path

from google.cloud import storage  # worker-image dependency


def _split(uri: str) -> tuple[str, str]:
    assert uri.startswith("gs://"), f"not a gs uri: {uri}"
    bucket, _, prefix = uri[len("gs://"):].partition("/")
    return bucket, prefix.strip("/")


def upload_dir(local_dir: str, gcs_uri: str) -> int:
    bucket_name, prefix = _split(gcs_uri)
    bucket = storage.Client().bucket(bucket_name)
    root = Path(local_dir)
    n = 0
    for f in root.rglob("*"):
        if f.is_file():
            rel = f.relative_to(root).as_posix()
            bucket.blob(f"{prefix}/{rel}").upload_from_filename(str(f))
            n += 1
    return n


def download_prefix(gcs_uri: str, local_dir: str) -> int:
    bucket_name, prefix = _split(gcs_uri)
    bucket = storage.Client().bucket(bucket_name)
    root = Path(local_dir)
    root.mkdir(parents=True, exist_ok=True)
    n = 0
    for blob in bucket.list_blobs(prefix=prefix + "/"):
        rel = blob.name[len(prefix) + 1:]
        if not rel:
            continue
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(dst))
        n += 1
    return n


def upload_file(local_path: str, gcs_uri: str) -> None:
    bucket_name, prefix = _split(gcs_uri)
    storage.Client().bucket(bucket_name).blob(prefix).upload_from_filename(str(local_path))
