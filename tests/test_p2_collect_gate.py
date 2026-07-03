import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p2_collect_gate.py"
SPEC = importlib.util.spec_from_file_location("p2_collect_gate", SCRIPT)
p2_collect = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = p2_collect
SPEC.loader.exec_module(p2_collect)


def row(model_id, valid=1.0, recall=0.0, valid_pass=True, recall_pass=True):
    return {
        "model_id": model_id,
        "passes_valid_json": valid_pass,
        "passes_contamination": recall_pass,
        "smoke": {"n_prompts": 200, "valid_json_rate": valid, "path": [{"auction_price": 1, "flow_imbalance": 0.2}]},
        "contamination": {"max_non_unknown_rate": recall},
    }


def test_gate_status_requires_two_surviving_families():
    rows = [
        row("Qwen/Qwen2.5-1.5B-Instruct"),
        row("Qwen/Qwen2.5-3B-Instruct"),
    ]
    assert p2_collect.gate_status(rows)[0] == "FAIL"
    rows.append(row("microsoft/Phi-3.5-mini-instruct"))
    assert p2_collect.gate_status(rows)[0] == "PASS"


def test_load_rows_sorts_json_files(tmp_path):
    (tmp_path / "b.json").write_text(json.dumps(row("microsoft/Phi-3.5-mini-instruct")))
    (tmp_path / "a.json").write_text(json.dumps(row("Qwen/Qwen2.5-1.5B-Instruct")))
    rows = p2_collect.load_rows(tmp_path)
    assert [r["model_id"] for r in rows] == ["Qwen/Qwen2.5-1.5B-Instruct", "microsoft/Phi-3.5-mini-instruct"]
