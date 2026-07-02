"""Alpaca historical bars loader (free plan). Verified assumptions live in GATE G0:
free plan = real-time IEX + 15-minute-delayed SIP; for a backtest, delayed SIP history
is sufficient. Confirm the exact `feed` parameter behavior for your keys via
scripts/p0_gate_data.py before any experiment; small caps on IEX-only bars are sparse,
so prefer the SIP-delayed feed for historical pulls if the account allows it.

Failure modes:
- 403/401 -> keys wrong or feed not permitted -> raise with remediation text.
- 429     -> exponential backoff (free tier ~200 req/min; verify at G0).
- empty bars for thin names -> caller must treat missing minutes as no-trade, never ffill volume.
"""
from __future__ import annotations

import os
import time
from typing import Iterator

import requests

BASE = "https://data.alpaca.markets/v2/stocks/bars"


def _headers() -> dict:
    key, sec = os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY")
    if not key or not sec:
        raise RuntimeError("Set APCA_API_KEY_ID / APCA_API_SECRET_KEY (see .env.example).")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}


def iter_bars(symbols: list[str], start: str, end: str, timeframe: str = "1Day",
              feed: str | None = None, limit: int = 10_000) -> Iterator[dict]:
    params: dict = {"symbols": ",".join(symbols), "start": start, "end": end,
                    "timeframe": timeframe, "limit": limit, "adjustment": "all"}
    if feed:
        params["feed"] = feed
    token = None
    backoff = 1.0
    while True:
        if token:
            params["page_token"] = token
        r = requests.get(BASE, params=params, headers=_headers(), timeout=30)
        if r.status_code == 429:
            time.sleep(backoff); backoff = min(backoff * 2, 60); continue
        if r.status_code in (401, 403):
            raise RuntimeError(f"Alpaca auth/feed error {r.status_code}: {r.text[:200]} "
                               f"-- check keys and whether feed={feed!r} is allowed on your plan.")
        r.raise_for_status()
        backoff = 1.0
        payload = r.json()
        for sym, bars in (payload.get("bars") or {}).items():
            for b in bars:
                yield {"symbol": sym, **b}
        token = payload.get("next_page_token")
        if not token:
            return
