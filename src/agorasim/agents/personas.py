"""Deterministic persona bank for agent heterogeneity.

Diversity sources (in place of MC-dropout, which standard inference stacks like
vLLM run with dropout disabled and is therefore NOT used -- see PLAN.md D-07):
  model family x persona archetype x sampling temperature x seed.

Personas are seeded and hashed so every run is exactly reproducible.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass

STYLES = ["momentum chaser", "dip buyer / contrarian", "news reactor",
          "fundamentals-curious value dabbler", "lottery-ticket speculator",
          "swing trader", "buy-and-hold accumulator", "fomo follower"]
EXPERIENCE = ["first-year novice", "two-year hobbyist", "five-year retail veteran"]
RISK = ["cautious", "moderate", "aggressive", "yolo"]
ATTENTION = ["checks once a day", "checks a few times a day", "glued to the feed"]
SIZING = ["tiny fixed-dollar buys", "round-lot habit", "all-in-or-nothing swings"]


@dataclass(frozen=True)
class Persona:
    persona_id: str
    style: str
    experience: str
    risk: str
    attention: str
    sizing: str
    cash: float
    shares: int

    def render(self) -> str:
        return (f"You are a retail investor: {self.experience}, {self.risk} risk appetite, "
                f"trading style: {self.style}; you {self.attention} and prefer {self.sizing}. "
                f"Current position: {self.shares} shares, ${self.cash:,.0f} cash.")


class PersonaBank:
    def __init__(self, n: int, seed: int = 1337,
                 cash_range: tuple[float, float] = (500.0, 25_000.0)):
        self.n, self.seed = n, seed
        rng = random.Random(seed)
        self.personas: list[Persona] = []
        for i in range(n):
            attrs = dict(
                style=rng.choice(STYLES), experience=rng.choice(EXPERIENCE),
                risk=rng.choice(RISK), attention=rng.choice(ATTENTION),
                sizing=rng.choice(SIZING),
                cash=round(rng.uniform(*cash_range), 2),
                shares=rng.choice([0, 0, 0, 5, 10, 25, 100]),
            )
            pid = hashlib.sha256(json.dumps({"seed": seed, "i": i, **attrs},
                                            sort_keys=True).encode()).hexdigest()[:12]
            self.personas.append(Persona(persona_id=pid, **attrs))

    def content_hash(self) -> str:
        blob = json.dumps([asdict(p) for p in self.personas], sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()
