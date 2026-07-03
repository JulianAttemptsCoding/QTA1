import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p0_collect_throughput.py"
SPEC = importlib.util.spec_from_file_location("p0_collect_throughput", SCRIPT)
p0_collect = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = p0_collect
SPEC.loader.exec_module(p0_collect)


def test_gate_status_requires_best_throughput_and_valid_json():
    rows = [
        {"model_id": "a", "decisions_per_hour": 2500, "valid_json_rate": 0.95},
        {"model_id": "b", "decisions_per_hour": 1800, "valid_json_rate": 0.91},
    ]
    assert p0_collect.gate_status(rows)[0] == "PASS"
    assert p0_collect.gate_status([{"decisions_per_hour": 1999, "valid_json_rate": 0.99}])[0] == "FAIL"
    assert p0_collect.gate_status([{"decisions_per_hour": 3000, "valid_json_rate": 0.89}])[0] == "FAIL"


def test_render_report_contains_models():
    text = p0_collect.render_report([
        {"model_id": "m", "n_prompts": 512, "elapsed_seconds": 10, "decisions_per_hour": 184320, "valid_json_rate": 1.0}
    ])
    assert "G0 Throughput" in text
    assert "| m | 512 |" in text
