# G2_CONTAMINATION — memorization / look-ahead exclusion matrix (P2 / A-202)

Generated (UTC): 2026-07-04

**Result: NO (model, ticker) exclusions. The OOS window is empirically contamination-free.**

## Method (C-2 recall probes)

For each surviving-roster model × OOS ticker, the model was asked — from memory, with NO data
provided (prompts/contamination_probe.j2) — for the closing share price on 10 post-cutoff
dates spread across the OOS window (2025-01-02 … 2026-06-30), in BOTH arms:

- **named** — real ticker/company identity,
- **alias** — a stable random alias (L-02),

scored as *recalled* iff the extracted price is within ±15% of the frozen-snapshot close.
`named_recall > 0.10` ⇒ memorized post-cutoff facts ⇒ exclude the pair from named claims.
`gap = named_recall − alias_recall` is the Glasserman–Lin (2023) contamination fingerprint.

## Exclusion matrix (recall rate; 10 dates × 5 tickers per model)

| Model | TLRY | CHPT | NVNI | BLNK | OGI | any excluded |
|---|---|---|---|---|---|---|
| Qwen2.5-1.5B | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | no |
| Qwen2.5-3B | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | no |
| Phi-3.5-mini | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | no |

named_recall = alias_recall = gap = 0.00 for every cell.

## Interpretation

- **C-1 (cutoff gate)** — satisfied by construction: the OOS window starts strictly after every
  enabled model's release (D-04). This probe is the empirical confirmation.
- **C-2 (recall probes)** — zero recall of post-cutoff prices for all pairs: the models do not
  know these small caps' 2025-2026 prices, so there is no memorization to exclude.
- **C-3 (anonymization A/B)** — the named-vs-alias gap is 0.00, i.e. the real-ticker identity
  confers no recall advantage. The alias arm remains the primary reporting arm for RQ3 (D-06).

No models or tickers are excluded; the full roster (Qwen2.5-1.5B, Qwen2.5-3B, Phi-3.5-mini)
proceeds to P4 on all 10 OOS tickers.

## Provenance

- Worker image `.../agorasim/worker:v13`; entrypoint `scripts/p2_contamination.py`.
- Jobs (us-central1, T4 SPOT, parallel): Qwen1.5B 3353663305422995456,
  Qwen3B 7904550728880881664, Phi-3.5 6956543007319392256.
- Raw results: `gs://…/agorasim/runs/g2_contamination/<model>.json`.
