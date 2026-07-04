"""Universe construction rules (documented, mechanical, no discretion after G1 freeze).

CALIB-2019 (behavior-fidelity track, Robintrack era):
  U-C1 common shares, primary US listing, price >= $1 on selection date
  U-C2 market cap between $50M and $2B (small cap)
  U-C3 retail-heavy proxy: top decile of Robinhood holders / (shares outstanding)
  U-C4 pick 10 tickers by rank, selection date 2019-06-28, hold fixed

OOS-20xx (prediction track, strictly post model-cutoff; concrete dates set at G1):
  U-O1 same share-class / price / cap filters, evaluated point-in-time
  U-O2 retail-heavy proxy WITHOUT paid data: rank by (a) count of Alpaca news items
       mentioning the ticker over trailing 60d, (b) dollar-volume spike ratio,
       (c) lot-size proxy (1/price); document exact formula before the freeze
  U-O3 pick 10 tickers; freeze BEFORE any agent inference is run (no peeking)

Anti-survivorship: selection uses only information available on the selection date;
delistings during the window stay in the sample with delisting returns where computable.

This module is the *pure* ranking core (no network I/O, no pandas): given already-assembled
per-ticker fields it applies the frozen filters and rank metrics deterministically, so the
logic is unit-testable offline. Data acquisition lives in scripts/p1_freeze_universes.py.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from statistics import median
from typing import Any, Optional

# --- Frozen selection parameters (committed; no discretion after the G1 freeze) ----------
CALIB_SELECTION_DATE = "2019-06-28"
CALIB_WINDOW = ("2019-07-01", "2019-12-31")
# OOS selection strictly after the max verified model cutoff from G0 (D-04). The enabled
# G0 roster (Qwen2.5, SmolLM2, Phi-3.5) all predate 2025; a 2024-12-20 selection with a
# 2025-01-02 window start clears every enabled model's release. Frozen here before inference.
OOS_SELECTION_DATE = "2024-12-20"
OOS_WINDOW = ("2025-01-02", "2026-06-30")

CAP_MIN = 50_000_000.0
CAP_MAX = 2_000_000_000.0
MIN_PRICE = 1.0
N_UNIVERSE = 10

# Name markers that exclude a symbol from the common-share universe (U-C1 / U-O1).
EXCLUDED_NAME_MARKERS = (
    " ETF", " ETN", " WARRANT", " RIGHT", " UNIT", " PREFERRED", " PFD",
    " ADR", " ADS", " NOTES", " FUND", " TRUST", " SPAC",
)


@dataclass(frozen=True)
class UniverseRow:
    ticker: str
    price: float
    shares_outstanding: float
    market_cap: float
    rank_metric: float
    notes: str


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(str(value)[:10])


def is_common_equity_name(name: str) -> bool:
    """False for obvious non-common-share instruments (ETF/warrant/unit/preferred/...)."""
    padded = f" {str(name).upper()} "
    return not any(marker in padded for marker in EXCLUDED_NAME_MARKERS)


def passes_cap_filter(cap: float) -> bool:
    return CAP_MIN <= cap <= CAP_MAX


def zscore(values: dict[str, float]) -> dict[str, float]:
    """Sample-std z-score over the finite values; constant/empty input -> all zeros."""
    finite = [v for v in values.values() if math.isfinite(v)]
    if not finite:
        return {k: 0.0 for k in values}
    mean = sum(finite) / len(finite)
    var = sum((v - mean) ** 2 for v in finite) / max(1, len(finite) - 1)
    std = math.sqrt(var) or 1.0
    return {k: (v - mean) / std for k, v in values.items()}


def close_on_or_before(bars: list[dict[str, Any]], asof: str) -> tuple[Optional[float], Optional[dict]]:
    """Most recent daily close at or before `asof` (point-in-time; never looks ahead)."""
    cutoff = parse_date(asof)
    candidates = [b for b in bars if b.get("t") and parse_date(b["t"]) <= cutoff]
    if not candidates:
        return None, None
    bar = max(candidates, key=lambda r: r["t"])
    return float(bar["c"]), bar


def shares_outstanding_asof(facts: Optional[dict], asof: str) -> Optional[float]:
    """Latest SEC dei:EntityCommonStockSharesOutstanding with period-end <= asof (>0)."""
    if not facts:
        return None
    units = (((facts.get("facts") or {}).get("dei") or {})
             .get("EntityCommonStockSharesOutstanding") or {}).get("units") or {}
    rows = units.get("shares") or []
    cutoff = parse_date(asof)
    usable: list[tuple[dt.date, str, float]] = []
    for row in rows:
        try:
            end = parse_date(str(row.get("end", "")))
            value = float(row["val"])
        except (ValueError, KeyError, TypeError):
            continue
        if value > 0 and end <= cutoff:
            usable.append((end, str(row.get("filed", "")), value))
    if not usable:
        return None
    usable.sort(key=lambda item: (item[0], item[1]))
    return usable[-1][2]


def dollar_volume_spike(bars: list[dict[str, Any]], asof: str, window: int = 60) -> Optional[float]:
    """Ratio of the as-of dollar volume to the trailing-`window` median (needs >=20 bars)."""
    cutoff = parse_date(asof)
    selected = sorted((b for b in bars if b.get("t") and parse_date(b["t"]) <= cutoff),
                      key=lambda r: r["t"])
    if len(selected) < 20:
        return None
    last = selected[-1]
    trailing = selected[:-1][-window:]
    dvs = [float(b["c"]) * float(b.get("v", 0.0)) for b in trailing if float(b.get("v", 0.0)) > 0]
    if not dvs:
        return None
    med = median(dvs)
    if med <= 0:
        return None
    return float(last["c"]) * float(last.get("v", 0.0)) / med


def rank_calib(rows: dict[str, dict[str, float]], n: int = N_UNIVERSE) -> list[UniverseRow]:
    """CALIB U-C1..U-C4: filter (price>=1, cap in band), rank by holders/shares, top n.

    rows[ticker] = {"price", "shares", "cap", "holders"} (already assembled from data).
    """
    valid: list[UniverseRow] = []
    for ticker, r in rows.items():
        price, shares, cap, holders = r["price"], r["shares"], r["cap"], r["holders"]
        if price < MIN_PRICE or shares <= 0 or not passes_cap_filter(cap):
            continue
        valid.append(UniverseRow(ticker, price, shares, cap, holders / shares,
                                 f"holders={int(holders)}"))
    valid.sort(key=lambda row: row.rank_metric, reverse=True)
    return valid[:n]


def rank_oos(rows: dict[str, dict[str, float]], n: int = N_UNIVERSE) -> list[UniverseRow]:
    """OOS U-O1..U-O3: retail-attention score z(news60)+z(dv_spike)+0.5*z(1/price), top n.

    rows[ticker] = {"price", "shares", "cap", "news60", "dv_spike", "inv_price"}; callers
    pass only symbols that already cleared the price/cap/common-share filters.
    """
    if not rows:
        return []
    news_z = zscore({t: float(r["news60"]) for t, r in rows.items()})
    spike_z = zscore({t: float(r["dv_spike"]) for t, r in rows.items()})
    lot_z = zscore({t: float(r["inv_price"]) for t, r in rows.items()})
    out: list[UniverseRow] = []
    for ticker, r in rows.items():
        score = news_z[ticker] + spike_z[ticker] + 0.5 * lot_z[ticker]
        out.append(UniverseRow(
            ticker, r["price"], r["shares"], r["cap"], score,
            f"news60={int(r['news60'])}; dv_spike={r['dv_spike']:.3f}; lot_proxy={r['inv_price']:.4f}",
        ))
    out.sort(key=lambda row: row.rank_metric, reverse=True)
    return out[:n]
