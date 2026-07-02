"""GATE G0 (data): run once with real keys; writes docs/G0_REPORT.md.

Checks:
1. Alpaca /v2/stocks/bars answers for one liquid ticker and three small caps;
   record which `feed` values work and the earliest minute/daily bars observed.
2. Alpaca /v1beta1/news answers; record earliest available article date and
   per-day article counts for three tickers.
3. Robintrack archive exists or can be downloaded; record row counts for samples.
4. SEC EDGAR and FRED are reachable with configured credentials.

Robintrack unavailability is a soft blocker per the execution prompt: P3/CALIB
cannot run, but OOS-side work may continue. Other failed checks make G0 fail.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import tarfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ALPACA_BARS_URL = "https://data.alpaca.markets/v2/stocks/bars"
ALPACA_NEWS_URL = "https://data.alpaca.markets/v1beta1/news"
EDGAR_COMPANYFACTS_AAPL = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
ROBINTRACK_ARCHIVE_URL = "https://robintrack-data.ameo.design/robintrack-popularity-history.tar.gz"

LIQUID_SYMBOL = "AAPL"
SMALLCAP_SYMBOLS = ["KOSS", "MVIS", "SNDL"]
NEWS_SYMBOLS = ["AAPL", "KOSS", "MVIS"]
ROBINTRACK_SAMPLE_SYMBOLS = ["AAPL", "TSLA", "GME"]
FEEDS: list[str | None] = [None, "iex", "sip"]

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "G0_REPORT.md"
ROBINTRACK_ROOT = ROOT / "data" / "raw" / "robintrack"
ROBINTRACK_ARCHIVE = ROBINTRACK_ROOT / "robintrack-popularity-history.tar.gz"


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str
    rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def hard_failed(self) -> bool:
        return self.status == "FAIL"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_dotenv(path: Path) -> dict[str, str]:
    """Tiny .env loader so local dev does not need python-dotenv."""
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            loaded[key] = value
            os.environ.setdefault(key, value)
    return loaded


def alpaca_headers() -> dict[str, str]:
    key = os.getenv("APCA_API_KEY_ID")
    secret = os.getenv("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise RuntimeError("Missing APCA_API_KEY_ID/APCA_API_SECRET_KEY names in .env.")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}


def get_json(url: str, *, params: dict[str, Any] | None = None,
             headers: dict[str, str] | None = None, timeout: int = 45) -> tuple[int, Any]:
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    if response.status_code == 429:
        time.sleep(2)
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
    try:
        payload = response.json()
    except ValueError:
        payload = response.text[:500]
    return response.status_code, payload


def probe_bars_for(symbol: str, timeframe: str, feed: str | None,
                   start: str = "2016-01-01T00:00:00Z",
                   end: str = "2026-06-30T23:59:59Z") -> dict[str, Any]:
    params: dict[str, Any] = {
        "symbols": symbol,
        "timeframe": timeframe,
        "start": start,
        "end": end,
        "adjustment": "all",
        "limit": 10000,
    }
    if feed:
        params["feed"] = feed
    code, payload = get_json(ALPACA_BARS_URL, params=params, headers=alpaca_headers())
    row = {
        "symbol": symbol,
        "timeframe": timeframe,
        "feed": feed or "(default)",
        "http_status": code,
        "bar_count": 0,
        "earliest": "",
        "latest_sample": "",
        "error": "",
    }
    if code >= 400:
        row["error"] = str(payload)[:180]
        return row
    bars = (payload.get("bars") or {}).get(symbol) or []
    row["bar_count"] = len(bars)
    if bars:
        row["earliest"] = bars[0].get("t", "")
        row["latest_sample"] = bars[-1].get("t", "")
    return row


def check_alpaca_bars() -> CheckResult:
    rows: list[dict[str, Any]] = []
    for feed in FEEDS:
        for symbol in [LIQUID_SYMBOL, *SMALLCAP_SYMBOLS]:
            for timeframe in ["1Day", "1Min"]:
                rows.append(probe_bars_for(symbol, timeframe, feed))
    symbols = [LIQUID_SYMBOL, *SMALLCAP_SYMBOLS]
    ok_by_symbol = {
        symbol: any(r["symbol"] == symbol and r["bar_count"] > 0 for r in rows)
        for symbol in symbols
    }
    workable_feeds = sorted({r["feed"] for r in rows if r["bar_count"] > 0})
    missing = [s for s, ok in ok_by_symbol.items() if not ok]
    if missing:
        return CheckResult(
            "alpaca_bars_feed_matrix",
            "FAIL",
            f"No historical bars returned for: {', '.join(missing)}.",
            rows,
        )
    return CheckResult(
        "alpaca_bars_feed_matrix",
        "PASS",
        f"Historical bars returned for liquid and small-cap probes; workable feeds: {', '.join(workable_feeds)}.",
        rows,
    )


def check_alpaca_news() -> CheckResult:
    params = {
        "symbols": ",".join(NEWS_SYMBOLS),
        "start": "2018-01-01T00:00:00Z",
        "end": "2026-06-30T23:59:59Z",
        "limit": 50,
        "sort": "asc",
    }
    code, payload = get_json(ALPACA_NEWS_URL, params=params, headers=alpaca_headers())
    rows: list[dict[str, Any]] = []
    if code >= 400:
        return CheckResult("alpaca_news_depth", "FAIL", f"HTTP {code}: {str(payload)[:220]}", rows)
    articles = payload.get("news") or []
    per_symbol_day: dict[tuple[str, str], int] = {}
    earliest = ""
    for article in articles:
        created = article.get("created_at") or article.get("updated_at") or ""
        if created and (not earliest or created < earliest):
            earliest = created
        day = created[:10] if created else "unknown"
        for symbol in article.get("symbols") or []:
            if symbol in NEWS_SYMBOLS:
                per_symbol_day[(symbol, day)] = per_symbol_day.get((symbol, day), 0) + 1
    for (symbol, day), count in sorted(per_symbol_day.items())[:30]:
        rows.append({"symbol": symbol, "day": day, "article_count": count})
    if not articles:
        return CheckResult("alpaca_news_depth", "FAIL", "No news articles returned for probe symbols.", rows)
    if earliest[:10] > "2025-01-02":
        return CheckResult(
            "alpaca_news_depth",
            "FAIL",
            f"Earliest returned article {earliest} is after OOS start; news history is too shallow.",
            rows,
        )
    return CheckResult(
        "alpaca_news_depth",
        "PASS",
        f"Returned {len(articles)} articles; earliest sample article: {earliest}.",
        rows,
    )


def safe_extract_tar(archive: Path, target: Path) -> None:
    target_resolved = target.resolve()
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf.getmembers():
            resolved = (target / member.name).resolve()
            if not str(resolved).startswith(str(target_resolved)):
                raise RuntimeError(f"Unsafe path in Robintrack archive: {member.name}")
        tf.extractall(target, filter="data")


def download_robintrack() -> None:
    ROBINTRACK_ROOT.mkdir(parents=True, exist_ok=True)
    if not ROBINTRACK_ARCHIVE.exists():
        with requests.get(ROBINTRACK_ARCHIVE_URL, stream=True, timeout=60) as response:
            response.raise_for_status()
            with ROBINTRACK_ARCHIVE.open("wb") as fh:
                for chunk in response.iter_content(chunk_size=1 << 20):
                    if chunk:
                        fh.write(chunk)
    safe_extract_tar(ROBINTRACK_ARCHIVE, ROBINTRACK_ROOT)


def find_robintrack_csv(symbol: str) -> Path | None:
    if not ROBINTRACK_ROOT.exists():
        return None
    candidates = list(ROBINTRACK_ROOT.rglob(f"{symbol}.csv"))
    candidates += list(ROBINTRACK_ROOT.rglob(f"{symbol.lower()}.csv"))
    return candidates[0] if candidates else None


def check_robintrack(try_download: bool = True) -> CheckResult:
    rows: list[dict[str, Any]] = []
    if try_download and not all(find_robintrack_csv(s) for s in ROBINTRACK_SAMPLE_SYMBOLS):
        try:
            download_robintrack()
        except Exception as exc:
            return CheckResult(
                "robintrack_archive",
                "SOFT_BLOCKER",
                "Could not automatically download/extract Robintrack. "
                "Download Kaggle dataset 'Robinhood Stock Popularity History' and extract to "
                "data/raw/robintrack/popularity_export/ so files are <TICKER>.csv with columns "
                f"timestamp,users_holding. Error: {exc}",
                rows,
            )
    for symbol in ROBINTRACK_SAMPLE_SYMBOLS:
        path = find_robintrack_csv(symbol)
        if not path:
            return CheckResult(
                "robintrack_archive",
                "SOFT_BLOCKER",
                "Robintrack files not found. Download Kaggle dataset 'Robinhood Stock Popularity History' "
                "and extract to data/raw/robintrack/popularity_export/ so files are <TICKER>.csv with "
                "columns timestamp,users_holding.",
                rows,
            )
        try:
            df = pd.read_csv(path, usecols=["timestamp", "users_holding"])
            rows.append({
                "symbol": symbol,
                "path": str(path.relative_to(ROOT)),
                "rows": int(len(df)),
                "first_timestamp": str(df["timestamp"].iloc[0]) if len(df) else "",
                "last_timestamp": str(df["timestamp"].iloc[-1]) if len(df) else "",
            })
        except Exception as exc:
            return CheckResult("robintrack_archive", "SOFT_BLOCKER", f"{path.name} could not be read: {exc}", rows)
    return CheckResult("robintrack_archive", "PASS", "Robintrack sample CSVs loaded.", rows)


def check_edgar() -> CheckResult:
    ua = os.getenv("SEC_API_USER_AGENT") or "agorasim@example.com AgoraSim research"
    code, payload = get_json(EDGAR_COMPANYFACTS_AAPL, headers={"User-Agent": ua})
    rows = [{"endpoint": "SEC companyfacts AAPL", "http_status": code}]
    if code >= 400 or not isinstance(payload, dict) or "facts" not in payload:
        return CheckResult("edgar_ping", "FAIL", f"EDGAR companyfacts failed with HTTP {code}.", rows)
    return CheckResult("edgar_ping", "PASS", "SEC EDGAR companyfacts returned facts for AAPL.", rows)


def check_fred() -> CheckResult:
    key = os.getenv("FRED_API_KEY")
    if not key:
        return CheckResult("fred_ping", "SKIP", "FRED_API_KEY absent; FRED is optional.", [])
    params = {"series_id": "DFF", "api_key": key, "file_type": "json", "limit": 1}
    code, payload = get_json(FRED_URL, params=params)
    rows = [{"endpoint": "FRED DFF observations", "http_status": code}]
    if code >= 400 or not isinstance(payload, dict) or "observations" not in payload:
        return CheckResult("fred_ping", "FAIL", f"FRED observations failed with HTTP {code}.", rows)
    return CheckResult("fred_ping", "PASS", "FRED observations endpoint returned data.", rows)


def markdown_table(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    keys = list(dict.fromkeys(k for row in rows for k in row.keys()))
    lines = ["| " + " | ".join(keys) + " |", "| " + " | ".join(["---"] * len(keys)) + " |"]
    for row in rows:
        vals = [str(row.get(k, "")).replace("\n", " ") for k in keys]
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def write_report(results: list[CheckResult], env_names: dict[str, bool]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    hard_failures = [r for r in results if r.hard_failed]
    soft = [r for r in results if r.status == "SOFT_BLOCKER"]
    overall = "FAIL" if hard_failures else "PASS_WITH_SOFT_BLOCKER" if soft else "PASS"
    lines = [
        "# G0 Data Gate Report",
        "",
        f"- Generated UTC: {utc_now()}",
        f"- Overall: **{overall}**",
        "- Secrets hygiene: report records only environment variable names, never values.",
        "",
        "## Environment Names",
        "",
        "| Name | Present |",
        "|---|---|",
    ]
    for name, present in sorted(env_names.items()):
        lines.append(f"| {name} | {present} |")
    lines += ["", "## Check Summary", "", "| Check | Status | Detail |", "|---|---|---|"]
    for result in results:
        lines.append(f"| {result.name} | {result.status} | {result.detail} |")
    for result in results:
        if result.rows:
            lines += ["", f"## {result.name} Details", ""]
            lines += markdown_table(result.rows)
    REPORT_PATH.write_text("\n".join(lines) + "\n")


def env_presence(names: list[str]) -> dict[str, bool]:
    return {name: bool(os.getenv(name)) for name in names}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-robintrack-download", action="store_true",
                        help="Validate only already-present Robintrack files.")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    names = [
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "SEC_API_USER_AGENT",
        "FRED_API_KEY",
        "GCP_PROJECT",
        "GCS_BUCKET",
        "GOOGLE_CLOUD_PROJECT",
        "HF_TOKEN",
    ]
    results: list[CheckResult] = []
    for fn in [
        check_alpaca_bars,
        check_alpaca_news,
        lambda: check_robintrack(try_download=not args.no_robintrack_download),
        check_edgar,
        check_fred,
    ]:
        try:
            results.append(fn())
        except Exception as exc:
            results.append(CheckResult(getattr(fn, "__name__", "check"), "FAIL", str(exc)))
    write_report(results, env_presence(names))
    for result in results:
        print(f"{result.status:13} {result.name}: {result.detail}")
    return 1 if any(r.hard_failed for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
