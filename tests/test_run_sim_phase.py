import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_sim_phase.py"
SPEC = importlib.util.spec_from_file_location("run_sim_phase", SCRIPT)
run_sim_phase = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = run_sim_phase
SPEC.loader.exec_module(run_sim_phase)


def test_run_id_for_uses_config_root_ticker_arm_attempt():
    config = {"run_id": "calib-2019-g1"}
    assert run_sim_phase.run_id_for(config, "IIPR", "alias", "v2") == "calib-2019-g1-iipr-alias-v2"


def test_snapshot_hashes_for_ticker_filters_kind_and_ticker():
    manifest = {
        "files": [
            {"path": "data/snapshots/g1/calib/IIPR/bars_1d.jsonl", "sha256": "a"},
            {"path": "data/snapshots/g1/calib/IIPR/news.jsonl", "sha256": "b"},
            {"path": "data/snapshots/g1/oos/IIPR/bars_1d.jsonl", "sha256": "c"},
            {"path": "data/snapshots/g1/calib/BLNK/bars_1d.jsonl", "sha256": "d"},
        ]
    }
    hashes = run_sim_phase.snapshot_hashes_for_ticker(manifest, "calib", "IIPR")
    assert hashes == {
        "data/snapshots/g1/calib/IIPR/bars_1d.jsonl": "a",
        "data/snapshots/g1/calib/IIPR/news.jsonl": "b",
    }


def test_build_calib_spec_contains_worker_args(tmp_path):
    args = type("Args", (), {})()
    args.ticker = "IIPR"
    args.arm = "named"
    args.gcs_model_root = "gs://bucket/models"
    args.run_salt = "salt"
    args.chunk_size = 512
    args.max_new_tokens = 160
    args.model_ids = ["Qwen/Qwen2.5-1.5B-Instruct", "microsoft/Phi-3.5-mini-instruct"]
    args.temperatures = [0.7, 1.0]
    args.gpu_memory_utilization = 0.85
    args.enforce_eager = True
    args.project = "project"
    args.region = "us-central1"
    args.display_name = None
    args.image_uri = "image"
    args.on_demand = False
    args.attempt = "v1"
    config = {
        "gcs_snapshot_manifest": "gs://bucket/manifest.json",
        "agents": {"n": 100, "persona_seed": 1337},
        "window": {"start": "2019-07-01", "end": "2019-12-31"},
    }

    spec = run_sim_phase.build_calib_spec(args, config, "run", "gs://bucket/runs/run")
    body = spec.request_body(redact_env=True)
    container_args = body["jobSpec"]["workerPoolSpecs"][0]["containerSpec"]["args"]

    assert container_args[:2] == ["scripts/p3_calibration_worker.py", "--run-id"]
    assert container_args.count("--model-id") == 2
    assert "--enforce-eager" in container_args
    assert json.dumps(body)


def test_build_oos_spec_contains_worker_args():
    args = type("Args", (), {})()
    args.ticker = "NVNI"
    args.arm = "alias"
    args.gcs_model_root = "gs://bucket/models"
    args.run_salt = "salt"
    args.n_agents = None
    args.chunk_size = 128
    args.max_new_tokens = 160
    args.model_ids = ["Qwen/Qwen2.5-1.5B-Instruct", "microsoft/Phi-3.5-mini-instruct"]
    args.temperatures = [0.7, 1.0]
    args.gpu_memory_utilization = 0.85
    args.enforce_eager = True
    args.project = "project"
    args.region = "us-central1"
    args.display_name = None
    args.image_uri = "image"
    args.on_demand = False
    args.attempt = "v1"
    config = {
        "gcs_snapshot_manifest": "gs://bucket/manifest.json",
        "agents": {"n": 200, "persona_seed": 1337},
        "window": {"start": "2025-01-02", "end": "2025-07-03"},
    }

    spec = run_sim_phase.build_oos_spec(args, config, "run", "gs://bucket/runs/run")
    body = spec.request_body(redact_env=True)
    container_args = body["jobSpec"]["workerPoolSpecs"][0]["containerSpec"]["args"]

    assert container_args[:2] == ["scripts/p4_oos_worker.py", "--run-id"]
    assert container_args[container_args.index("--n-agents") + 1] == "200"
    assert container_args[container_args.index("--end") + 1] == "2025-07-03"
    assert "--enforce-eager" in container_args
