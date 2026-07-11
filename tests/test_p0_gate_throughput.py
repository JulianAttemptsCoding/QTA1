import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p0_gate_throughput.py"
SPEC = importlib.util.spec_from_file_location("p0_gate_throughput", SCRIPT)
p0_gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = p0_gate
SPEC.loader.exec_module(p0_gate)


def test_relative_blob_path_keeps_downloads_under_local_model_dir():
    prefix = "agorasim/models/Qwen--Qwen2.5-1.5B-Instruct/"
    blob_name = "agorasim/models/Qwen--Qwen2.5-1.5B-Instruct/config.json"

    rel = p0_gate.relative_blob_path(blob_name, prefix)

    assert rel == "config.json"
    assert not rel.startswith("/")


def test_relative_blob_path_handles_nested_cache_files():
    prefix = "agorasim/models/Qwen--Qwen2.5-1.5B-Instruct"
    blob_name = "agorasim/models/Qwen--Qwen2.5-1.5B-Instruct/.cache/huggingface/CACHEDIR.TAG"

    assert p0_gate.relative_blob_path(blob_name, prefix) == ".cache/huggingface/CACHEDIR.TAG"


def test_manifest_model_uri_prefers_ok_gcs_entry():
    manifest = {
        "HuggingFaceTB/SmolLM2-1.7B-Instruct": {
            "status": "OK",
            "gcs": "gs://bucket/models/HuggingFaceTB__SmolLM2-1.7B-Instruct",
        },
        "meta-llama/Llama-3.2-3B-Instruct": {"status": "SKIP"},
    }

    assert p0_gate.manifest_model_uri(manifest, "HuggingFaceTB/SmolLM2-1.7B-Instruct").endswith("__SmolLM2-1.7B-Instruct")
    assert p0_gate.manifest_model_uri(manifest, "meta-llama/Llama-3.2-3B-Instruct") is None


def test_decision_guided_schema_matches_parser_requirements():
    schema = p0_gate.DECISION_JSON_SCHEMA

    assert set(schema["required"]) == {"action", "order_type", "qty", "limit_price", "confidence", "horizon_days", "rationale"}
    assert schema["properties"]["action"]["enum"] == ["buy", "sell", "hold"]
    assert schema["properties"]["horizon_days"]["enum"] == list(range(1, 31))
    assert schema["properties"]["limit_price"]["minimum"] == 0


def test_safe_model_id_matches_model_cache_manifest_convention():
    assert p0_gate.safe_model_id("Qwen/Qwen2.5-1.5B-Instruct") == "Qwen__Qwen2.5-1.5B-Instruct"
