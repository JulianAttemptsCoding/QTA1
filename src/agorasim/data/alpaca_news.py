"""Alpaca News API loader SKELETON (endpoint exists on the data API; historical depth
for free keys is a G0 verification item -- do not assume until p0_gate_data.py passes).
Headlines are the agents' event feed; store raw JSONL per (ticker, day), hashed into
the data snapshot manifest. Point-in-time rule L-01 applies: only items with
created_at strictly before the decision timestamp may enter a prompt.
"""
from __future__ import annotations

NEWS_BASE = "https://data.alpaca.markets/v1beta1/news"
