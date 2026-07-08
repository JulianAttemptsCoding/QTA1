import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p4_gate_budget.py"
SPEC = importlib.util.spec_from_file_location("p4_gate_budget", SCRIPT)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = gate
SPEC.loader.exec_module(gate)


def summary(requests: int, elapsed_seconds: float):
    return {
        "n_requests": requests,
        "n_outputs": requests,
        "elapsed_seconds": elapsed_seconds,
    }


def test_g4_passes_at_g0_rate():
    result = gate.evaluate_g4([summary(4747, 3600)])

    assert result["decision"] == "PASS"
    assert abs(result["overrun_fraction"]) < 1e-12


def test_g4_pauses_above_thirty_percent():
    result = gate.evaluate_g4([summary(4747, 4681)])

    assert result["decision"] == "PAUSE_REPLAN"
    assert result["overrun_fraction"] > 0.30


def test_g4_tracks_incomplete_outputs():
    row = summary(100, 100)
    row["n_outputs"] = 99

    result = gate.evaluate_g4([row])

    assert result["complete"] is False
