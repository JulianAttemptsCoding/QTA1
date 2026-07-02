# QC_AUDIT.md — Multi-pass QC/QA audit of the AgoraSim decision, plan, and repo

- **Target Domain:** Applied machine learning × empirical market microstructure
  (LLM agent-based simulation research)
- **Target Standard/Venue:** ACM ICAIF full paper (the venue of ABIDES and most
  LLM-market-sim work) + "investor-grade" proof-of-concept package
- **Work under audit:** DECISION_MEMO.md, PLAN.md, FEASIBILITY.md, README.md,
  prompts/, configs/, src/, tests/ as of this commit
- **Protocol note (honesty):** each pass below was a full end-to-end re-read of all
  audited artifacts against the Master Checklist, executed sequentially by one
  reviewer (me). Revisions were applied to the artifacts immediately; the documents
  in this repo are the POST-audit versions, and the passes below record what changed.

---

## STAGE 1: MASTER QC CHECKLIST (ICAIF paper + investor PoC)

**Framing & significance**
- [ ] M-01 Objective, novelty, significance clear in ≤30 seconds of README
- [ ] M-02 Claims falsifiable; registered RQs; value of a null result stated
- [ ] M-03 Positioning against TwinMarket / StockAgent / Lopez-Lira 2025 / MarS explicit

**Validity (the field's known killers)**
- [ ] M-04 Look-ahead/memorization: training-cutoff handling, probes, anonymization A/B
- [ ] M-05 Point-in-time discipline for every prompt input; leakage spot-checks
- [ ] M-06 Survivorship/selection: universes frozen pre-inference, delistings retained
- [ ] M-07 Sim-price vs signal confusion resolved (what exactly is scored?)

**Methodology & statistics**
- [ ] M-08 Baselines incl. single-strong-LLM on identical inputs; ablations defined
- [ ] M-09 IC / DM / DSR specified; trial registry; multiplicity handled
- [ ] M-10 Kill criteria numeric and gate-attached
- [ ] M-11 Herding/degenerate-consensus failure anticipated and measured

**Feasibility & engineering**
- [ ] M-12 Compute math explicit, conservative, and gated by measurement (not vibes)
- [ ] M-13 Data availability verified or explicitly gated (feeds, depth, licensing)
- [ ] M-14 Reproducibility: manifests, hashes, seeds, resume-safe jobs, tests green
- [ ] M-15 Budget ≤ $100 with levers; spot-preemption tolerated

**Ethics/compliance/presentation**
- [ ] M-16 ToS-clean compute plan; no manipulation pathway; not-investment-advice
- [ ] M-17 No redistribution of licensed raw data
- [ ] M-18 Docs read as finance-ML research (not generic ML); structure navigable

---

## STAGE 2/3: PASSES

#### [QC Pass #1 of 10]
1. **Fresh-Mind Baseline:** First-draft framing was "simulate retail with LLM agents
   and see how well it predicts the stock" — a single unfalsifiable headline bet
   with ~0 prior probability of a clean win; as an ICAIF submission it would be
   rejected for overclaiming, as an investor doc it sets up failure.
2. **Benchmark Comparison:** TwinMarket (arXiv:2502.01506) and Lopez-Lira 2025
   (arXiv:2504.10789) both succeed by claiming *realism/mechanism findings*, not
   alpha; Lopez-Lira & Tang (JFE) shows how prediction claims are framed credibly.
3. **Checklist Audit:** M-01 FAIL (goal buried), M-02 FAIL (no registered RQs, null
   has no value), M-03 PARTIAL.
4. **Actioned Revisions:** Reframed the entire project around three registered RQs
   (realism, behavioral fidelity, incremental information); wrote the "null RQ3 is
   still a fundable PoC" logic into PLAN §0–1 and README's 30-second pitch.

#### [QC Pass #2 of 10]
1. **Fresh-Mind Baseline:** With RQs fixed, the largest remaining hole: every
   candidate model's training data contains the 2018–2021 meme era; any backtest
   there is contaminated by memorization.
2. **Benchmark Comparison:** Glasserman & Lin (arXiv:2309.17322) anonymization
   methodology; Look-Ahead-Bench (arXiv:2601.13770) as current-practice bar.
3. **Checklist Audit:** M-04 FAIL (no cutoff policy), M-05 PARTIAL (point-in-time
   stated but unenforced).
4. **Actioned Revisions:** Added D-04 (OOS strictly post max-cutoff, frozen at G1),
   D-05 (Robintrack era demoted to calibration-only), D-06 + C-1..C-3 (cutoff gate,
   recall probes with exclusion rule, anonymization A/B in every arm), L-01..L-04
   enforced in `prompt_builder` with a human spot-check at G1.

#### [QC Pass #3 of 10]
1. **Fresh-Mind Baseline:** Suppose RQ3 shows positive IC — reviewer's first
   question: "is the *crowd* doing anything, or would one strong LLM on the same
   inputs do the same?" Draft had no answer.
2. **Benchmark Comparison:** Lopez-Lira & Tang single-model sentiment (the incumbent
   text baseline); MASS (arXiv:2505.10278) motivates agent-count scaling curves.
3. **Checklist Audit:** M-08 FAIL, M-09 PARTIAL (metrics named, no trial registry),
   M-10 PARTIAL.
4. **Actioned Revisions:** D-09 mandatory baseline suite (single-strong-LLM on
   identical inputs, momentum 1/5/20, AR(1), logistic on same features); A-402
   scaling curve N∈{50,100,300,1000}; docs/TRIALS.md registry wired into DSR (D-11);
   numeric kill criteria attached to G2/G3 (≥99% valid-JSON; sign-agreement ≤52%
   both arms ⇒ stop).

#### [QC Pass #4 of 10]
1. **Fresh-Mind Baseline:** Original diversification list included MC-dropout;
   inference engines (vLLM) run dropout-disabled, and hacking it in is exactly the
   "technical novelty" the constraints forbid. Budget math also relied on
   unmeasured throughput.
2. **Benchmark Comparison:** Standard vLLM offline-batching practice; T4 (SM75)
   known limitations vs newer GPUs.
3. **Checklist Audit:** M-12 FAIL (no measurement gate; optimistic tokens/s),
   D-07 inconsistent with K-3.
4. **Actioned Revisions:** Dropped MC-dropout (D-07) in favor of model×persona×
   temperature×seed; added `p0_gate_throughput.py` as a blocking gate; recomputed
   FEASIBILITY table at a conservative 5k decisions/hr and $0.30/hr spot with
   explicit levers if measurement halves throughput.

#### [QC Pass #5 of 10]
1. **Fresh-Mind Baseline:** Data assumptions were the weakest empirical claims:
   "Alpaca free historical data" was asserted without feed semantics; small-cap
   IEX sparsity unaddressed; news depth unknown; licensing/redistribution unstated.
2. **Benchmark Comparison:** Alpaca Market Data docs + community threads (free =
   real-time IEX, 15-min-delayed SIP; historical older than 15 min queryable);
   Robintrack archive coverage 2018-05-02→2020-08-13, ~8.5k tickers (Welch 2022
   cleaning conventions).
3. **Checklist Audit:** M-13 PARTIAL, M-17 FAIL (no licensing note).
4. **Actioned Revisions:** `p0_gate_data.py` now records a per-feed matrix, earliest
   bar/news dates, and Robintrack integrity before anything runs (F-03/F-04 hedges
   added); data/README.md forbids committing/redistributing raw vendor data;
   loaders raise remediation-bearing errors on 401/403/429.

#### [QC Pass #6 of 10]
1. **Fresh-Mind Baseline:** Conceptual confusion risk: readers (and we) could
   conflate "simulated price tracks real price" with "simulated flow predicts real
   returns" — the former is neither needed nor claimed.
2. **Benchmark Comparison:** MarS (arXiv:2409.07486) = generative realism route;
   Lopez-Lira 2025 = mechanism route; neither scores sim-price tracking, which
   validates the separation.
3. **Checklist Audit:** M-07 FAIL in draft prose; M-11 FAIL (no herding metric).
4. **Actioned Revisions:** D-01 two-track design made explicit everywhere
   (`flow_imbalance` = scored signal; `call_auction` = realism only); F-06 added
   with a daily decision-entropy diagnostic and a temperature/persona-spread
   response, reported as a finding rather than silently patched.

#### [QC Pass #7 of 10]
1. **Fresh-Mind Baseline:** Statistics pass: are the reported numbers the ones a
   referee would compute? IC defined? DM horizon? DSR inputs? Survivorship?
2. **Benchmark Comparison:** Diebold–Mariano standard usage at h=1; Bailey &
   López de Prado DSR (same discipline as the user's GMDA/TACTIC-MoB projects);
   Welch 2022 daily-last-observation convention for Robintrack.
3. **Checklist Audit:** M-09 PARTIAL (DM lag handling unstated), M-06 PARTIAL
   (delistings unmentioned).
4. **Actioned Revisions:** Implemented IC (Spearman with tie-averaged ranks), DM
   with truncated LRV at horizon h, and DSR with expected-max-SR null in
   `evals/prediction.py` + unit tests (perfect-signal, better-forecast, trial-count
   penalization); U-C/U-O rules retain delistings and freeze selection dates;
   pooled + per-ticker reporting with block-bootstrap CIs specified in A-501.

#### [QC Pass #8 of 10]
1. **Fresh-Mind Baseline:** Reproducibility/engineering: would a clean machine +
   the archived artifacts regenerate every number? Would a spot kill corrupt a run?
2. **Benchmark Comparison:** ICAIF artifact-badge norms; the user's own
   backup-first IDE-agent conventions.
3. **Checklist Audit:** M-14 PARTIAL (manifest existed; resume logic and tests
   incomplete).
4. **Actioned Revisions:** Request-id ledger + chunked JSONL append in
   `vllm_batch.py` (idempotent reruns; ≤1 chunk loss on preemption, F-01/F-02);
   `RunManifest` made mandatory-by-policy and covered by a test; persona bank and
   prompts content-hashed; suite now 14 tests, all passing; stub smoke exercises
   the full pipe including auction price movement.

#### [QC Pass #9 of 10]
1. **Fresh-Mind Baseline:** Ethics/compliance read as an outside counsel would:
   compute sourcing, market-manipulation optics, advice liability, data licensing.
2. **Benchmark Comparison:** Google Cloud free-trial terms (one promotional credit
   per customer); standard ethics statements in finance-ML papers.
3. **Checklist Audit:** M-16 FAIL in original *idea prompt* (multi-account credit
   farming), M-17 now PASS after Pass 5.
4. **Actioned Revisions:** Multi-account farming excluded and documented as a ToS
   violation (K-4, DECISION_MEMO); legitimate expansion paths listed (research
   credits, academic programs, TPU Research Cloud); explicit "prediction-only, no
   posting/trading/influence pathway" statement; "not investment advice" added to
   README, PLAN honesty box, and DECISION_MEMO.

#### [QC Pass #10 of 10]
1. **Fresh-Mind Baseline:** Final end-to-end read as an ICAIF referee + a skeptical
   angel investor. The 30-second pitch lands (README ¶1); every claim routes to a
   gate, metric, or citation; the plan survives its own kill criteria.
2. **Benchmark Comparison:** Median accepted ICAIF simulation paper (single-market
   sim, stylized facts, limited baselines, weak contamination handling): this plan
   exceeds that bar on contamination controls (C-1..C-3 + A/B arms), baseline
   strength (D-09), and pre-registration (TRIALS.md). It is *below* frontier work
   (MarS-scale engineering) on simulator sophistication — by design (K-3).
3. **Checklist Audit:** M-01..M-18 PASS or PASS-with-gate (M-12/M-13 pass
   conditional on G0 measurements, as intended). Residual risks, explicitly
   accepted: (R1) 1.5–3B agents may be behaviorally too weak / "too rational" —
   protected by G2/G3 kills, flagged by the behavioral-consistency literature;
   (R2) free small-cap bar coverage may force universe changes — F-03 lever;
   (R3) RQ3 likely null — reframed as a valid measured outcome.
4. **Actioned Revisions:** None required beyond copy-edits; convergence reached
   (Pass 10 introduced no new substantive failures).

---

## VERDICT
The plan, memo, and repo now (a) state a falsifiable, venue-appropriate
contribution inside 30 seconds, (b) neutralize the two standard killers of LLM
backtests (look-ahead/memorization; leaky point-in-time discipline) with measured
controls rather than assertions, (c) pre-register trials and kill criteria, and
(d) fit the $100 compute envelope with a measurement gate before spend. Remaining
uncertainty is empirical, not structural, and is priced into the gates.
