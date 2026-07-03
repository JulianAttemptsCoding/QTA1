"""Local orchestration for simulation phases.

This script does not run model inference. It writes the required pre-launch run
manifest, uploads that manifest to GCS, and submits a Vertex AI custom job that
does the heavy work.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agorasim.agents import PersonaBank
from agorasim.agents.prompt_builder import load_template, prompt_hash
from agorasim.infra import RunManifest
from agorasim.infra.vertex_launch import VertexJobSpec, submit


DEFAULT_SURVIVORS = ["Qwen/Qwen2.5-1.5B-Instruct", "microsoft/Phi-3.5-mini-instruct"]
DEFAULT_TEMPERATURES = [0.7, 1.0]
DEFAULT_GCS_RUN_ROOT = "gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/runs"
DEFAULT_GCS_MODEL_ROOT = "gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/models"


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_float_csv(value: str) -> list[float]:
    return [float(item) for item in parse_csv_list(value)]


def run_id_for(config: dict[str, Any], ticker: str, arm: str, attempt: str) -> str:
    root = str(config["run_id"]).replace("_", "-")
    return f"{root}-{ticker.lower()}-{arm}-{attempt}"


def snapshot_hashes_for_ticker(snapshot_manifest: dict[str, Any], kind: str, ticker: str) -> dict[str, str]:
    needle = f"/{kind}/{ticker}/"
    hashes = {}
    for row in snapshot_manifest["files"]:
        normalized = row["path"].replace("\\", "/")
        if needle in normalized:
            hashes[normalized] = row["sha256"]
    if not hashes:
        raise KeyError(f"No snapshot hashes found for {kind}/{ticker}")
    return hashes


def upload_file(local_path: Path, gcs_uri: str) -> None:
    gcloud = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not gcloud:
        raise FileNotFoundError("Could not find gcloud/gcloud.cmd on PATH.")
    subprocess.run([gcloud, "storage", "cp", str(local_path), gcs_uri], check=True)


def build_manifest(
    *,
    run_id: str,
    config_path: Path,
    model_ids: list[str],
    n_agents: int,
    persona_seed: int,
    snapshot_manifest_path: Path,
    ticker: str,
    arm: str,
) -> RunManifest:
    snapshot_manifest = json.loads(snapshot_manifest_path.read_text())
    bank = PersonaBank(n_agents, seed=persona_seed)
    prompt_hashes = {
        "agent_system.j2": prompt_hash(load_template("agent_system.j2")),
        "decision_user.j2": prompt_hash(load_template("decision_user.j2")),
    }
    data_hashes = snapshot_hashes_for_ticker(snapshot_manifest, "calib", ticker)
    return RunManifest.create(
        run_id,
        "P3",
        config_path,
        persona_bank_hash=bank.content_hash(),
        prompt_hashes=prompt_hashes,
        model_ids=model_ids,
        seed=persona_seed,
        data_snapshot_hashes=data_hashes,
        notes=f"P3 calibration {ticker} {arm}; manifest written before Vertex launch.",
    )


def build_calib_spec(args: argparse.Namespace, config: dict[str, Any], run_id: str, gcs_output_dir: str) -> VertexJobSpec:
    agents = config["agents"]
    window = config["window"]
    container_args = [
        "scripts/p3_calibration_worker.py",
        "--run-id",
        run_id,
        "--ticker",
        args.ticker,
        "--arm",
        args.arm,
        "--gcs-output-dir",
        gcs_output_dir,
        "--gcs-model-root",
        args.gcs_model_root,
        "--gcs-snapshot-manifest",
        config["gcs_snapshot_manifest"],
        "--n-agents",
        str(int(agents["n"])),
        "--persona-seed",
        str(int(agents["persona_seed"])),
        "--start",
        str(window["start"]),
        "--end",
        str(window["end"]),
        "--run-salt",
        args.run_salt,
        "--chunk-size",
        str(args.chunk_size),
        "--max-new-tokens",
        str(args.max_new_tokens),
    ]
    for model_id in args.model_ids:
        container_args.extend(["--model-id", model_id])
    for temperature in args.temperatures:
        container_args.extend(["--temperature", str(temperature)])
    if args.gpu_memory_utilization is not None:
        container_args.extend(["--gpu-memory-utilization", str(args.gpu_memory_utilization)])
    if args.enforce_eager:
        container_args.append("--enforce-eager")
    return VertexJobSpec(
        project=args.project,
        region=args.region,
        display_name=args.display_name or f"agorasim-p3-{args.ticker.lower()}-{args.arm}-{args.attempt}",
        image_uri=args.image_uri,
        args=container_args,
        spot=not args.on_demand,
    )


def launch_calib(args: argparse.Namespace) -> dict[str, Any]:
    config_path = Path(args.config)
    config = load_yaml(config_path)
    if args.ticker not in config["universe"]["tickers"]:
        raise ValueError(f"{args.ticker} is not in {config_path}")
    run_id = run_id_for(config, args.ticker, args.arm, args.attempt)
    gcs_output_dir = f"{args.gcs_run_root.rstrip('/')}/p3/{run_id}"
    local_dir = Path("runs") / run_id
    manifest = build_manifest(
        run_id=run_id,
        config_path=config_path,
        model_ids=args.model_ids,
        n_agents=int(config["agents"]["n"]),
        persona_seed=int(config["agents"]["persona_seed"]),
        snapshot_manifest_path=Path(config["snapshot_manifest"]),
        ticker=args.ticker,
        arm=args.arm,
    )
    manifest_path = manifest.write(local_dir)
    spec = build_calib_spec(args, config, run_id, gcs_output_dir)
    request_log = Path("docs") / "vertex_job_specs" / f"{spec.display_name}.json"
    if args.dry_run:
        request_log.parent.mkdir(parents=True, exist_ok=True)
        request_log.write_text(json.dumps(spec.request_body(redact_env=True), indent=2, sort_keys=True))
        return {
            "dry_run": True,
            "run_id": run_id,
            "gcs_output_dir": gcs_output_dir,
            "manifest": str(manifest_path),
            "request_log": str(request_log),
        }
    upload_file(manifest_path, f"{gcs_output_dir}/manifest.json")
    result = submit(spec, request_log)
    return {
        "run_id": run_id,
        "gcs_output_dir": gcs_output_dir,
        "manifest": str(manifest_path),
        "request_log": str(request_log),
        "job": result["name"],
        "state": result.get("state"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="project-c779f701-1a49-4a58-b54")
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--image-uri", required=True)
    parser.add_argument("--gcs-run-root", default=DEFAULT_GCS_RUN_ROOT)
    parser.add_argument("--gcs-model-root", default=DEFAULT_GCS_MODEL_ROOT)
    parser.add_argument("--on-demand", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    sub = parser.add_subparsers(dest="kind", required=True)
    calib = sub.add_parser("launch-calib")
    calib.add_argument("--config", default="configs/sim_calib_2019.yaml")
    calib.add_argument("--ticker", required=True)
    calib.add_argument("--arm", choices=["named", "alias"], required=True)
    calib.add_argument("--attempt", default="v1")
    calib.add_argument("--display-name")
    calib.add_argument("--model-ids", type=parse_csv_list, default=DEFAULT_SURVIVORS)
    calib.add_argument("--temperatures", type=parse_float_csv, default=DEFAULT_TEMPERATURES)
    calib.add_argument("--run-salt", default="calib-2019-v1")
    calib.add_argument("--chunk-size", type=int, default=512)
    calib.add_argument("--max-new-tokens", type=int, default=160)
    calib.add_argument("--gpu-memory-utilization", type=float)
    calib.add_argument("--enforce-eager", action="store_true")
    args = parser.parse_args()

    if args.kind == "launch-calib":
        print(json.dumps(launch_calib(args), sort_keys=True), flush=True)
        return 0
    raise ValueError(args.kind)


if __name__ == "__main__":
    raise SystemExit(main())
