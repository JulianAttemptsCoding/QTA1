# G0_REPORT — data reality gate (A-002)

Generated (UTC): 2026-07-02T22:11:30.389961+00:00

**GATE G0 (data): PASS**
Hard checks (must PASS): ['alpaca_bars_smallcap', 'alpaca_news_depth']. Hard failures: none

| check | status | detail |
|---|---|---|
| alpaca_bars_liquid | PASS | 20 daily bars AAPL Jan2016 (sip); earliest_in_window=2016-01-04T05:00:00Z |
| smallcap_feed_probe | INFO | feed=iex/2019H2: {'GPRO': 0, 'SGMO': 0, 'PLUG': 0} |
| smallcap_feed_probe | INFO | feed=iex/recent: {'GPRO': 60, 'SGMO': 60, 'PLUG': 60} |
| smallcap_feed_probe | INFO | feed=sip/2019H2: {'GPRO': 128, 'SGMO': 128, 'PLUG': 128} |
| smallcap_feed_probe | INFO | feed=sip/recent: {'GPRO': 60, 'SGMO': 60, 'PLUG': 60} |
| smallcap_feed_probe | INFO | feed=default/2019H2: {'GPRO': 128, 'SGMO': 128, 'PLUG': 128} |
| smallcap_feed_probe | INFO | feed=default/recent: {'GPRO': 60, 'SGMO': 60, 'PLUG': 60} |
| alpaca_bars_smallcap | PASS | at least one feed/window returned smallcap daily bars: True |
| alpaca_news_depth | PASS | earliest_news=2015-01-01T19:14:12Z; 60d smallcap counts {'GPRO': 10, 'SGMO': 9, 'PLUG': 39} |
| edgar_ping | PASS | companyfacts entityName=Apple Inc. |
| fred_ping | PASS | series GDP ok: Gross Domestic Product |
| robintrack_archive | SOFT-BLOCK | no local export; source reachability {'robintrack.net': 200, 'github_ameobea': 200}; CALIB-only (P3), see notes.md BLOCKER |

## Feed matrix (smallcap daily bar counts)
```
{
  "feed=iex/2019H2": {
    "GPRO": 0,
    "SGMO": 0,
    "PLUG": 0
  },
  "feed=iex/recent": {
    "GPRO": 60,
    "SGMO": 60,
    "PLUG": 60
  },
  "feed=sip/2019H2": {
    "GPRO": 128,
    "SGMO": 128,
    "PLUG": 128
  },
  "feed=sip/recent": {
    "GPRO": 60,
    "SGMO": 60,
    "PLUG": 60
  },
  "feed=default/2019H2": {
    "GPRO": 128,
    "SGMO": 128,
    "PLUG": 128
  },
  "feed=default/recent": {
    "GPRO": 60,
    "SGMO": 60,
    "PLUG": 60
  }
}
```
