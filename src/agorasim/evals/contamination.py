"""Memorization / look-ahead controls (LLMs may have seen the backtest era in training).

Protocol (details: PLAN.md section 7):
C-1 Cutoff gate     : every model has a documented training cutoff; the OOS window
                      starts strictly after max(cutoff) of every model used.
C-2 Recall probes   : per (model, ticker) ask for post-cutoff facts (price ranges,
                      events). Nontrivial recall inside the OOS window -> model excluded.
C-3 Anonymization A/B: run identical experiments with ticker/company aliased
                      (Glasserman & Lin 2023). Report both; large named-vs-aliased
                      gaps are treated as memorization, not skill.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProbeResult:
    model_id: str
    ticker: str
    n_probes: int
    n_correct: int

    @property
    def recall_rate(self) -> float:
        return 0.0 if self.n_probes == 0 else self.n_correct / self.n_probes


def model_passes(probe: ProbeResult, max_recall: float = 0.10) -> bool:
    """Exclude a model for a ticker if it recalls post-cutoff facts above chance-ish level."""
    return probe.recall_rate <= max_recall
