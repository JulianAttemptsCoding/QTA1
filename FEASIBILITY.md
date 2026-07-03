# FEASIBILITY.md - Data audit and compute/cost model

G0 has now replaced the original planning assumptions with measured data and
throughput checks. See `docs/G0_REPORT.md`, `docs/G0_THROUGHPUT.md`, and
`docs/FEASIBILITY_ADDENDUM.md` for the detailed evidence.

## 1. Data audit

| Source | What we take | G0 status |
|---|---|---|
| Alpaca Market Data | Historical daily and minute bars for liquid and retail-heavy small-cap probes. | PASS: default, IEX, and SIP historical feeds returned usable bars. |
| Alpaca News API (`/v1beta1/news`) | Timestamped headlines per ticker as the agents' event feed. | PASS: historical sample returned 50 articles with coverage back to 2018-01-01 in the probe. |
| SEC EDGAR | Filings text, shares outstanding for cap filters, and 8-K fallback feed. | PASS: companyfacts endpoint returned AAPL facts with a compliant User-Agent. |
| FRED | Optional macro context lines in prompts. | PASS: observations endpoint returned data. |
| Robintrack archive | Robinhood holder counts for calibration-era retail-crowd behavior. | PASS: public archive sample loaded for AAPL, TSLA, and GME. |
| Explicitly not used | TAQ/BJZZ retail imputation, paid Nasdaq retail tracker, Reddit dumps. | Excluded by plan constraints or current API/licensing risks. |

Raw vendor/public archives remain untracked under ignored `data/raw/`.

## 2. Model shortlist

G0 cached and measured the ungated open-weight set on Vertex AI T4 workers:

| Model | G0 role | Notes |
|---|---|---|
| `HuggingFaceTB/SmolLM2-1.7B-Instruct` | Primary budget model | Best measured throughput: 4,747 decisions/hour; valid JSON 0.988. |
| `Qwen/Qwen2.5-1.5B-Instruct` | Diversity / fallback | 2,541 decisions/hour; valid JSON 1.000. |
| `Qwen/Qwen2.5-3B-Instruct` | Diversity / fallback | 2,203 decisions/hour; valid JSON 0.990. |
| `microsoft/Phi-3.5-mini-instruct` | Diversity only unless budget allows | 1,907 decisions/hour; valid JSON 1.000 with eager mode. |

The gated Llama/Gemma pair remains disabled for this run because the supplied HF
credential was not authorized for the gated Llama repo. P-05 permits continuing
with the ungated four-model set.

## 3. Measured compute model

- G0 worker: Vertex AI custom job, `n1-standard-8`, 1x NVIDIA_TESLA_T4, spot.
- Price assumption: `$0.30/hr` for the combined spot worker/GPU planning rate.
- Selected budget rate: `4,747` decisions/hour from SmolLM2.
- G0 kill threshold: `>= 2,000` decisions/hour on a selectable worker/model.
- JSON validity threshold: `>= 0.900`; lowest accepted G0 rate was `0.988`.

| Phase | Decisions | T4-hours @4,747/hr | Spot $ |
|---|---:|---:|---:|
| P0 gates + P2 bring-up | ~10k | 2.1 | 1 |
| P3 calibration (10 tkr x 100 ag x 126 d x 2 arms) | 252k | 53.1 | 16 |
| P4 main OOS (10 x 200 x 125) | 250k | 52.7 | 16 |
| P4 scaling curve (2 x {50,100,300,1000} x 60) | 174k | 36.7 | 11 |
| P4 ablations (news-off, personas-off) | 24k | 5.1 | 2 |
| Contingency 30% + on-demand fallback risk | - | - | 15-30 |
| **Total** | **~710k** | **~150** | **~$61-76** |

The measured rate is close to the original 5,000 decisions/hour planning number,
so the project remains inside the $100 envelope. If later phases run more than
30% slower than G0, G4 requires pausing and replanning before more spend.

## 4. Storage/network

Snapshots and JSONL logs are expected to be a few GB. GCS standard storage cost is
noise relative to GPU spend (<$1/month at this scale).

## 5. Legitimate compute expansion

1. GCP research credits application.
2. TPU Research Cloud or Vertex TPU trial only if the runtime port is minimal.
3. Larger paid quota only after a positive G3.

Multi-account free-trial farming remains excluded as a ToS violation.
