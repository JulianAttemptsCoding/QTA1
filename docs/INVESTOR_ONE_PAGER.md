# AgoraSim One-Pager

## What It Is

AgoraSim is a research prototype for a "digital twin" of retail crowd behavior:
hundreds of small open-weight LLM agents read point-in-time public information
about retail-heavy small-cap stocks and make one buy/sell/hold decision per day.
The output is not a trade bot. It is an auditable scenario-analysis and event
study engine.

## Why It Matters

Retail crowd behavior matters during small-cap news cycles, squeezes, dilution
events, and social attention shocks. AgoraSim tests whether cheap open models can
produce a measurable, reproducible crowd-flow proxy without proprietary order
flow or paid data.

## What Worked

- Vertex-only execution produced archived raw prompts, outputs, manifests, and
  daily sim aggregates.
- Calibration-era behavior cleared the pre-set kill gate: pooled Robintrack sign
  agreement was `0.524`.
- The OOS main run was fully pre-registered and reproducible across `1,250`
  ticker-days.
- Follow-up scaling to N=300 improved two-ticker short-window IC versus N=100,
  while N1000 was stopped for budget discipline.

## What Did Not Work

- The main OOS crowd signal is not a compelling alpha source: pooled weighted IC
  was `0.0276`, hit rate was `0.4363`, and the confidence interval crossed zero.
- Some simulated auction paths are too flat to claim broad market-process realism.
- Persona diversity increases entropy, but the first ablation does not prove it
  improves predictive performance.

## Current Status

- Gates G0-G5: complete.
- Final tracked budget: `$80.25`.
- Active Vertex jobs: none.
- Code branch: `codex`.
- Heavy compute account/project:
  `jjjsresearch@gmail.com / project-82d97cf9-5889-43a4-850`.

## Next Fundable Step

Turn the negative result into a sharper simulator: pre-register a diagnostic
iteration focused on directional bias, calibration of confidence to position
size, and event-window replay quality. The product value is scenario analysis
and explainable retail-flow simulation, not immediate trading performance.
