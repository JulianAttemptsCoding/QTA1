"""Unit tests for contamination recall scoring (C-2)."""
from agorasim.evals.contamination import (
    ProbeResult, extract_price, is_recall, model_passes,
)


def test_extract_price_variants():
    assert extract_price("$1.53") == 1.53
    assert extract_price("about 2.10 dollars") == 2.10
    assert extract_price("1,234.5") == 1234.5
    assert extract_price("UNKNOWN") is None
    assert extract_price("i don't know") is None
    assert extract_price("") is None


def test_is_recall_tolerance():
    assert is_recall(1.05, 1.00, tol=0.10)      # within 5%
    assert not is_recall(1.30, 1.00, tol=0.10)  # 30% off
    assert not is_recall(None, 1.00)
    assert not is_recall(1.0, 0.0)               # guard bad close


def test_model_passes_threshold():
    assert model_passes(ProbeResult("m", "T", 10, 1))       # 0.10 recall -> ok
    assert not model_passes(ProbeResult("m", "T", 10, 2))   # 0.20 recall -> exclude


def test_sample_date_closes_spread():
    import scripts.p2_contamination as c  # noqa: import through package path
    bars = [{"t": f"2025-{m:02d}-15T00:00:00Z", "c": float(m)} for m in range(1, 13)]
    pairs = c.sample_date_closes(bars, 4)
    assert len(pairs) == 4
    dates = [d for d, _ in pairs]
    assert dates == sorted(dates)  # chronological, evenly spread
