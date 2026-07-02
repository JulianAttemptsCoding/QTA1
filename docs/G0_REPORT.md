# G0 Data Gate Report

- Generated UTC: 2026-07-02T22:11:00.966985+00:00
- Overall: **PASS**
- Secrets hygiene: report records only environment variable names, never values.

## Environment Names

| Name | Present |
|---|---|
| APCA_API_KEY_ID | True |
| APCA_API_SECRET_KEY | True |
| FRED_API_KEY | True |
| GCP_PROJECT | False |
| GCS_BUCKET | False |
| GOOGLE_CLOUD_PROJECT | False |
| HF_TOKEN | False |
| SEC_API_USER_AGENT | False |

## Check Summary

| Check | Status | Detail |
|---|---|---|
| alpaca_bars_feed_matrix | PASS | Historical bars returned for liquid and small-cap probes; workable feeds: (default), iex, sip. |
| alpaca_news_depth | PASS | Returned 50 articles; earliest sample article: 2018-01-01T21:11:29Z. |
| robintrack_archive | PASS | Robintrack sample CSVs loaded. |
| edgar_ping | PASS | SEC EDGAR companyfacts returned facts for AAPL. |
| fred_ping | PASS | FRED observations endpoint returned data. |

## alpaca_bars_feed_matrix Details

| symbol | timeframe | feed | http_status | bar_count | earliest | latest_sample | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL | 1Day | (default) | 200 | 2637 | 2016-01-04T05:00:00Z | 2026-06-30T04:00:00Z |  |
| AAPL | 1Min | (default) | 200 | 10000 | 2016-01-01T00:00:00Z | 2016-01-22T19:34:00Z |  |
| KOSS | 1Day | (default) | 200 | 2637 | 2016-01-04T05:00:00Z | 2026-06-30T04:00:00Z |  |
| KOSS | 1Min | (default) | 200 | 10000 | 2016-01-04T16:20:00Z | 2018-05-14T19:56:00Z |  |
| MVIS | 1Day | (default) | 200 | 2637 | 2016-01-04T05:00:00Z | 2026-06-30T04:00:00Z |  |
| MVIS | 1Min | (default) | 200 | 10000 | 2016-01-04T14:30:00Z | 2016-03-30T15:48:00Z |  |
| SNDL | 1Day | (default) | 200 | 1737 | 2019-08-01T04:00:00Z | 2026-06-30T04:00:00Z |  |
| SNDL | 1Min | (default) | 200 | 10000 | 2019-08-01T16:08:00Z | 2019-09-20T15:27:00Z |  |
| AAPL | 1Day | iex | 200 | 1489 | 2020-07-27T04:00:00Z | 2026-06-30T04:00:00Z |  |
| AAPL | 1Min | iex | 200 | 10000 | 2020-07-27T13:30:00Z | 2020-09-03T15:01:00Z |  |
| KOSS | 1Day | iex | 200 | 1405 | 2020-07-27T04:00:00Z | 2026-06-30T04:00:00Z |  |
| KOSS | 1Min | iex | 200 | 10000 | 2020-07-27T14:39:00Z | 2021-06-18T13:32:00Z |  |
| MVIS | 1Day | iex | 200 | 1489 | 2020-07-27T04:00:00Z | 2026-06-30T04:00:00Z |  |
| MVIS | 1Min | iex | 200 | 10000 | 2020-07-27T13:45:00Z | 2021-01-05T17:22:00Z |  |
| SNDL | 1Day | iex | 200 | 1489 | 2020-07-27T04:00:00Z | 2026-06-30T04:00:00Z |  |
| SNDL | 1Min | iex | 200 | 10000 | 2020-07-27T16:43:00Z | 2021-01-06T18:09:00Z |  |
| AAPL | 1Day | sip | 200 | 2637 | 2016-01-04T05:00:00Z | 2026-06-30T04:00:00Z |  |
| AAPL | 1Min | sip | 200 | 10000 | 2016-01-01T00:00:00Z | 2016-01-22T19:34:00Z |  |
| KOSS | 1Day | sip | 200 | 2637 | 2016-01-04T05:00:00Z | 2026-06-30T04:00:00Z |  |
| KOSS | 1Min | sip | 200 | 10000 | 2016-01-04T16:20:00Z | 2018-05-14T19:56:00Z |  |
| MVIS | 1Day | sip | 200 | 2637 | 2016-01-04T05:00:00Z | 2026-06-30T04:00:00Z |  |
| MVIS | 1Min | sip | 200 | 10000 | 2016-01-04T14:30:00Z | 2016-03-30T15:48:00Z |  |
| SNDL | 1Day | sip | 200 | 1737 | 2019-08-01T04:00:00Z | 2026-06-30T04:00:00Z |  |
| SNDL | 1Min | sip | 200 | 10000 | 2019-08-01T16:08:00Z | 2019-09-20T15:27:00Z |  |

## alpaca_news_depth Details

| symbol | day | article_count |
| --- | --- | --- |
| AAPL | 2018-01-01 | 1 |
| AAPL | 2018-01-02 | 7 |
| AAPL | 2018-01-03 | 8 |
| AAPL | 2018-01-04 | 2 |
| AAPL | 2018-01-05 | 7 |
| AAPL | 2018-01-06 | 2 |
| AAPL | 2018-01-07 | 2 |
| AAPL | 2018-01-08 | 9 |
| AAPL | 2018-01-09 | 3 |
| KOSS | 2018-01-02 | 7 |
| KOSS | 2018-01-03 | 1 |
| KOSS | 2018-01-09 | 1 |

## robintrack_archive Details

| symbol | path | rows | first_timestamp | last_timestamp |
| --- | --- | --- | --- | --- |
| AAPL | data\raw\robintrack\tmp\popularity_export\AAPL.csv | 19792 | 2018-05-02 04:53:46 | 2020-08-13 22:55:09 |
| TSLA | data\raw\robintrack\tmp\popularity_export\TSLA.csv | 19800 | 2018-05-02 04:53:19 | 2020-08-13 22:54:47 |
| GME | data\raw\robintrack\tmp\popularity_export\GME.csv | 19795 | 2018-05-02 04:53:32 | 2020-08-13 22:54:57 |

## edgar_ping Details

| endpoint | http_status |
| --- | --- |
| SEC companyfacts AAPL | 200 |

## fred_ping Details

| endpoint | http_status |
| --- | --- |
| FRED DFF observations | 200 |
