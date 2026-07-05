# AgoraSim — One-Pager

**Thesis.** Can a *crowd* of small, cheap LLM "retail investors" reveal information about
small-cap stock moves that a single model can't? AgoraSim is a proof-of-concept that builds the
crowd, runs it under strict anti-cheating controls, and measures the answer honestly.

**What we built (≈$8 of spot GPU).**
- A reproducible simulator: N small instruct LLMs (Qwen-1.5B/3B, Phi-3.5) each make one daily
  buy/sell/hold decision per stock; their aggregate order-flow imbalance is the signal, and a
  call auction gives an endogenous price.
- End-to-end discipline: point-in-time data snapshots (SHA-256 hashed), a leakage spot-check
  with zero look-ahead, post-cutoff contamination probes (zero memorization), and a registered
  trial ledger with multiple-testing-deflated statistics.
- 13,500 decisions at **99.94% valid structured output** on a single commodity T4 GPU.

**What we found (out-of-sample, 10 small caps, 2026 window).**
- **No next-day edge.** The crowd's consensus does not predict tomorrow (information
  coefficient ≈ 0, hit rate < 50%).
- **A small *contrarian* tilt at one week.** Heavier crowd buying preceded slightly *weaker*
  5-day returns (IC ≈ −0.14, 95% CI excludes zero) — the LLM crowd is structurally over-
  optimistic, and fading its strongest conviction did marginally better.
- **But no free lunch.** The signal does **not** beat trivial price momentum (statistically
  indistinguishable), and the effect is tiny, short-horizon, and in hard-to-trade names.

**Bottom line.** The engineering thesis holds — you *can* run a disciplined LLM retail-crowd
simulation cheaply and measure it without fooling yourself. The alpha thesis does not, on this
evidence: the crowd's main measurable property is a quantified optimism/herding bias, not
tradeable prediction. That is a credible negative result, reported as one — and the instrument
is now in place to test it across more regimes and against the calibration (Robinhood-holder)
track once that data is sourced.

**Not** investment advice; **no** live trading, order routing, or real money is involved.
