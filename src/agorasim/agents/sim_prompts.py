"""Point-in-time decision-request assembly from frozen snapshots (shared by the P2 gate and
the P3/P4 sim runners). Enforces leakage control L-01 (only bars/news dated <= the decision
day) and L-02 (stable alias for the anonymized arm). Pure + network-free -> unit-testable.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from agorasim.agents.personas import PersonaBank
from agorasim.agents.prompt_builder import load_template, render
from agorasim.data.universe import parse_date

TEMPS = (0.7, 1.0)  # D-07 diversity: temperature mix across the crowd


def stable_alias(ticker: str) -> str:
    """Deterministic anonymized name (L-02): same ticker -> same alias, unlinkable to the real one."""
    h = hashlib.sha256(f"agorasim-alias::{ticker}".encode()).hexdigest()
    letters = "".join(chr(65 + (int(h[i:i + 2], 16) % 26)) for i in range(0, 8, 2))
    return f"{letters} Holdings ({letters})"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def bar_line(b: dict) -> str:
    return (f"{b['t'][:10]}, {float(b['o']):.2f}, {float(b['h']):.2f}, {float(b['l']):.2f}, "
            f"{float(b['c']):.2f}, {int(b.get('v', 0))}")


def news_line(n: dict) -> str:
    ts = n.get("created_at") or n.get("updated_at")
    return f"{ts}: {str(n.get('headline') or n.get('summary') or '')[:180]}"


def point_in_time_blocks(bars_all: list[dict], news_all: list[dict], asof: str,
                         n_bars: int = 20, n_news: int = 3) -> tuple[str, str, list[dict]]:
    """Render the (bars_block, news_block, included_bars) visible strictly as of `asof`."""
    cutoff = parse_date(asof)
    bars = [b for b in sorted(bars_all, key=lambda r: r["t"]) if parse_date(b["t"]) <= cutoff][-n_bars:]
    news = sorted([n for n in news_all
                   if (n.get("created_at") or n.get("updated_at"))
                   and parse_date(n.get("created_at") or n.get("updated_at")) <= cutoff],
                  key=lambda r: r.get("created_at") or r.get("updated_at"))[-n_news:]
    return "\n".join(bar_line(b) for b in bars), "\n".join(news_line(n) for n in news), bars


def build_requests(ticker: str, snap_dir: Path, n_agents: int, days: int, arm: str,
                   persona_seed: int = 1337) -> list[dict]:
    """Point-in-time requests for `n_agents` personas x the last `days` trading days of a ticker.

    Each request = {request_id, prompt (raw system\\n\\nuser), sampling{temperature, seed}}.
    Uses the LAST `days` bars so every decision day has >=20 trailing bars of history.
    """
    bars_all = sorted(read_jsonl(snap_dir / "bars_1d.jsonl"), key=lambda r: r["t"])
    news_all = read_jsonl(snap_dir / "news.jsonl")
    if len(bars_all) < days + 20:
        raise RuntimeError(f"{ticker}: only {len(bars_all)} bars, need >= {days + 20} for a "
                           f"{days}-day slice with history")
    decision_days = [b["t"][:10] for b in bars_all[-days:]]
    personas = PersonaBank(n_agents, seed=persona_seed).personas
    name_or_alias = stable_alias(ticker) if arm == "alias" else f"{ticker} ({ticker})"
    sys_t, user_t = load_template("agent_system.j2"), load_template("decision_user.j2")

    requests: list[dict] = []
    for di, asof in enumerate(decision_days):
        bars_block, news_block, bars = point_in_time_blocks(bars_all, news_all, asof)
        last_close = f"{bars[-1]['c']:.2f}"
        for ai, p in enumerate(personas):
            system = render(sys_t, persona=p.render())
            user = render(user_t, asof_date=asof, name_or_alias=name_or_alias,
                          bars_block=bars_block, news_block=news_block, shares=str(p.shares),
                          avg_cost=last_close, cash=f"{p.cash:.2f}")
            requests.append({
                "request_id": f"{ticker}-{arm}-{asof}-a{ai}",
                "prompt": f"{system}\n\n{user}",
                "sampling": {"temperature": TEMPS[(di + ai) % len(TEMPS)], "seed": 1000 + ai},
            })
    return requests
