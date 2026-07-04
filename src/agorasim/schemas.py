"""Structured agent decision schema + robust parsing of LLM JSON output.

Failure modes handled explicitly:
- Model emits markdown fences or prose around JSON  -> stripped / first balanced object extracted.
- Model emits invalid enum / out-of-range values    -> pydantic ValidationError -> counted, decision dropped.
- action == "hold" with nonzero qty                 -> normalized to qty = 0.
Parse-failure rate is a first-class metric (Gate G2 requires >= 99% valid).
"""
from __future__ import annotations

import json
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


class AgentDecision(BaseModel):
    action: Literal["buy", "sell", "hold"]
    order_type: Literal["market", "limit"] = "market"
    qty: int = Field(ge=0, le=1_000_000, description="shares")
    limit_price: Optional[float] = Field(default=None, gt=0)
    confidence: float = Field(ge=0.0, le=1.0)
    horizon_days: int = Field(default=1, ge=1, le=30)
    rationale: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _normalize(self) -> "AgentDecision":
        if self.action == "hold":
            object.__setattr__(self, "qty", 0)
        if self.order_type == "limit" and self.limit_price is None:
            object.__setattr__(self, "order_type", "market")
        return self


def parse_decision(raw: str) -> Optional[AgentDecision]:
    """Best-effort extraction of one AgentDecision from raw LLM text. None on failure."""
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    m = JSON_OBJ_RE.search(text)
    if not m:
        return None
    try:
        payload = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    # Small models routinely emit `"limit_price": 0` for hold/market orders (a placeholder,
    # not a real limit). The guided-decoding JSON schema declares minimum 0.01, but
    # lm-format-enforcer does not enforce numeric bounds, so the 0 reaches here and trips the
    # AgentDecision `gt=0` field constraint -> the whole decision is dropped as invalid. A
    # non-positive limit price is meaningless (there is no such limit order), so coerce it to
    # None = "no limit" (market). This is the operative fix that lifted Qwen3B/Phi-3.5 from
    # ~0% to ~100% valid-JSON on Gate G0 without loosening the limit-order invariant.
    lp = payload.get("limit_price")
    if isinstance(lp, (int, float)) and not isinstance(lp, bool) and lp <= 0:
        payload["limit_price"] = None
    try:
        return AgentDecision(**{k: v for k, v in payload.items() if k in AgentDecision.model_fields})
    except Exception:
        return None
