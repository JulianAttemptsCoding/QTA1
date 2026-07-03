import json
import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p1_freeze_universes.py"
SPEC = importlib.util.spec_from_file_location("p1_freeze_universes", SCRIPT)
p1 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = p1
SPEC.loader.exec_module(p1)


def test_shares_outstanding_asof_uses_latest_before_cutoff():
    facts = {
        "facts": {
            "dei": {
                "EntityCommonStockSharesOutstanding": {
                    "units": {
                        "shares": [
                            {"end": "2024-01-01", "filed": "2024-01-15", "val": 100},
                            {"end": "2024-06-30", "filed": "2024-07-15", "val": 200},
                            {"end": "2025-01-01", "filed": "2025-01-15", "val": 300},
                        ]
                    }
                }
            }
        }
    }
    assert p1.shares_outstanding_asof(facts, "2024-12-20") == 200


def test_zscore_constant_values_are_zero():
    assert p1.zscore({"A": 1.0, "B": 1.0}) == {"A": 0.0, "B": 0.0}


def test_close_on_or_before_selects_latest_available_bar():
    bars = [
        {"t": "2024-12-19T05:00:00Z", "c": 9.5},
        {"t": "2024-12-20T05:00:00Z", "c": 10.0},
        {"t": "2024-12-23T05:00:00Z", "c": 11.0},
    ]
    price, bar = p1.close_on_or_before(bars, "2024-12-20")
    assert price == 10.0
    assert bar["t"].startswith("2024-12-20")


def test_build_manifest_hashes_files(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    snap = root / "data" / "snapshots" / "g1"
    path = snap / "calib" / "ABC" / "bars_1d.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text('{"t":"2025-01-01"}\n')
    monkeypatch.setattr(p1, "ROOT", root)
    monkeypatch.setattr(p1, "SNAPSHOT_ROOT", snap)
    manifest = p1.build_manifest([path], "gs://bucket/agorasim/snapshots/g1")
    assert manifest["files"][0]["path"] == "data/snapshots/g1/calib/ABC/bars_1d.jsonl"
    assert manifest["files"][0]["gcs_uri"] == "gs://bucket/agorasim/snapshots/g1/calib/ABC/bars_1d.jsonl"
    assert len(manifest["files"][0]["sha256"]) == 64


def test_write_jsonl_round_trip(tmp_path):
    path = tmp_path / "rows.jsonl"
    p1.write_jsonl(path, [{"b": 2, "a": 1}])
    assert json.loads(path.read_text()) == {"a": 1, "b": 2}
