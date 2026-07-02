"""Market layer. Two deliberately simple, standard mechanisms (no technical novelty):

1) flow_imbalance : the PREDICTION signal. We never need the simulated price to
   track the real price; the tested hypothesis is that aggregate simulated order
   flow carries information about the *real* next-period return.
2) call_auction   : uniform-price batch auction used only for the REALISM track
   (stylized facts of the endogenous simulated price path), following the
   discrete-round convention of LLM market simulators (Lopez-Lira 2025).

Failure modes:
- No crossing orders -> auction returns last_price, volume 0 (never raises).
- All-hold rounds    -> imbalance 0 by construction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from agorasim.schemas import AgentDecision


@dataclass(frozen=True)
class AuctionResult:
    price: float
    volume: int
    buy_qty: int
    sell_qty: int


def flow_imbalance(decisions: Sequence[AgentDecision], confidence_weighted: bool = True) -> float:
    """Signed normalized imbalance in [-1, 1]: (buy - sell) / (buy + sell); 0 if no flow."""
    buy = sell = 0.0
    for d in decisions:
        w = d.qty * (d.confidence if confidence_weighted else 1.0)
        if d.action == "buy":
            buy += w
        elif d.action == "sell":
            sell += w
    tot = buy + sell
    return 0.0 if tot == 0 else (buy - sell) / tot


def call_auction(
    decisions: Sequence[AgentDecision],
    last_price: float,
    tick: float = 0.01,
) -> AuctionResult:
    """Uniform-price call auction. Market orders are price-takers (buy at +inf, sell at 0).
    Clearing price = candidate price maximizing executable volume; ties -> closest to last_price.
    """
    buys: list[tuple[float, int]] = []
    sells: list[tuple[float, int]] = []
    for d in decisions:
        if d.qty <= 0:
            continue
        if d.action == "buy":
            buys.append((float("inf") if d.order_type == "market" else float(d.limit_price), d.qty))
        elif d.action == "sell":
            sells.append((0.0 if d.order_type == "market" else float(d.limit_price), d.qty))
    if not buys or not sells:
        return AuctionResult(price=last_price, volume=0,
                             buy_qty=sum(q for _, q in buys), sell_qty=sum(q for _, q in sells))

    candidates = sorted(
        {last_price}
        | {p for p, _ in buys if p != float("inf")}
        | {p for p, _ in sells if p > 0.0}
    )

    def executable(p: float) -> int:
        demand = sum(q for lim, q in buys if lim >= p)
        supply = sum(q for lim, q in sells if lim <= p)
        return min(demand, supply)

    best = max(candidates, key=lambda p: (executable(p), -abs(p - last_price)))
    vol = executable(best)
    if vol == 0:
        return AuctionResult(price=last_price, volume=0,
                             buy_qty=sum(q for _, q in buys), sell_qty=sum(q for _, q in sells))
    price = round(round(best / tick) * tick, 10)
    return AuctionResult(price=price, volume=vol,
                         buy_qty=sum(q for _, q in buys), sell_qty=sum(q for _, q in sells))
