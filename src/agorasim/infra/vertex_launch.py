"""Vertex AI custom-job launcher.

Uses the REST API instead of `gcloud ai custom-jobs create` for submission so we
can set `jobSpec.scheduling.strategy = SPOT`, which is documented by Google but
not exposed in the installed gcloud worker-pool shorthand.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests


TERMINAL_STATES = {
    "JOB_STATE_SUCCEEDED",
    "JOB_STATE_FAILED",
    "JOB_STATE_CANCELLED",
    "JOB_STATE_EXPIRED",
}


@dataclass(frozen=True)
class VertexJobSpec:
    project: str
    region: str
    display_name: str
    image_uri: str
    args: list[str]
    machine_type: str = "n1-standard-8"
    accelerator_type: str = "NVIDIA_TESLA_T4"
    accelerator_count: int = 1
    replica_count: int = 1
    boot_disk_size_gb: int = 100
    boot_disk_type: str = "pd-ssd"
    spot: bool = True
    env: dict[str, str] = field(default_factory=dict)
    gcloud_configuration: str | None = "agorasim-new"

    def request_body(self, redact_env: bool = False) -> dict[str, Any]:
        env = [
            {"name": name, "value": "<redacted>" if redact_env else value}
            for name, value in sorted(self.env.items())
        ]
        job_spec: dict[str, Any] = {
            "workerPoolSpecs": [
                {
                    "machineSpec": {
                        "machineType": self.machine_type,
                        "acceleratorType": self.accelerator_type,
                        "acceleratorCount": self.accelerator_count,
                    },
                    "replicaCount": self.replica_count,
                    "diskSpec": {
                        "bootDiskType": self.boot_disk_type,
                        "bootDiskSizeGb": self.boot_disk_size_gb,
                    },
                    "containerSpec": {
                        "imageUri": self.image_uri,
                        "args": self.args,
                        "env": env,
                    },
                }
            ]
        }
        if self.spot:
            job_spec["scheduling"] = {"strategy": "SPOT", "restartJobOnWorkerRestart": False}
        return {"displayName": self.display_name, "jobSpec": job_spec}


def access_token(configuration: str | None = None) -> str:
    gcloud = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not gcloud:
        raise FileNotFoundError("Could not find gcloud/gcloud.cmd on PATH.")
    command = [gcloud, "auth", "print-access-token"]
    if configuration:
        command.append(f"--configuration={configuration}")
    return subprocess.check_output(
        command,
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def api_url(project: str, region: str, suffix: str = "customJobs") -> str:
    return f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/{suffix}"


def submit(spec: VertexJobSpec, request_log_path: Path | None = None) -> dict[str, Any]:
    if request_log_path:
        request_log_path.parent.mkdir(parents=True, exist_ok=True)
        request_log_path.write_text(json.dumps(spec.request_body(redact_env=True), indent=2, sort_keys=True))
    response = requests.post(
        api_url(spec.project, spec.region),
        headers={
            "Authorization": f"Bearer {access_token(spec.gcloud_configuration)}",
            "Content-Type": "application/json; charset=utf-8",
        },
        data=json.dumps(spec.request_body()),
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def describe(project: str, region: str, job_name: str, configuration: str | None = "agorasim-new") -> dict[str, Any]:
    response = requests.get(
        api_url(project, region, f"customJobs/{job_name.split('/')[-1]}"),
        headers={"Authorization": f"Bearer {access_token(configuration)}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def poll(
    project: str,
    region: str,
    job_name: str,
    interval_s: int = 120,
    configuration: str | None = "agorasim-new",
) -> dict[str, Any]:
    while True:
        payload = describe(project, region, job_name, configuration=configuration)
        state = payload.get("state")
        print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {job_name} {state}", flush=True)
        if state in TERMINAL_STATES:
            return payload
        time.sleep(interval_s)
