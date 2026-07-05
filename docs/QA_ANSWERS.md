# QA_ANSWERS — audit of the RQ3 result (oos-main-v2)

Generated (UTC): 2026-07-05. Sources: GCS run artifacts, `docs/`, git history, run manifests,
and cheap CPU recomputation on the archived signals + G1 snapshots (`scripts/qa_analysis.py`).
No GPU jobs were launched. Anything that would require new inference is labelled **NEW-TRIAL**.

---

## The exact prompt and how it was assembled

Every decision is a raw **completion** string `f"{system}\n\n{user}"` (NOT a chat-template call —
`agents/vllm_batch.run_offline` uses `llm.generate`), built by `agents/sim_prompts.build_requests`
→ `point_in_time_blocks` from the frozen snapshot. Prompt-template SHA-256[:16] recorded in the
run manifests (`agent_system.j2 = 46246a8e5fa61e98`, `decision_user.j2 = c9add336ab035877`) — I
verified the committed templates hash to those exact values, so the run prompt == the repo prompt.

**System (`prompts/agent_system.j2`)** — `{{persona}}` is one of 8 styles × experience × risk ×
attention × sizing (`agents/personas.py`):
```
{{persona}}
You make one trading decision per session for the stock described below. You are not an
assistant; respond in character as this investor. You must reply with ONLY a single JSON object,
no prose, matching exactly:
{"action": "buy|sell|hold", "order_type": "market|limit", "qty": <int shares>, "limit_price":
<number or null>, "confidence": <0..1>, "horizon_days": <int>, "rationale": "<one short sentence>"}
Rules: qty must respect your cash (for buys) and your shares (for sells). If unsure, hold with qty 0.
```
**User (`prompts/decision_user.j2`)**:
```
Session date: {{asof_date}} (you know nothing after this date).
Stock: {{name_or_alias}}
Recent daily bars (date, open, high, low, close, volume), oldest first:
{{bars_block}}
Recent headlines (timestamped, oldest first; may be empty):
{{news_block}}
Your position: {{shares}} shares at avg cost {{avg_cost}}; cash {{cash}}.
For market orders, set limit_price to the most recent close.
Decide now. JSON only.
```
- `bars_block` = last **20** daily bars ≤ as-of (`point_in_time_blocks(n_bars=20)`).
- `news_block` = last **3** headlines with `created_at` ≤ as-of (`n_news=3`).
- `name_or_alias` in the **alias** arm = a deterministic random string `stable_alias(ticker)`
  (e.g. TLRY → "FTLA Holdings (FTLA)"); the real ticker is NOT in the template — but see C16.
- Sampling: `temperature ∈ {0.7, 1.0}` alternating by `(day_index + agent_index) % 2`, `seed =
  1000 + agent_index`; guided JSON decoding (`DECISION_JSON_SCHEMA`, lm-format-enforcer). NOT
  temperature 0.
- One prompt per (ticker, decision-day, agent). oos-main-v2 = 10 tickers × 30 days × 45 agents
  (15 per model × 3 models, each model a distinct persona seed 1337/2337/3337) = 13,500 prompts.

---

## A. Statistical validity of the 5d IC = −0.137

**A1 — bootstrap unit / block length; day-blocked recompute.**
`p5_stats.block_bootstrap_ic(signal, fwd, block=5, n=2000)` resamples the **pooled ticker-day
array**, ordered ticker-major-then-date (the order `collect_sim_phase` writes signals.jsonl). It is
a moving-block bootstrap with **block length 5** over that pooled series — so it is *pooled
ticker-days*, **NOT whole calendar days**; it does not keep all 10 tickers of a day together, and
it ignores the strong same-day cross-sectional correlation. Recomputing with **whole-day circular
blocks** (all tickers of a day resampled together, block=5 days, n=3000):

| CI method | 5d IC (cw) | 5d IC (uw) |
|---|---|---|
| pooled ticker-day blocks (as shipped, docs/P5_STATS.md) | [−0.271, −0.007] | [−0.267, −0.005] |
| **whole-day blocks (correct unit)** | **[−0.236, −0.011]** | **[−0.233, −0.010]** |

Both still exclude zero, but only barely (upper bound ≈ −0.01). The shipped CI slightly
*overstated* precision by ignoring within-day correlation; the corrected day-blocked CI is a touch
narrower on the low side and equally close to zero on top. **Verdict: marginally significant.**

**A2 — DM overlap handling.** `p5_stats` calls `diebold_mariano(loss_crowd, loss_base, h=h)` with
`h = the horizon`, so the 5d rows ran DM at **h=5** (LRV Newey-West-style truncation over lags
1..4, code `for k in range(1,h)`). The loss is a **directional 0/1 loss** (`sign(signal) ≠
sign(return)`) vs the same for the 5-day-momentum baseline. Result at 5d: **DM = +0.32, p = 0.75**
(cw) / **+0.43, p = 0.66** (uw) — the crowd is *not* distinguishable from momentum. Caveat: the DM
series is the pooled ticker-major vector, not a clean single time series, so the LRV autocorrelation
correction is only approximate. It did already run at h=5 (no rerun needed).

**A3 — cross-sectional vs time-series decomposition (day-blocked).**
- **Within-day cross-sectional** mean Spearman IC (does the crowd rank the 10 names correctly on a
  given day?) = **−0.044**, sd 0.302 across 25 days, **t = −0.73 → NOT distinguishable from zero.**
- **Per-ticker time-series** IC: NVNI −0.48, TPET −0.35, EDIT −0.28, OGI −0.28, FRSX −0.22, TLRY
  −0.12, CHPT −0.05, BLNK +0.02, ICCM +0.16, CCO +0.24; **mean = −0.137**.

**The pooled −0.137 is entirely a time-series effect** (crowd more bullish than its own norm on a
name → that name underperforms next week); there is **no cross-sectional stock-picking signal**.
The per-ticker ICs are very dispersed (−0.48 … +0.24).

**A4 — jackknife by ticker** (drop-one pooled 5d IC): −NVNI −0.100, −CCO −0.181, −TLRY −0.155,
−EDIT −0.121, −CHPT −0.149, −BLNK −0.116, −FRSX −0.132, −TPET −0.122, −OGI −0.138, −ICCM −0.153.
No single name flips the **sign**, but **dropping NVNI flips the day-blocked CI to include zero:
[−0.195, +0.012]**. (Dropping CCO → [−0.288, −0.019], dropping TLRY → [−0.289, −0.011] both still
exclude zero.) **The statistical significance of the headline result is load-bearing on a single
ticker (NVNI, whose own TS IC is −0.48).** This is the biggest fragility in the result.

**A5 — signal dispersion.** `imbalance_cw`: min −0.835, p25 +0.162, median +0.684, mean **+0.506**,
p75 +0.926, max +1.000; **82.0%** of ticker-days are net-positive, **29.2%** are > 0.9 (saturated
extreme-buy); **250 unique values, no ties** (confidence-weighting makes it continuous, so the
Spearman ranks are clean). On the **imbalance ≤ 0.9 subsample** (n=177) the 5d IC weakens to
**−0.084** → roughly a third of the effect comes from the ~29% saturated extreme-buy days.

**A6 — confound vs reversal.** On the same 250 ticker-days: trailing-5d **momentum IC = −0.288**
(i.e. strong 5-day *reversal* in these names this window), reversal = +0.288, imbalance IC =
−0.137, corr(imbalance, momentum) = +0.09. **Partial rank corr(imbalance, fwd | momentum) =
−0.116** — the crowd signal is *largely distinct* from plain reversal (it barely shrinks when
controlling for it). BUT note (see D19): momentum-5d IC is only −0.037 on the full 3,630-day
history — the run's 30-day window was an unusually strong **mean-reversion regime**, which inflates
both the market's reversal and the crowd's contrarian IC. So: the crowd adds a little beyond
reversal, but the window is not return-representative, and plain price reversal was the stronger
signal.

**A7 — what DSR measured.** `p5_stats` computes DSR on the **sign(signal) trading-strategy Sharpe**
(annualized `sign(imbalance)·forward_return`), not on the IC. Inputs: `sr_hat` = that strategy's
SR, skew/kurt of its daily returns, `n_trials = 4` (TRIALS.md), and `sr_var_across_trials =
variance of the four signal×horizon strategy SRs = 1.307` (SRs = [0.92, 2.17, −0.93, 1.41]).
**Two caveats:** (i) the sign-follow strategy is ~always long (crowd 82% net-buy), so its SR
mostly reflects the window's drift, not signal skill — the cw_5d "DSR = 0.99" is not evidence of a
real edge; (ii) using the four signal×horizon SRs as the `sr_var` trial dispersion is a loose
reading of Bailey–López de Prado (the registered trials are the *signals*, not the sign-follow
strategy). **Treat the DSR numbers as non-load-bearing; the IC + its day-blocked CI is the honest
statistic.**

---

## B. Selection & registration audit

**B8 — when was the 30-day window fixed; were signal-vs-return stats computed earlier?**
The window is mechanical: "**last N trading days of the frozen G1 snapshot**" (`build_requests`
uses the last `--days` bars), so for oos-main-v2 it is **2026-05-18 → 06-26**. `--days 30` was
fixed at the **oos-main-v2 launch, commit `499ff5b` (2026-07-05 09:44 +08)**. (The earlier
oos-main-v1 used `--days 60`, commit `89176fa` 05:08, but hung and produced no signals.)
**Yes — signal-vs-return statistics were computed before that:** during the main-run wait I ran
`p5_stats --run-id oos-pilot-v2` (~06:2x) on the pilot's 40 ticker-days and saw IC ≈ −0.19. Every
artifact that pairs signals with returns: (a) the **pilot** P5_STATS.md (computed ~06:2x, *not*
committed — deleted before the main run), and (b) **oos-main-v2** P5_STATS.md (committed `8072012`
11:55). **Honest disclosure:** a pilot IC on TLRY/CHPT was viewed before the 30-day main window was
finalized; the 30-day choice itself was throughput-driven (B9), not chosen to improve the IC, but
this is a real researcher-degree-of-freedom and is disclosed here.

**B9 — why the last 30 days specifically?** For **speed/stability**, not recency of coverage or
returns: oos-main-v1 at `--days 60` with chunk-512 hit a KV-preemption hang (>1 h, no output), so
the relaunch (`499ff5b`) cut to 30 days and chunk 128 to finish reliably in ~2 h. The deciding
record is `notes.md` [2026-07-05 P4/P5/P6] ("reduced ... for speed/stability after the chunk-512
hang") and STATE.json. It is **not** documented as a returns-based choice. "Last N days" (rather
than a random in-window slice) is `build_requests`' fixed rule.

**B10 — TRIALS.md, and was n=4 committed before p5_stats ran?** Yes. TRIALS.md was committed at
`a3b00a9` **2026-07-05 05:09:40**; `p5_stats.py` was committed at `8c73782` 05:23 and first *ran*
(on the pilot) ~06:2x and on the main run 11:55 — all **after** registration. Full contents:
```
| # | Date | Phase | Signal / config | Universe | Window | Status |
| 1 | 2026-07-05 | P4 | flow_imbalance (conf-weighted), alias arm | OOS-10 | G1-frozen | registered |
| 2 | 2026-07-05 | P4 | flow_imbalance (unweighted), alias arm | OOS-10 | G1-frozen | registered |
| 3 | 2026-07-05 | P4 | single-strong-LLM sentiment baseline | OOS-10 | G1-frozen | registered |
| 4 | 2026-07-05 | P4 | momentum(1/5/20), AR(1), logistic baselines | OOS-10 | G1-frozen | registered |
```
n_trials = 4. Minor doc lag: the header line says "Run: oos-main-v1" while the executed run was
oos-main-v2 (same universe/rules; cosmetic).

**B11 — pilot's 40 ticker-days.** IC **was** computed on them (≈ −0.19, cw). Pilot = TLRY + CHPT ×
last 20 days (~2026-06-02 → 06-30); main = 10 tickers × last 30 days (05-18 → 06-26). **The pilot
days overlap the main window for TLRY and CHPT** — so those two names' main-run days were partly
"seen" during the pilot IC. Disclosed; the pilot was labelled a pipeline-validation and its
P5_STATS.md was discarded, but the overlap is real.

---

## C. Mechanism of the optimism bias (the real PoC finding)

**C12 — action distribution + entropy.** Overall (13,492 parsed of 13,500): **buy 50.5%, hold
39.6%, sell 9.9%.** Per family — **wildly heterogeneous**:

| model | buy | sell | hold | mean signed (buy+1/sell−1) |
|---|---:|---:|---:|---:|
| Qwen2.5-1.5B | 81.8% | 9.3% | 8.9% | **+0.725** |
| Qwen2.5-3B | 5.6% | 20.2% | 74.2% | **−0.145** |
| Phi-3.5-mini | 64.1% | 0.3% | 35.7% | **+0.638** |

Per persona style (validates personas modulate behavior): fomo follower **100% buy**, momentum
chaser 73.6% buy, swing trader 61.3% buy, buy-and-hold 63% buy, lottery-ticket 52% buy, news
reactor 46.9% buy, fundamentals dabbler 38.2% buy, **dip buyer / contrarian 15.8% buy / 24.3%
sell** (correctly the most bearish). **Per-(ticker,day) decision entropy** (Shannon over
buy/sell/hold, normalized base-3): mean **0.834**, median 0.846, range [0.53, 0.98] — the crowd is
genuinely diverse, not unanimous. **This entropy/F-06 metric was NOT computed anywhere previously
(grep of `src/` for entropy/F-06 is empty) — it is new here.**

**C13 — temperature/seeds.** From the manifests + `sim_prompts`: **temperature = {0.7, 1.0}
alternating** (NOT 0.0), `seed = 1000 + agent_index`, persona seed 1337/2337/3337 per model. The
manifest records only the persona seed (`"seed": 1337`, `persona_bank_hash "seed=1337:n=15"`); the
per-request temps live in the (un-uploaded) requests file but are deterministic from the code.
**Within-model diversity = 15 personas × 2 temperatures × per-agent seed, with stochastic sampling
(temp > 0)** — so it is *not* personas-only.

**C14 — guided-decoding order bias.** `DECISION_JSON_SCHEMA["properties"]["action"]["enum"] =
["buy","sell","hold"]` (buy first) and `action` is the **first field** in the schema. lm-format-
enforcer constrains the action token to those three enum strings but does **not** force the first
token to "buy" (the model's own logits choose among the three). Still, first-field + buy-first is a
plausible nudge. **NEW-TRIAL A/B (not run):** rerun the 200-decision G2 slice (or one main
ticker-slice) with the enum reversed `["hold","sell","buy"]` and with the JSON field order
shuffled, compare buy%. Cost estimate: ~200–600 decisions × 3 models, a few min GPU each →
**≈ $0.05–0.10, < 15 min wall**.

**C15 — news emptiness.** **0/300 (0.0%)** ticker-days had zero visible news; every name has many
items available (cumulative ≤-as-of counts: TLRY ~379, BLNK ~139, CHPT ~124, NVNI ~112, OGI ~90,
ICCM ~83, FRSX ~82, CCO ~62, EDIT/TPET ~43). The prompt shows the **last 3** of these, so **every
prompt carried 3 recent headlines** — the crowd was *not* reacting to bars alone.

**C16 — alias integrity (important).** **210/300 = 70.0%** of alias-arm ticker-days have the **real
ticker symbol appear in the visible headline text** (regex of the ≤-as-of news; company-name hits
would be higher still). So the alias arm hides the *label* but the news content de-anonymizes the
name most of the time — the named-vs-alias contrast really measures *label-token* memorization
only, and the alias arm is substantially leaky. (Mitigant: A-202 contamination probes showed 0.0
post-cutoff price recall, so this is an identity leak, not a future-price leak.) **NEW-TRIAL
scrubbed rerun:** add a headline-scrub pass (mask the ticker/company tokens) and rerun one arm ≈
same size as the main run → **≈ $2, ~2 h wall** (+ a cheap CPU scrub step).

**C17 — bias vs scale.** Per-model mean signed action: Qwen-1.5B **+0.725**, Qwen-3B **−0.145**,
Phi-3.5 **+0.638**. **Non-monotonic** — the smallest model is the most bullish, the mid Qwen is
actually net-cautious (hold-heavy), Phi is bullish again. The aggregate +0.5 optimism is driven by
Qwen-1.5B and Phi; Qwen-3B dissents. "Bias is model-specific, not a clean size curve" is itself a
finding.

---

## D. Missing registered components — status & cost

**D18 — single-strong-LLM baseline (D-09a): NOT run.** Confirmed — no artifact under
`runs/` and trial #3 is registered-but-unexecuted. To run on the identical 300 ticker-days: one
analyst-prompt inference per ticker-day per arm ≈ 300 calls → on the existing worker at ~2,500/hr,
**~7 min GPU/arm, ≈ $0.05/arm**. **NEW-TRIAL** (already registered as #3).

**D19 — AR(1) + momentum + logistic (D-09c/d): computed now (CPU, registered — not a new trial).**
- **AR(1):** IC(r_t, r_{t+1}) = **−0.060**, hit 0.442 (n=3,710) — weak 1-day reversal.
- **Momentum(1/5/20) IC** (full daily history, n≈3,500–3,700): vs 1d fwd −0.060 / −0.051 / −0.024;
  vs 5d fwd −0.046 / −0.037 / −0.025. All weak; note the *run-window* 5d momentum IC was −0.288
  (A6) — the window is a special reversal regime.
- **Logistic**(trailing-1d, trailing-5d → next-day up): accuracy **0.572 = base rate 0.572** (no
  edge), IC(p, up) = +0.059. The engineered-feature baseline has essentially no skill.

**D20 — RQ1 stylized facts on the call-auction paths (CPU, no Robintrack):** run
`evals/stylized_facts.py` per ticker on oos-main-v2 auction prices —

| ticker | excess kurt | acf(r,1) | acf(|r|,1) | corr(V,\|r\|) |
|---|---:|---:|---:|---:|
| NVNI | +3.04 | −0.16 | +0.12 | −0.06 |
| TLRY | −1.07 | −0.22 | −0.33 | −0.02 |
| EDIT | +0.57 | +0.19 | +0.02 | +0.18 |
| CHPT | −0.12 | +0.23 | +0.12 | +0.13 |
| BLNK | −0.02 | −0.05 | +0.05 | −0.13 |
| FRSX | +4.84 | −0.32 | +0.51 | +0.18 |
| TPET | +1.00 | −0.49 | +0.41 | −0.11 |
| OGI | +1.31 | +0.18 | −0.00 | +0.01 |
| CCO | +1.09 | −0.52 | +0.52 | −0.11 |
| ICCM | +23.81 | −0.04 | −0.04 | −0.12 |

Heavy tails (SF1) clearly present (ICCM, FRSX, NVNI, TPET, CCO, OGI); volatility clustering (SF3)
present for FRSX/CCO/TPET, absent for others; acf(r,1) mostly negative (short-horizon reversal).
**Caveat:** the collector anchors each day's auction `last_price` to the **actual close**, so these
auction returns partly inherit the real return series — the SF battery on this path is confounded
and only weakly "endogenous"; a truly free-running auction (RQ1 proper) is future work.

**D21 — named-arm behavioral comparison: NOT run** (only the alias main run + the A-202 recall
probes). Cost of a named-arm duplicate of the main run: same size as oos-main-v2 → **≈ $2, ~2 h
wall, 3 jobs.** **NEW-TRIAL.**

**D22 — Robintrack status / user action.** `robintrack.net` is a defunct SPA (no bulk URL found).
The code path is complete and CPU-only. **To unblock P3/RQ2 the user must:** download the Robintrack
popularity export (e.g. Kaggle **"Robinhood Stock Popularity History"**, or a robintrack archive
mirror), extract per-ticker CSVs to **`data/raw/robintrack/popularity_export/<TICKER>.csv`** with
columns **`timestamp, users_holding`**, then run `python scripts/p1_freeze_universes.py --track
calib`. Everything downstream (CALIB freeze, RQ2 fidelity) then runs on CPU/existing worker.

**D23 — were the throughput levers applied in v17?** **Yes.** `sim_prompts.point_in_time_blocks`
defaults to **20 bars / 3 news** (~600–700-token prompt) and `run_offline` uses **max_model_len
2048, chunk 128** in worker:v17. Measured on oos-main-v2 (job start→end / 4,500 decisions):
Qwen-1.5B **2,231/hr** (121 min), Qwen-3B **2,461/hr** (110 min), Phi-3.5 **2,738/hr** (99 min);
**wall ≈ 2.0 h** (3 parallel); **cost ≈ $2.00** (5.7 GPU-hr × ~$0.35 spot). (Prompts are the trimmed
~650-token form, not the old ~900-token one.)

---

## E. Data & engineering QA

**E24 — bar quality.** Over the 30 decision-days, **all 10 tickers have 30/30 bars, 0 missing, 0
zero-volume** — including NVNI, TPET, ICCM. Forward returns are computed on the trading-day index
(`close[i+h]/close[i]−1`), so there are no gap-spanning artifacts; days lacking an h-ahead bar (the
last h of the window) are simply dropped (250 of 300 ticker-days survive at h=5).

**E25 — G5 clean rerun.** Re-ran `collect_sim_phase --run-id oos-main-v2` (re-download raw from GCS
+ re-aggregate) then `p5_stats` and diffed docs/P5_STATS.md: **byte-identical.** Reproducible.

**E26 — shared-bucket hygiene.** `runs/` contains claude prefixes {`g0_throughput`,
`g2_contamination`, `g2_smoke`, `oos-pilot-v2`, `oos-main-v2`} and the codex prefix {`p3/`}. Prefixes
are disjoint (no collision observed), **but** both projects use the same bucket and (apparently) the
same service account, so isolation rests on the **prefix convention, not on ACLs** — either project
*could* read/write the other's paths. Recommend distinct sub-prefixes (`runs/claude/…`) or per-run
ACLs if strict isolation is needed.

**E27 — exact budget (from job create→end × ~$0.30–0.35/hr spot):**

| prefix | $ | note |
|---|---:|---|
| oosmain (v1, **cancelled hang**) | 4.37 | 3 jobs × ~250 min wasted on the chunk-512 KV thrash |
| g0 (valid-JSON debugging) | 3.48 | many short validation probes v1→v11 |
| oosmain2 (**the real run**) | 2.00 | |
| oospilot2 | 0.70 | |
| g2 (smoke + contamination) | 0.57 | |
| oospilot (v1) | 0.51 | |
| p0 + model-cache | 0.20 | |
| **TOTAL** | **≈ $11.84** | of the $85 stop → **headroom ≈ $73** |

Biggest lesson: the oos-main-v1 chunk-512 hang cost **$4.37**, more than double the real run.

---

## F. Iteration-planning estimates (not launched)

Basis: measured ~2,500 dec/hr/T4, ~$0.35/T4-hr spot, 4-T4 spot quota (us-central1), Qwen-1.5B
straggles ~10–25% behind (sets each wave's length), ~5 min provisioning/job.

**F28 — multi-window robustness** (same 10 tickers × 45 agents × 30 days, +5 non-overlapping
windows across 2025-01 → 2026-04): 5 × 13,500 = **67,500 decisions ≈ 27 GPU-hr ≈ $9–10**. As
15 jobs / 4-T4 quota = 4 waves × ~2 h = **~8 h wall.**

**F29 — scaling curve + ablations.** Scaling A-402 (N ∈ {15,45,90,150} × 2 tickers × 30 days × 3
models) = 54,000 decisions ≈ 22 GPU-hr ≈ **$7.6**, ~**6–8 h wall** (the N=150 shard ~3.6 h dominates
its wave). Ablations A-403 (news-off + personas-off, 2 tickers × 100 agents × 60 days each) ≈
24,000–48,000 decisions ≈ **$3–7**, ~**3–5 h wall**.

**F30 — F28+F29 combined:** ≈ 150–170k decisions ≈ **60–65 GPU-hr ≈ $22–25**; with 4-T4 quota +
straggler + provisioning + uneven shard sizes, realistic **wall ≈ 14–18 h** (spread over spot
availability). Running total would reach ≈ $34–37 of the $85 stop — comfortably within budget.
