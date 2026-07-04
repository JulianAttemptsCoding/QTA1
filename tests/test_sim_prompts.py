"""Unit tests for point-in-time request assembly (leakage L-01, alias stability L-02)."""
import datetime as dt
import json

from agorasim.agents.sim_prompts import (
    build_requests, point_in_time_blocks, stable_alias,
)
from agorasim.data.universe import parse_date


def _write_snapshot(tmp_path, n_bars=40):
    d = tmp_path / "TEST"
    d.mkdir()
    start = dt.date(2025, 2, 1)
    bars = [{"t": f"{(start + dt.timedelta(days=i)).isoformat()}T00:00:00Z", "o": 1.0,
             "h": 1.1, "l": 0.9, "c": 1.0 + i * 0.01, "v": 1000 + i} for i in range(n_bars)]
    # one news item on each of two days, plus one AFTER the window to prove it is excluded
    news = [{"created_at": "2025-02-05T12:00:00Z", "headline": "early"},
            {"created_at": "2025-02-20T12:00:00Z", "headline": "mid"},
            {"created_at": "2025-12-31T12:00:00Z", "headline": "future-leak"}]
    (d / "bars_1d.jsonl").write_text("\n".join(json.dumps(b) for b in bars))
    (d / "news.jsonl").write_text("\n".join(json.dumps(n) for n in news))
    return d


def test_stable_alias_deterministic_and_unlinkable():
    assert stable_alias("TLRY") == stable_alias("TLRY")
    assert stable_alias("TLRY") != stable_alias("NVNI")
    assert "TLRY" not in stable_alias("TLRY")


def test_point_in_time_blocks_no_lookahead():
    bars = [{"t": f"2025-02-{d:02d}T00:00:00Z", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1} for d in range(1, 11)]
    news = [{"created_at": "2025-02-03T00:00:00Z", "headline": "ok"},
            {"created_at": "2025-02-28T00:00:00Z", "headline": "leak"}]
    bblock, nblock, incl = point_in_time_blocks(bars, news, "2025-02-05")
    assert "2025-02-05" in bblock and "2025-02-06" not in bblock
    assert "ok" in nblock and "leak" not in nblock
    assert all(parse_date(b["t"]) <= parse_date("2025-02-05") for b in incl)


def test_build_requests_count_and_ids(tmp_path):
    d = _write_snapshot(tmp_path)
    reqs = build_requests("TEST", d, n_agents=5, days=4, arm="named")
    assert len(reqs) == 5 * 4
    assert all(r["request_id"].startswith("TEST-named-") for r in reqs)
    assert {r["sampling"]["temperature"] for r in reqs} <= {0.7, 1.0}


def test_build_requests_is_leakage_free(tmp_path):
    d = _write_snapshot(tmp_path)
    reqs = build_requests("TEST", d, n_agents=2, days=3, arm="named")
    for r in reqs:
        asof = "-".join(r["request_id"].split("-")[2:5])
        cutoff = parse_date(asof)
        assert "future-leak" not in r["prompt"]
        for line in r["prompt"].splitlines():
            if len(line) >= 10 and line[:4].isdigit() and line[4] == "-":
                assert parse_date(line[:10]) <= cutoff


def test_build_requests_alias_arm_hides_ticker(tmp_path):
    d = _write_snapshot(tmp_path)
    reqs = build_requests("TEST", d, n_agents=1, days=2, arm="alias")
    assert all("TEST (" not in r["prompt"] for r in reqs)


def test_build_requests_needs_history(tmp_path):
    d = _write_snapshot(tmp_path, n_bars=15)
    try:
        build_requests("TEST", d, n_agents=2, days=10, arm="named")
        assert False, "expected RuntimeError for insufficient history"
    except RuntimeError as e:
        assert "bars" in str(e)
