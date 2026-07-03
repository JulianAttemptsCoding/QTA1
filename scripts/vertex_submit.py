"""Submit AgoraSim Vertex jobs with redacted request-spec logging."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agorasim.infra.vertex_launch import VertexJobSpec, poll, submit


def append_note(notes_path: Path, text: str) -> None:
    with notes_path.open("a", encoding="utf-8") as fh:
        fh.write(text.rstrip() + "\n")


def common_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--image-uri", required=True)
    parser.add_argument("--machine-type", default="n1-standard-8")
    parser.add_argument("--accelerator-type", default="NVIDIA_TESLA_T4")
    parser.add_argument("--accelerator-count", type=int, default=1)
    parser.add_argument("--boot-disk-size-gb", type=int, default=100)
    parser.add_argument("--on-demand", action="store_true", help="Disable SPOT scheduling.")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=120)
    parser.add_argument("--notes-path", default="notes.md")
    parser.add_argument("--request-log-dir", default="docs/vertex_job_specs")
    sub = parser.add_subparsers(dest="kind", required=True)

    cache = sub.add_parser("model-cache")
    cache.add_argument("--display-name", default="agorasim-p0-model-cache")
    cache.add_argument("--gcs-model-root", required=True)
    cache.add_argument("--gcs-sha-uri", required=True)

    throughput = sub.add_parser("throughput")
    throughput.add_argument("--display-name", required=True)
    throughput.add_argument("--model-id", required=True)
    throughput.add_argument("--gcs-model-root", required=True)
    throughput.add_argument("--gcs-output-uri", required=True)
    throughput.add_argument("--n-prompts", type=int, default=512)
    throughput.add_argument("--gpu-memory-utilization", type=float)
    throughput.add_argument("--enforce-eager", action="store_true")

    p2 = sub.add_parser("p2-gate")
    p2.add_argument("--display-name", required=True)
    p2.add_argument("--model-id", required=True)
    p2.add_argument("--gcs-model-root", required=True)
    p2.add_argument("--gcs-snapshot-manifest", required=True)
    p2.add_argument("--gcs-output-uri", required=True)
    p2.add_argument("--ticker", default="IIPR")
    p2.add_argument("--n-agents", type=int, default=20)
    p2.add_argument("--n-days", type=int, default=10)
    p2.add_argument("--gpu-memory-utilization", type=float)
    p2.add_argument("--enforce-eager", action="store_true")
    return parser


def main() -> int:
    args = common_parser().parse_args()
    if args.kind == "model-cache":
        container_args = [
            "scripts/model_cache.py",
            "--gcs-model-root",
            args.gcs_model_root,
            "--gcs-sha-uri",
            args.gcs_sha_uri,
        ]
        env = {}
        if os.getenv("HF_TOKEN"):
            env["HF_TOKEN"] = os.environ["HF_TOKEN"]
        display_name = args.display_name
    elif args.kind == "throughput":
        container_args = [
            "scripts/p0_gate_throughput.py",
            "--model-id",
            args.model_id,
            "--gcs-model-root",
            args.gcs_model_root,
            "--gcs-output-uri",
            args.gcs_output_uri,
            "--n-prompts",
            str(args.n_prompts),
        ]
        if args.gpu_memory_utilization is not None:
            container_args.extend(["--gpu-memory-utilization", str(args.gpu_memory_utilization)])
        if args.enforce_eager:
            container_args.append("--enforce-eager")
        env = {}
        display_name = args.display_name
    else:
        container_args = [
            "scripts/p2_gate_real_model.py",
            "--model-id",
            args.model_id,
            "--gcs-model-root",
            args.gcs_model_root,
            "--gcs-snapshot-manifest",
            args.gcs_snapshot_manifest,
            "--gcs-output-uri",
            args.gcs_output_uri,
            "--ticker",
            args.ticker,
            "--n-agents",
            str(args.n_agents),
            "--n-days",
            str(args.n_days),
        ]
        if args.gpu_memory_utilization is not None:
            container_args.extend(["--gpu-memory-utilization", str(args.gpu_memory_utilization)])
        if args.enforce_eager:
            container_args.append("--enforce-eager")
        env = {}
        display_name = args.display_name

    spec = VertexJobSpec(
        project=args.project,
        region=args.region,
        display_name=display_name,
        image_uri=args.image_uri,
        args=container_args,
        machine_type=args.machine_type,
        accelerator_type=args.accelerator_type,
        accelerator_count=args.accelerator_count,
        boot_disk_size_gb=args.boot_disk_size_gb,
        spot=not args.on_demand,
        env=env,
    )
    request_log = Path(args.request_log_dir) / f"{display_name}.json"
    response = submit(spec, request_log_path=request_log)
    print(json.dumps({"name": response.get("name"), "state": response.get("state"), "request_log": str(request_log)}, sort_keys=True))
    if args.wait:
        final = poll(args.project, args.region, response["name"], interval_s=args.poll_seconds)
        append_note(
            Path(args.notes_path),
            f"## [{final.get('endTime', 'UNKNOWN')}] P0/VERTEX-POLL\n"
            f"- Job `{response['name']}` reached `{final.get('state')}`.\n"
            f"- Display name: `{display_name}`.\n"
            f"- Redacted request spec: `{request_log}`.",
        )
        print(json.dumps({"name": response.get("name"), "final_state": final.get("state")}, sort_keys=True))
        return 0 if final.get("state") == "JOB_STATE_SUCCEEDED" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
