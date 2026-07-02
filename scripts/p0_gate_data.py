"""GATE G0 (data): run once with real keys; writes docs/G0_REPORT.md. See PLAN A-002.

Hard-gate (PLAN G0 kill criteria): a workable historical bar feed for small caps AND
usable news history. EDGAR/FRED are recorded but do not by themselves fail G0.
Robintrack is a SOFT blocker (CALIB-only, P3) per PLAN section 4.

Secret hygiene (R4): never print secret values. The FRED key travels in a URL, so any
error text is sanitized before it reaches stdout / the report.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> None:
    envf = ROOT / ".env"
    if not envf.exists():
        return
    for line in envf.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()
sys.path.insert(0, str(ROOT / "src"))
from agorasim.data.alpaca_bars import iter_bars  # noqa: E402
from agorasim.data.alpaca_news import iter_news  # noqa: E402

LIQUID = "AAPL"
SMALLCAPS = ["GPRO", "SGMO", "PLUG"]
results: list[tuple[str, str, str]] = []
feed_matrix: dict[str, object] = {}


def rec(check: str, status: str, detail: str) -> None:
    results.append((check, status, detail))
    print(f"[{status}] {check}: {detail}")


# ---- 1. liquid bars + earliest available ----
try:
    bars = list(iter_bars([LIQUID], "2016-01-01", "2016-02-01", feed="sip"))
    earliest = min((b["t"] for b in bars), default=None)
    rec("alpaca_bars_liquid", "PASS" if bars else "FAIL",
        f"{len(bars)} daily bars {LIQUID} Jan2016 (sip); earliest_in_window={earliest}")
except Exception as e:  # noqa: BLE001
    rec("alpaca_bars_liquid", "FAIL", f"{type(e).__name__}: {str(e)[:160]}")

# ---- 2. smallcap feed matrix (the hard bar check) ----
windows = {"2019H2": ("2019-07-01", "2019-12-31"), "recent": ("2025-01-02", "2025-03-31")}
hard_bars_ok = False
for feed in ["iex", "sip", None]:
    for wname, (s, e) in windows.items():
        key = f"feed={feed or 'default'}/{wname}"
        try:
            counts = {t: len(list(iter_bars([t], s, e, feed=feed))) for t in SMALLCAPS}
            feed_matrix[key] = counts
            if sum(counts.values()) > 0:
                hard_bars_ok = True
            rec("smallcap_feed_probe", "INFO", f"{key}: {counts}")
        except Exception as ex:  # noqa: BLE001
            feed_matrix[key] = f"ERR {type(ex).__name__}"
            rec("smallcap_feed_probe", "INFO", f"{key}: {type(ex).__name__}: {str(ex)[:100]}")
rec("alpaca_bars_smallcap", "PASS" if hard_bars_ok else "FAIL",
    f"at least one feed/window returned smallcap daily bars: {hard_bars_ok}")

# ---- 3. news depth (hard news check) ----
try:
    first = next(iter(iter_news([LIQUID], "2015-01-01", "2025-01-01", sort="asc", limit=50)), None)
    earliest_news = first.get("created_at") if first else None
    end = dt.date(2025, 3, 31)
    start = end - dt.timedelta(days=60)
    perday = {t: len(list(iter_news([t], start.isoformat(), end.isoformat(),
                                    sort="asc", limit=50))) for t in SMALLCAPS}
    ok = earliest_news is not None
    rec("alpaca_news_depth", "PASS" if ok else "FAIL",
        f"earliest_news={earliest_news}; 60d smallcap counts {perday}")
except Exception as e:  # noqa: BLE001
    rec("alpaca_news_depth", "FAIL", f"{type(e).__name__}: {str(e)[:160]}")

# ---- 4. EDGAR reachability ----
try:
    ua = os.getenv("SEC_USER_AGENT") or os.getenv("SEC_API_USER_AGENT") or "agorasim research"
    req = urllib.request.Request(
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
        headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=30) as resp:
        j = json.load(resp)
    rec("edgar_ping", "PASS", f"companyfacts entityName={j.get('entityName')}")
except Exception as e:  # noqa: BLE001
    rec("edgar_ping", "FAIL", f"{type(e).__name__}: {str(e)[:160]}")

# ---- 5. FRED (optional; sanitize key from any error) ----
fred = os.getenv("FRED_API_KEY")
if not fred:
    rec("fred_ping", "SKIP", "FRED_API_KEY absent (optional)")
else:
    try:
        url = f"https://api.stlouisfed.org/fred/series?series_id=GDP&api_key={fred}&file_type=json"
        with urllib.request.urlopen(url, timeout=30) as resp:
            j = json.load(resp)
        title = (j.get("seriess") or [{}])[0].get("title", "?")
        rec("fred_ping", "PASS", f"series GDP ok: {title[:40]}")
    except Exception as e:  # noqa: BLE001
        rec("fred_ping", "FAIL", f"{type(e).__name__}: {str(e)[:160].replace(fred, '***')}")

# ---- 6. Robintrack (SOFT blocker; CALIB-only) ----
rt_dir = ROOT / "data" / "raw" / "robintrack" / "popularity_export"
try:
    csvs = list(rt_dir.glob("*.csv")) if rt_dir.exists() else []
    if csvs:
        from agorasim.data.robintrack import load_ticker_csv
        counts = {p.stem: len(load_ticker_csv(p)) for p in csvs[:3]}
        rec("robintrack_archive", "PASS", f"local export present ({len(csvs)} files); sample daily rows {counts}")
    else:
        reach = {}
        for name, url in [("robintrack.net", "https://robintrack.net/data-download"),
                          ("github_ameobea", "https://github.com/Ameobea/robintrack")]:
            try:
                req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "agorasim"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    reach[name] = resp.status
            except Exception as ex:  # noqa: BLE001
                reach[name] = type(ex).__name__
        rec("robintrack_archive", "SOFT-BLOCK",
            f"no local export; source reachability {reach}; CALIB-only (P3), see notes.md BLOCKER")
except Exception as e:  # noqa: BLE001
    rec("robintrack_archive", "SOFT-BLOCK", f"{type(e).__name__}: {str(e)[:160]}")

# ---- gate decision + report ----
hard_checks = {"alpaca_bars_smallcap", "alpaca_news_depth"}
hard_fail = [c for (c, s, _d) in results if c in hard_checks and s == "FAIL"]
gate = "FAIL" if hard_fail else "PASS"

docs = ROOT / "docs"
docs.mkdir(exist_ok=True)
lines = [
    "# G0_REPORT — data reality gate (A-002)", "",
    f"Generated (UTC): {dt.datetime.now(dt.timezone.utc).isoformat()}", "",
    f"**GATE G0 (data): {gate}**",
    f"Hard checks (must PASS): {sorted(hard_checks)}. Hard failures: {hard_fail or 'none'}", "",
    "| check | status | detail |", "|---|---|---|",
]
for c, s, d in results:
    lines.append(f"| {c} | {s} | {str(d).replace('|', '/')} |")
lines += ["", "## Feed matrix (smallcap daily bar counts)", "```",
          json.dumps(feed_matrix, indent=2), "```", ""]
(docs / "G0_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(f"\nGATE G0 (data): {gate}  -> docs/G0_REPORT.md")
sys.exit(0 if gate == "PASS" else 1)
