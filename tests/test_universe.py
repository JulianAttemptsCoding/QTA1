"""Unit tests for the pure universe-ranking core (network-free, deterministic)."""
import math

import agorasim.data.universe as u


def test_is_common_equity_name_excludes_non_common():
    assert u.is_common_equity_name("Acme Industries Inc")
    assert not u.is_common_equity_name("SPDR S&P 500 ETF")
    assert not u.is_common_equity_name("Some Company Warrant")
    assert not u.is_common_equity_name("Acme 5% Preferred")


def test_passes_cap_filter_band():
    assert not u.passes_cap_filter(49_999_999)
    assert u.passes_cap_filter(50_000_000)
    assert u.passes_cap_filter(2_000_000_000)
    assert not u.passes_cap_filter(2_000_000_001)


def test_zscore_mean_zero_unit_std():
    z = u.zscore({"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0})
    assert abs(sum(z.values())) < 1e-9
    assert z["a"] < z["b"] < z["c"] < z["d"]


def test_zscore_constant_is_zeros():
    assert u.zscore({"a": 5.0, "b": 5.0}) == {"a": 0.0, "b": 0.0}


def test_close_on_or_before_is_point_in_time():
    bars = [
        {"t": "2019-06-25T00:00:00Z", "c": 10.0},
        {"t": "2019-06-27T00:00:00Z", "c": 11.0},
        {"t": "2019-07-01T00:00:00Z", "c": 99.0},  # after as-of, must be ignored
    ]
    price, bar = u.close_on_or_before(bars, "2019-06-28")
    assert price == 11.0
    assert bar["t"].startswith("2019-06-27")


def test_close_on_or_before_none_when_empty():
    assert u.close_on_or_before([], "2019-06-28") == (None, None)


def test_shares_outstanding_asof_latest_before_cutoff():
    facts = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
        {"end": "2019-03-31", "val": 100.0, "filed": "2019-04-15"},
        {"end": "2019-06-30", "val": 200.0, "filed": "2019-07-10"},  # end after cutoff
        {"end": "2019-06-15", "val": 150.0, "filed": "2019-06-20"},
    ]}}}}}
    # cutoff 2019-06-28: newest usable period-end is 2019-06-15 -> 150
    assert u.shares_outstanding_asof(facts, "2019-06-28") == 150.0


def test_shares_outstanding_asof_missing():
    assert u.shares_outstanding_asof(None, "2019-06-28") is None
    assert u.shares_outstanding_asof({"facts": {}}, "2019-06-28") is None


def test_dollar_volume_spike_ratio():
    # 24 trailing bars at dv=100 (c=1,v=100) then a spike bar dv=1000 on the as-of date
    bars = [{"t": f"2024-11-{d:02d}T00:00:00Z", "c": 1.0, "v": 100.0} for d in range(1, 25)]
    bars.append({"t": "2024-12-20T00:00:00Z", "c": 1.0, "v": 1000.0})
    spike = u.dollar_volume_spike(bars, "2024-12-20")
    assert spike is not None and abs(spike - 10.0) < 1e-9


def test_dollar_volume_spike_needs_history():
    bars = [{"t": f"2024-12-{d:02d}T00:00:00Z", "c": 1.0, "v": 100.0} for d in range(1, 5)]
    assert u.dollar_volume_spike(bars, "2024-12-20") is None


def test_rank_calib_filters_and_orders():
    rows = {
        "AAA": {"price": 5.0, "shares": 1_000_000, "cap": 500_000_000, "holders": 50_000},   # metric .05
        "BBB": {"price": 5.0, "shares": 1_000_000, "cap": 500_000_000, "holders": 10_000},   # metric .01
        "LOWP": {"price": 0.5, "shares": 1_000_000, "cap": 500_000_000, "holders": 99_000},  # price<1 drop
        "BIG": {"price": 5.0, "shares": 1_000_000_000, "cap": 5_000_000_000, "holders": 99_000},  # cap>2B drop
    }
    out = u.rank_calib(rows)
    assert [r.ticker for r in out] == ["AAA", "BBB"]
    assert out[0].rank_metric > out[1].rank_metric
    assert "holders=50000" in out[0].notes


def test_rank_oos_score_blend_and_topn():
    # AAA leads on news + dv_spike; ZZZ trails on all three components.
    rows = {
        "AAA": {"price": 2.0, "shares": 1e8, "cap": 2e8, "news60": 40, "dv_spike": 10.0, "inv_price": 0.5},
        "MID": {"price": 4.0, "shares": 1e8, "cap": 4e8, "news60": 20, "dv_spike": 3.0, "inv_price": 0.25},
        "ZZZ": {"price": 8.0, "shares": 1e8, "cap": 6e8, "news60": 5, "dv_spike": 1.0, "inv_price": 0.125},
    }
    out = u.rank_oos(rows, n=2)
    assert [r.ticker for r in out] == ["AAA", "MID"]
    assert len(out) == 2
    assert "news60=40" in out[0].notes


def test_rank_oos_empty():
    assert u.rank_oos({}) == []


def test_frozen_dates_are_ordered_and_post_cutoff():
    # OOS window starts after selection, which is after the CALIB era (sanity on the freeze).
    assert u.OOS_WINDOW[0] > u.OOS_SELECTION_DATE
    assert u.OOS_SELECTION_DATE > u.CALIB_WINDOW[1]
    assert math.isclose(u.CAP_MIN, 5e7) and math.isclose(u.CAP_MAX, 2e9)
