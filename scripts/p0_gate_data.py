"""GATE G0 (data): run once with real keys; writes docs/G0_REPORT.md. Checks:
1. Alpaca /v2/stocks/bars answers for a liquid ticker AND a small cap; record which
   `feed` values work on the free plan and the earliest available minute/daily bar.
2. Alpaca /v1beta1/news answers; record earliest available article date.
3. Robintrack archive downloaded + row counts for 3 sample tickers.
4. SEC EDGAR + FRED reachable with configured credentials.
Exit nonzero if any check fails: NOTHING downstream runs until G0 = PASS.
"""
import sys

CHECKS = ["alpaca_bars_liquid", "alpaca_bars_smallcap_feed_matrix", "alpaca_news_depth",
          "robintrack_archive", "edgar_ping", "fred_ping"]

if __name__ == "__main__":
    print("Implement checks in order; each writes a PASS/FAIL line to docs/G0_REPORT.md:")
    for c in CHECKS:
        print(" -", c)
    sys.exit(1)  # intentionally failing until implemented + run with real keys
