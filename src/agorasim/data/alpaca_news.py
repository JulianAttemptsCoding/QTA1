"""Alpaca News API loader (free plan). Historical depth is a G0 verification item --
do not assume until p0_gate_data.py passes. Headlines are the agents' event feed; store
raw JSONL per (ticker, day), hashed into the snapshot manifest. Point-in-time rule L-01:
only items with created_at strictly before the decision timestamp may enter a prompt.

Failure modes:
- 401/403 -> keys wrong / news not permitted -> raise with remediation text.
- 429     -> exponential backoff.
"""
from __future__ import annotations

import os
import time
from typing import Iterator

import requests

NEWS_BASE = "https://data.alpaca.markets/v1beta1/news"


def _headers() -> dict:
    key, sec = os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY")
    if not key or not sec:
        raise RuntimeError("Set APCA_API_KEY_ID / APCA_API_SECRET_KEY (see .env.example).")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}


def iter_news(symbols: list[str], start: str, end: str, sort: str = "asc",
              limit: int = 50, include_content: bool = False) -> Iterator[dict]:
    """Yield raw Alpaca news items for `symbols` within [start, end].

    Paginates via next_page_token. sort='asc' to discover the earliest article,
    'desc' for most-recent-first. limit is capped at 50 by the endpoint.
    """
    params: dict = {"symbols": ",".join(symbols), "start": start, "end": end,
                    "sort": sort, "limit": min(limit, 50),
                    "include_content": str(include_content).lower(),
                    "exclude_contentless": "false"}
    token = None
    backoff = 1.0
    while True:
        if token:
            params["page_token"] = token
        r = requests.get(NEWS_BASE, params=params, headers=_headers(), timeout=30)
        if r.status_code == 429:
            time.sleep(backoff); backoff = min(backoff * 2, 60); continue
        if r.status_code in (401, 403):
            raise RuntimeError(f"Alpaca news auth error {r.status_code}: {r.text[:200]} "
                               f"-- check keys and whether news history is allowed on your plan.")
        r.raise_for_status()
        backoff = 1.0
        payload = r.json()
        for item in (payload.get("news") or []):
            yield item
        token = payload.get("next_page_token")
        if not token:
            return
