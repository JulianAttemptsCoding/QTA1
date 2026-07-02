# FEASIBILITY.md — Data audit and compute/cost model

Everything marked (G0) is a planning assumption that `scripts/p0_gate_data.py` /
`p0_gate_throughput.py` must confirm before money is spent.

## 1. Data audit (free/public only)

| Source | What we take | Status |
|---|---|---|
| Alpaca Market Data (free/Basic plan) | Historical daily + minute bars. Free plan = real-time IEX plus 15-minute-delayed SIP; for backtests the delay is irrelevant. (G0: confirm which `feed` values your keys accept for historical pulls and earliest available dates; small caps on IEX-only bars are sparse — F-03.) | Primary prices |
| Alpaca News API (`/v1beta1/news`) | Timestamped headlines per ticker as the agents' event feed. (G0: confirm historical depth on free keys; fallback F-04 = EDGAR 8-K/press releases.) | Primary text |
| SEC EDGAR (free) | Filings text, shares outstanding for cap filters, 8-K fallback feed. Respect fair-access rate limits; set a real User-Agent. | Fundamentals/fallback |
| FRED (free) | Optional macro context lines in prompts (rates, VIX-adjacent series). | Optional |
| Robintrack archive (public download, 2018-05-02 → 2020-08-13) | Robinhood holder counts per ticker (~8.5k tickers) — the ground-truth retail behavior series for RQ2 and the CALIB universe filter. Used per Welch-style daily-last-observation convention. | Calibration only (D-05) |
| Explicitly NOT used | TAQ/BJZZ retail imputation (paid), Nasdaq retail tracker (paid), Reddit dumps (API limits / dead archives — may revisit) | — |

## 2. Model shortlist (T4 16 GB, fp16 or 4-bit)

Qwen2.5-1.5B/3B-Instruct, Llama-3.2-3B-Instruct, Phi-3.5-mini, Gemma-2-2B-it.
Cutoffs read from model cards at G0 and *tested* via contamination probes (C-2);
the OOS window starts strictly after the max verified cutoff (D-04).

## 3. Compute model (planning numbers)

- Workload per decision: ~900 input tokens (persona + 30 daily bars + ≤5 headlines
  + position) and ≤160 output tokens of JSON.
- Planning throughput: **5,000 decisions/hour** per spot T4 with a 1.5B model under
  vLLM continuous batching (conservative; T4 is an older SM75 part — measure at G0;
  optimistic case 2–3×).
- Planning price: spot n1-standard-8 + T4 ≈ **$0.30/hr**; on-demand ≈ $0.75/hr.

| Phase | Decisions | T4-hours @5k/hr | Spot $ |
|---|---:|---:|---:|
| P0 gates + P2 bring-up | ~10k | 2 | 1 |
| P3 calibration (10 tkr × 100 ag × 126 d × 2 arms) | 252k | 50 | 15 |
| P4 main OOS (10 × 200 × 125) | 250k | 50 | 15 |
| P4 scaling curve (2 × {50,100,300,1000} × 60) | 174k | 35 | 11 |
| P4 ablations (news-off, personas-off) | 24k | 5 | 2 |
| Contingency 30% + on-demand fallback risk | — | — | 15–30 |
| **Total** | **~710k** | **~142** | **≈ $60–75** |

Levers if G0 halves throughput: 5 OOS tickers first (−$8), 60-day OOS pilot before
extension (−$8), drop the 1000-agent scaling point (−$6).

## 4. Storage/network

Snapshots + JSONL logs ≈ a few GB; GCS standard storage cost is noise (<$1/mo).

## 5. Legitimate compute expansion (in order)

1. GCP research credits application (academic project, public-good framing).
2. TPU Research Cloud (free TPU quota; vLLM has TPU support) — port is a config
   change, not a rewrite.
3. Larger paid quota only after a positive G3.
Multi-account free-trial farming is excluded (ToS; see DECISION_MEMO).
