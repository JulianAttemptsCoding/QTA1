# Data directory (nothing raw is committed)

- `raw/`       downloaded API pulls and the Robintrack archive (gitignored)
- `snapshots/` frozen, hashed point-in-time datasets referenced by run manifests (gitignored)

Licensing note (verify at G0): Alpaca/IEX-derived data is for your own research use;
do NOT redistribute raw bars in this repo or in the PoC package. Robintrack's archive
is publicly downloadable from robintrack.net/data-download; cite it, link it, don't rehost.
