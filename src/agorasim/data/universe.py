"""Universe construction rules (documented, mechanical, no discretion after G1 freeze).

CALIB-2019 (behavior-fidelity track, Robintrack era):
  U-C1 common shares, primary US listing, price >= $1 on selection date
  U-C2 market cap between $50M and $2B (small cap)
  U-C3 retail-heavy proxy: top decile of Robinhood holders / (shares outstanding)
  U-C4 pick 10 tickers by rank, selection date 2019-06-28, hold fixed

OOS-20xx (prediction track, strictly post model-cutoff; concrete dates set at G1):
  U-O1 same share-class / price / cap filters, evaluated point-in-time
  U-O2 retail-heavy proxy WITHOUT paid data: rank by (a) count of Alpaca news items
       mentioning the ticker over trailing 60d, (b) dollar-volume spike ratio,
       (c) lot-size proxy if available; document exact formula before the freeze
  U-O3 pick 10 tickers; freeze BEFORE any agent inference is run (no peeking)

Anti-survivorship: selection uses only information available on the selection date;
delistings during the window stay in the sample with delisting returns where computable.
"""
