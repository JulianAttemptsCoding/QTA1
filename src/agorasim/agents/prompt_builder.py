"""Point-in-time prompt assembly. HARD RULES enforced here (leakage control L-01..L-03):

L-01 Only information timestamped strictly BEFORE the decision timestamp enters a prompt.
L-02 In anonymized mode, ticker and company name are replaced by a stable random alias
     (Glasserman & Lin 2023 style) to separate reasoning from memorization.
L-03 Prompts never contain the evaluation target or any post-decision data.

Every rendered prompt is hashed; hashes go into the run manifest.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parents[3] / "prompts"


def load_template(name: str) -> str:
    return (PROMPT_DIR / name).read_text()


def render(template: str, **kw: str) -> str:
    out = template
    for k, v in kw.items():
        out = out.replace("{{" + k + "}}", str(v))
    if "{{" in out:
        raise ValueError(f"Unfilled template slots remain: {out[out.index('{{'):][:60]}...")
    return out


def prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
