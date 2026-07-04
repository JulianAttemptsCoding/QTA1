"""Unit tests for the sim collector aggregation (pool raw decisions -> crowd signals)."""
import json

import scripts.collect_sim_phase as c


def test_parse_request_id():
    assert c.parse_request_id("TLRY-alias-2025-03-17-a5") == ("TLRY", "alias", "2025-03-17")
    assert c.parse_request_id("NVNI-named-2026-01-15-a0") == ("NVNI", "named", "2026-01-15")


def _raw(rid, **d):
    d.setdefault("order_type", "market")
    d.setdefault("confidence", 1.0)
    d.setdefault("rationale", "x")
    return {"request_id": rid, "raw_text": json.dumps(d), "model": "m"}


def test_aggregate_imbalance_and_summary():
    raw = [
        _raw("TLRY-alias-2025-03-17-a0", action="buy", qty=100),
        _raw("TLRY-alias-2025-03-17-a1", action="buy", qty=100),
        _raw("TLRY-alias-2025-03-17-a2", action="sell", qty=100),
        _raw("TLRY-alias-2025-03-17-a3", action="hold", qty=0),
        {"request_id": "TLRY-alias-2025-03-17-a4", "raw_text": "GARBAGE not json", "model": "m"},
    ]
    closes = {("TLRY", "2025-03-17"): 1.50}
    rows = c.aggregate(raw, closes)
    day = [r for r in rows if not r.get("_summary")][0]
    assert day["ticker"] == "TLRY" and day["date"] == "2025-03-17"
    assert day["n_decisions"] == 4          # garbage dropped
    assert abs(day["imbalance_cw"] - (200 - 100) / 300) < 1e-6
    assert day["ref_close"] == 1.5
    summ = rows[-1]
    assert summ["_summary"] and summ["n_decisions_total"] == 5 and summ["n_valid"] == 4


def test_aggregate_all_hold_zero_imbalance():
    raw = [_raw("NVNI-alias-2025-06-16-a0", action="hold", qty=0)]
    rows = c.aggregate(raw, {("NVNI", "2025-06-16"): 8.0})
    day = [r for r in rows if not r.get("_summary")][0]
    assert day["imbalance_cw"] == 0.0 and day["auction_volume"] == 0
