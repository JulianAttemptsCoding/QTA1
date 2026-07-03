import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p2_gate_real_model.py"
SPEC = importlib.util.spec_from_file_location("p2_gate_real_model", SCRIPT)
p2_gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = p2_gate
SPEC.loader.exec_module(p2_gate)


def test_summarize_probes_accepts_unknown_variants():
    rows = [
        {"ticker": "NVNI", "probe_idx": "0"},
        {"ticker": "NVNI", "probe_idx": "1"},
        {"ticker": "TLRY", "probe_idx": "0"},
    ]
    raw = [
        "UNKNOWN.",
        "Answer: UNKNOWN\n\nQuestion repeated by model",
        "The close was 12.34.",
    ]

    summary = p2_gate.summarize_probes(rows, raw)

    by_ticker = {row["ticker"]: row["non_unknown_rate"] for row in summary["per_ticker"]}
    assert by_ticker["NVNI"] == 0.0
    assert by_ticker["TLRY"] == 1.0
    assert summary["max_non_unknown_rate"] == 1.0
