import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p0_gate_data.py"
SPEC = importlib.util.spec_from_file_location("p0_gate_data", SCRIPT)
p0_gate_data = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = p0_gate_data
SPEC.loader.exec_module(p0_gate_data)


def test_load_dotenv_strips_quotes_without_overriding(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('A="one two"\nB=three\n')
    monkeypatch.setenv("B", "already")
    loaded = p0_gate_data.load_dotenv(env)
    assert loaded == {"A": "one two", "B": "three"}
    assert p0_gate_data.os.environ["A"] == "one two"
    assert p0_gate_data.os.environ["B"] == "already"


def test_markdown_table_uses_union_of_keys():
    rows = [{"a": 1}, {"b": 2}]
    table = p0_gate_data.markdown_table(rows)
    assert table[0] == "| a | b |"
    assert "| 1 |  |" in table
    assert "|  | 2 |" in table


def test_soft_blocker_is_not_hard_failure():
    result = p0_gate_data.CheckResult("robintrack_archive", "SOFT_BLOCKER", "missing")
    assert not result.hard_failed
