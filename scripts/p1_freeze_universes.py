"""Freeze G1 universes and point-in-time snapshots.

This script is intentionally deterministic and auditable. It downloads public/API
data into ignored data/snapshots, writes tracked docs with universe membership and
hashes, and performs a small no-lookahead spot check. It does not run LLMs.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests

ALPACA_BARS_URL = "https://data.alpaca.markets/v2/stocks/bars"
ALPACA_NEWS_URL = "https://data.alpaca.markets/v1beta1/news"
ALPACA_ASSETS_URL = "https://paper-api.alpaca.markets/v2/assets"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

CALIB_SELECTION_DATE = "2019-06-28"
CALIB_WINDOW = ("2019-07-01", "2019-12-31")
OOS_SELECTION_DATE = "2024-12-20"
OOS_WINDOW = ("2025-01-02", "2026-06-30")
SNAPSHOT_VERSION = "g1"

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw"
ROBINTRACK_EXPORT = RAW_ROOT / "robintrack" / "tmp" / "popularity_export"
SEC_CACHE = RAW_ROOT / "sec" / "companyfacts"
ALPACA_CACHE = RAW_ROOT / "alpaca"
SNAPSHOT_ROOT = ROOT / "data" / "snapshots" / SNAPSHOT_VERSION
DOC_UNIVERSES = ROOT / "docs" / "G1_UNIVERSES.md"
DOC_MANIFEST = ROOT / "docs" / "G1_SNAPSHOT_MANIFEST.json"
DOC_SPOTCHECK = ROOT / "docs" / "G1_LEAKAGE_SPOTCHECK.md"

EXCLUDED_NAME_MARKERS = (
    " ETF",
    " ETN",
    " WARRANT",
    " RIGHT",
    " UNIT",
    " PREFERRED",
    " PFD",
    " ADR",
    " ADS",
    " NOTES",
    " FUND",
    " TRUST",
    " SPAC",
)


@dataclass(frozen=True)
class UniverseRow:
    ticker: str
    price: float
    shares_outstanding: float
    market_cap: float
    rank_metric: float
    notes: str


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_dotenv(path: Path) -> dict[str, str]:
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
        raise RuntimeError("Set APCA_API_KEY_ID / APCA_API_SECRET_KEY (see .env.example).")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}


def request_json(url: str, *, params: dict[str, Any] | None = None,
                 headers: dict[str, str] | None = None, timeout: int = 60) -> Any:
    backoff = 1.0
    for attempt in range(5):
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        if response.status_code in (429, 500, 502, 503, 504) and attempt < 4:
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError(f"Unreachable request retry path for {url}")


def sec_headers() -> dict[str, str]:
    return {"User-Agent": os.getenv("SEC_API_USER_AGENT") or "agorasim@example.com AgoraSim research"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for row in rows for k in row.keys()))
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value[:10])


def next_day(date_text: str) -> str:
    return (dt.date.fromisoformat(date_text) + dt.timedelta(days=1)).isoformat()


def robintrack_selection_holders(selection_date: str) -> dict[str, int]:
    """Return last holder count observed on selection_date for every ticker."""
    if not ROBINTRACK_EXPORT.exists():
        raise FileNotFoundError(f"Robintrack export not found: {ROBINTRACK_EXPORT}")
    rg = shutil.which("rg")
    rows: dict[str, tuple[str, int]] = {}
    if rg:
        proc = subprocess.run(
            [rg, "-F", selection_date, "."],
            cwd=ROBINTRACK_EXPORT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode not in (0, 1):
            raise RuntimeError(proc.stderr.strip() or "rg failed reading Robintrack archive")
        for line in proc.stdout.splitlines():
            path_text, _, rest = line.partition(":")
            if not rest:
                continue
            symbol = Path(path_text).stem.upper()
            timestamp, _, value = rest.rpartition(",")
            timestamp = timestamp.strip().strip('"')
            if not timestamp.startswith(selection_date):
                continue
            try:
                holders = int(value)
            except ValueError:
                continue
            if symbol not in rows or timestamp > rows[symbol][0]:
                rows[symbol] = (timestamp, holders)
        return {symbol: holders for symbol, (_, holders) in rows.items()}

    for path in ROBINTRACK_EXPORT.glob("*.csv"):
        last_ts = ""
        last_holders: int | None = None
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                ts = str(row.get("timestamp", ""))
                if ts.startswith(selection_date):
                    last_ts = ts
                    last_holders = int(row["users_holding"])
                elif last_ts and ts[:10] > selection_date:
                    break
        if last_holders is not None:
            rows[path.stem.upper()] = (last_ts, last_holders)
    return {symbol: holders for symbol, (_, holders) in rows.items()}


def fetch_bars(symbols: list[str], start: str, end: str, *,
               timeframe: str = "1Day", feed: str = "sip", batch_size: int = 200,
               adjustment: str = "raw") -> dict[str, list[dict[str, Any]]]:
    all_bars: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        params: dict[str, Any] = {
            "symbols": ",".join(batch),
            "start": f"{start}T00:00:00Z",
            "end": f"{end}T23:59:59Z",
            "timeframe": timeframe,
            "adjustment": adjustment,
            "limit": 10000,
            "feed": feed,
        }
        token = None
        while True:
            if token:
                params["page_token"] = token
            payload = request_json(ALPACA_BARS_URL, params=params, headers=alpaca_headers())
            for symbol, rows in (payload.get("bars") or {}).items():
                all_bars.setdefault(symbol, []).extend(rows)
            token = payload.get("next_page_token")
            if not token:
                break
    return all_bars


def close_on_or_before(bars: list[dict[str, Any]], asof: str) -> tuple[float | None, dict[str, Any] | None]:
    cutoff = parse_date(asof)
    candidates = [bar for bar in bars if parse_date(str(bar.get("t", ""))) <= cutoff]
    if not candidates:
        return None, None
    bar = sorted(candidates, key=lambda row: row["t"])[-1]
    return float(bar["c"]), bar


def fetch_assets() -> list[dict[str, Any]]:
    ALPACA_CACHE.mkdir(parents=True, exist_ok=True)
    cache = ALPACA_CACHE / "assets_active_us_equity.json"
    if cache.exists():
        return json.loads(cache.read_text())
    payload = request_json(
        ALPACA_ASSETS_URL,
        params={"status": "active", "asset_class": "us_equity"},
        headers=alpaca_headers(),
    )
    write_json(cache, payload)
    return payload


def is_common_active_asset(asset: dict[str, Any]) -> bool:
    asset_class = asset.get("asset_class") or asset.get("class")
    if asset.get("status") != "active" or asset_class != "us_equity":
        return False
    if asset.get("exchange") not in {"NYSE", "NASDAQ", "AMEX"}:
        return False
    name = str(asset.get("name", "")).upper()
    if any(marker in name for marker in EXCLUDED_NAME_MARKERS):
        return False
    symbol = str(asset.get("symbol", ""))
    if not symbol or any(ch in symbol for ch in ("/", " ")):
        return False
    return True


def sec_ticker_map() -> dict[str, int]:
    cache = SEC_CACHE / "company_tickers.json"
    if cache.exists():
        payload = json.loads(cache.read_text())
    else:
        payload = request_json(SEC_TICKERS_URL, headers=sec_headers())
        write_json(cache, payload)
    mapping: dict[str, int] = {}
    for row in payload.values():
        ticker = str(row.get("ticker", "")).upper()
        cik = int(row.get("cik_str", 0))
        if ticker and cik:
            mapping[ticker] = cik
    return mapping


def companyfacts(cik: int) -> dict[str, Any] | None:
    SEC_CACHE.mkdir(parents=True, exist_ok=True)
    path = SEC_CACHE / f"CIK{cik:010d}.json"
    if path.exists():
        return json.loads(path.read_text())
    try:
        payload = request_json(SEC_FACTS_URL.format(cik=cik), headers=sec_headers())
    except requests.HTTPError:
        return None
    write_json(path, payload)
    time.sleep(0.11)
    return payload


def shares_outstanding_asof(facts: dict[str, Any] | None, asof: str) -> float | None:
    if not facts:
        return None
    units = (((facts.get("facts") or {}).get("dei") or {}).get("EntityCommonStockSharesOutstanding") or {}).get("units") or {}
    rows = units.get("shares") or []
    cutoff = parse_date(asof)
    usable = []
    for row in rows:
        try:
            end = parse_date(str(row.get("end", "")))
            value = float(row["val"])
        except (ValueError, KeyError, TypeError):
            continue
        if value > 0 and end <= cutoff:
            filed = str(row.get("filed", ""))
            usable.append((end, filed, value))
    if not usable:
        return None
    usable.sort(key=lambda item: (item[0], item[1]))
    return usable[-1][2]


def zscore(values: dict[str, float]) -> dict[str, float]:
    finite = [v for v in values.values() if math.isfinite(v)]
    if not finite:
        return {k: 0.0 for k in values}
    mean = sum(finite) / len(finite)
    var = sum((v - mean) ** 2 for v in finite) / max(1, len(finite) - 1)
    std = math.sqrt(var) or 1.0
    return {k: (v - mean) / std for k, v in values.items()}


def build_calib_universe(limit: int) -> list[UniverseRow]:
    holder_counts = robintrack_selection_holders(CALIB_SELECTION_DATE)
    candidates = [symbol for symbol, _ in sorted(holder_counts.items(), key=lambda item: item[1], reverse=True)[:limit]]
    bars = fetch_bars(candidates, CALIB_SELECTION_DATE, CALIB_SELECTION_DATE)
    cik_by_ticker = sec_ticker_map()
    valid: list[UniverseRow] = []
    for symbol in candidates:
        price, _ = close_on_or_before(bars.get(symbol, []), CALIB_SELECTION_DATE)
        if price is None or price < 1:
            continue
        cik = cik_by_ticker.get(symbol)
        shares = shares_outstanding_asof(companyfacts(cik), CALIB_SELECTION_DATE) if cik else None
        if not shares:
            continue
        cap = shares * price
        if 50_000_000 <= cap <= 2_000_000_000:
            holders = holder_counts[symbol]
            valid.append(UniverseRow(symbol, price, shares, cap, holders / shares, f"holders={holders}"))
    valid.sort(key=lambda row: row.rank_metric, reverse=True)
    return valid[:10]


def dollar_volume_spike(bars: list[dict[str, Any]], selection_date: str) -> float | None:
    selected = [bar for bar in bars if parse_date(str(bar.get("t", ""))) <= parse_date(selection_date)]
    if len(selected) < 20:
        return None
    selected.sort(key=lambda row: row["t"])
    last = selected[-1]
    trailing = selected[:-1][-60:]
    dvs = [float(row["c"]) * float(row.get("v", 0.0)) for row in trailing if float(row.get("v", 0.0)) > 0]
    if not dvs:
        return None
    median = pd.Series(dvs).median()
    if median <= 0:
        return None
    return float(last["c"]) * float(last.get("v", 0.0)) / float(median)


def fetch_news_for_symbol(symbol: str, start: str, end: str) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "symbols": symbol,
        "start": f"{start}T00:00:00Z",
        "end": f"{end}T23:59:59Z",
        "limit": 50,
        "sort": "asc",
    }
    out: list[dict[str, Any]] = []
    token = None
    while True:
        if token:
            params["page_token"] = token
        payload = request_json(ALPACA_NEWS_URL, params=params, headers=alpaca_headers())
        out.extend(payload.get("news") or [])
        token = payload.get("next_page_token")
        if not token:
            break
    return out


def news_count(symbol: str, start: str, end: str) -> int:
    return len(fetch_news_for_symbol(symbol, start, end))


def build_oos_universe(prelim_limit: int) -> list[UniverseRow]:
    assets = [asset for asset in fetch_assets() if is_common_active_asset(asset)]
    symbols = sorted({asset["symbol"] for asset in assets})
    trail_start = (dt.date.fromisoformat(OOS_SELECTION_DATE) - dt.timedelta(days=90)).isoformat()
    bars = fetch_bars(symbols, trail_start, OOS_SELECTION_DATE)
    spike: dict[str, float] = {}
    inverse_price: dict[str, float] = {}
    close_price: dict[str, float] = {}
    for symbol in symbols:
        price, _ = close_on_or_before(bars.get(symbol, []), OOS_SELECTION_DATE)
        if price is None or price < 1:
            continue
        s = dollar_volume_spike(bars.get(symbol, []), OOS_SELECTION_DATE)
        if s is None:
            continue
        close_price[symbol] = price
        spike[symbol] = s
        inverse_price[symbol] = 1.0 / price
    preliminary_z = zscore(spike)
    price_z = zscore(inverse_price)
    preliminary = sorted(spike, key=lambda s: preliminary_z[s] + 0.5 * price_z[s], reverse=True)[:prelim_limit]

    cik_by_ticker = sec_ticker_map()
    valid_symbols: list[str] = []
    shares_by_symbol: dict[str, float] = {}
    cap_by_symbol: dict[str, float] = {}
    for symbol in preliminary:
        cik = cik_by_ticker.get(symbol)
        shares = shares_outstanding_asof(companyfacts(cik), OOS_SELECTION_DATE) if cik else None
        if not shares:
            continue
        cap = shares * close_price[symbol]
        if 50_000_000 <= cap <= 2_000_000_000:
            valid_symbols.append(symbol)
            shares_by_symbol[symbol] = shares
            cap_by_symbol[symbol] = cap
        if len(valid_symbols) >= 80:
            break

    news_start = (dt.date.fromisoformat(OOS_SELECTION_DATE) - dt.timedelta(days=60)).isoformat()
    news_counts = {symbol: news_count(symbol, news_start, OOS_SELECTION_DATE) for symbol in valid_symbols}
    news_z = zscore({s: float(news_counts[s]) for s in valid_symbols})
    spike_z = zscore({s: spike[s] for s in valid_symbols})
    lot_z = zscore({s: inverse_price[s] for s in valid_symbols})

    rows: list[UniverseRow] = []
    for symbol in valid_symbols:
        score = news_z[symbol] + spike_z[symbol] + 0.5 * lot_z[symbol]
        rows.append(UniverseRow(
            symbol,
            close_price[symbol],
            shares_by_symbol[symbol],
            cap_by_symbol[symbol],
            score,
            f"news60={news_counts[symbol]}; dv_spike={spike[symbol]:.3f}; lot_proxy={inverse_price[symbol]:.4f}",
        ))
    rows.sort(key=lambda row: row.rank_metric, reverse=True)
    return rows[:10]


def snapshot_symbol(kind: str, symbol: str, start: str, end: str, include_robintrack: bool) -> list[Path]:
    out_dir = SNAPSHOT_ROOT / kind / symbol
    bars = fetch_bars([symbol], start, end)[symbol]
    news = fetch_news_for_symbol(symbol, start, end)
    paths: list[Path] = []
    bars_path = out_dir / "bars_1d.jsonl"
    news_path = out_dir / "news.jsonl"
    write_jsonl(bars_path, bars)
    write_jsonl(news_path, news)
    paths.extend([bars_path, news_path])
    if include_robintrack:
        source = ROBINTRACK_EXPORT / f"{symbol}.csv"
        if source.exists():
            df = pd.read_csv(source, parse_dates=["timestamp"])
            mask = (df["timestamp"].dt.date >= dt.date.fromisoformat(start)) & (df["timestamp"].dt.date <= dt.date.fromisoformat(end))
            rt_path = out_dir / "robintrack.csv"
            df.loc[mask].to_csv(rt_path, index=False)
            paths.append(rt_path)
    return paths


def build_manifest(paths: list[Path], gcs_root: str | None) -> dict[str, Any]:
    entries = []
    for path in sorted(paths):
        rel = path.relative_to(ROOT).as_posix()
        gcs_uri = f"{gcs_root.rstrip('/')}/{path.relative_to(SNAPSHOT_ROOT).as_posix()}" if gcs_root else None
        entries.append({
            "path": rel,
            "gcs_uri": gcs_uri,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return {
        "generated_utc": utc_now(),
        "snapshot_version": SNAPSHOT_VERSION,
        "selection": {
            "calib_selection_date": CALIB_SELECTION_DATE,
            "calib_window": {"start": CALIB_WINDOW[0], "end": CALIB_WINDOW[1]},
            "oos_selection_date": OOS_SELECTION_DATE,
            "oos_window": {"start": OOS_WINDOW[0], "end": OOS_WINDOW[1]},
        },
        "files": entries,
    }


def markdown_table(rows: list[UniverseRow]) -> list[str]:
    out = ["| Rank | Ticker | Price | Market cap | Metric | Notes |", "|---:|---|---:|---:|---:|---|"]
    for idx, row in enumerate(rows, 1):
        out.append(f"| {idx} | {row.ticker} | {row.price:.2f} | {row.market_cap:.0f} | {row.rank_metric:.8f} | {row.notes} |")
    return out


def write_universe_doc(calib: list[UniverseRow], oos: list[UniverseRow]) -> None:
    lines = [
        "# G1 Frozen Universes",
        "",
        f"- Generated UTC: {utc_now()}",
        "- Status: **G1 universe freeze complete; snapshot hash manifest generated**",
        f"- CALIB selection date: {CALIB_SELECTION_DATE}",
        f"- CALIB window: {CALIB_WINDOW[0]} through {CALIB_WINDOW[1]}",
        f"- OOS selection date: {OOS_SELECTION_DATE}",
        f"- OOS window: {OOS_WINDOW[0]} through {OOS_WINDOW[1]}",
        "- OOS start is after the latest enabled model release/cutoff proxy from G0.",
        "",
        "## CALIB-2019",
        "",
        "Rule implementation: rank valid small-cap common-share candidates by Robintrack holders / SEC shares outstanding as of the selection date.",
        "",
        *markdown_table(calib),
        "",
        "## OOS-2025",
        "",
        "Retail-attention score frozen before inference: z(news_count_60d) + z(dollar_volume_spike) + 0.5*z(1/price), after Alpaca active-equity, price, SEC shares, and market-cap filters.",
        "",
        *markdown_table(oos),
        "",
        "## Raw Data Policy",
        "",
        "Raw snapshots live under ignored `data/snapshots/g1/`; only hashes and metadata are committed.",
    ]
    DOC_UNIVERSES.write_text("\n".join(lines) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def bar_line(row: dict[str, Any]) -> str:
    return f"{row['t'][:10]}, {float(row['o']):.2f}, {float(row['h']):.2f}, {float(row['l']):.2f}, {float(row['c']):.2f}, {int(row.get('v', 0))}"


def leakage_spotcheck(calib_symbols: list[str], oos_symbols: list[str]) -> None:
    from agorasim.agents import PersonaBank
    from agorasim.agents.prompt_builder import load_template, render

    checks = []
    dates: list[tuple[str, str, str]] = [
        ("calib", "2019-07-15"),
        ("calib", "2019-09-03"),
        ("calib", "2019-12-16"),
        ("oos", "2025-01-15"),
        ("oos", "2025-03-17"),
        ("oos", "2025-06-16"),
        ("oos", "2025-09-15"),
        ("oos", "2026-01-15"),
        ("oos", "2026-03-16"),
        ("oos", "2026-06-15"),
    ]
    expanded_dates = []
    for idx, (kind, asof) in enumerate(dates):
        symbol_pool = calib_symbols if kind == "calib" else oos_symbols
        expanded_dates.append((kind, symbol_pool[idx % len(symbol_pool)], asof))

    sys_t = load_template("agent_system.j2")
    user_t = load_template("decision_user.j2")
    personas = PersonaBank(len(expanded_dates), seed=20260703).personas
    for idx, (kind, symbol, asof) in enumerate(expanded_dates):
        base = SNAPSHOT_ROOT / kind / symbol
        bars_path = base / "bars_1d.jsonl"
        news_path = base / "news.jsonl"
        bars_all = read_jsonl(bars_path)
        news_all = read_jsonl(news_path)
        bars = [row for row in bars_all if parse_date(str(row.get("t", ""))) <= parse_date(asof)]
        news = [
            row for row in news_all
            if (row.get("created_at") or row.get("updated_at"))
            and parse_date(str(row.get("created_at") or row.get("updated_at"))) <= parse_date(asof)
        ]
        bars = sorted(bars, key=lambda row: row["t"])[-30:]
        news = sorted(news, key=lambda row: row.get("created_at") or row.get("updated_at"))[-5:]
        persona = personas[idx]
        prompt = render(sys_t, persona=persona.render()) + "\n\n" + render(
            user_t,
            asof_date=asof,
            name_or_alias=f"{symbol} Holdings",
            bars_block="\n".join(bar_line(row) for row in bars),
            news_block="\n".join(
                f"{row.get('created_at') or row.get('updated_at')}: {str(row.get('headline') or row.get('summary') or '')[:180]}"
                for row in news
            ),
            shares=str(persona.shares),
            avg_cost=f"{bars[-1]['c']:.2f}" if bars else "1.00",
            cash=f"{persona.cash:.2f}",
        )
        max_bar = max((str(row.get("t", "")) for row in bars), default="")
        max_news = max((str(row.get("created_at") or row.get("updated_at") or "") for row in news), default="")
        bad_bars = sum(1 for row in bars if parse_date(str(row.get("t", ""))) > parse_date(asof))
        bad_news = sum(
            1 for row in news
            if parse_date(str(row.get("created_at") or row.get("updated_at") or "")) > parse_date(asof)
        )
        checks.append({
            "kind": kind,
            "symbol": symbol,
            "asof": asof,
            "included_bars": len(bars),
            "included_news": len(news),
            "max_included_bar": max_bar,
            "max_included_news": max_news,
            "post_asof_included_rows": bad_bars + bad_news,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        })
    failing = [row for row in checks if row["post_asof_included_rows"]]
    lines = [
        "# G1 Leakage Spot Check",
        "",
        f"- Generated UTC: {utc_now()}",
        "- Method: 10 deterministic ticker/date checks rendered from frozen snapshots using the production prompt templates.",
        "- PASS condition: no rendered prompt includes bars or news after its as-of date.",
        "",
        "| Kind | Symbol | As-of | Bars | News | Max included bar | Max included news | Post-asof included | Prompt SHA-256 |",
        "|---|---|---|---:|---:|---|---|---:|---|",
    ]
    for row in checks:
        lines.append(
            f"| {row['kind']} | {row['symbol']} | {row['asof']} | {row['included_bars']} | {row['included_news']} | "
            f"{row['max_included_bar']} | {row['max_included_news']} | {row['post_asof_included_rows']} | "
            f"{row['prompt_sha256']} |"
        )
    lines += [
        "",
        f"Result: **{'FAIL' if failing else 'PASS'}**.",
    ]
    DOC_SPOTCHECK.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calib-candidate-limit", type=int, default=1000)
    parser.add_argument("--oos-prelim-limit", type=int, default=500)
    parser.add_argument("--gcs-root", default="gs://project-82d97cf9-5889-43a4-850-agorasim/agorasim/snapshots/g1")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    calib = build_calib_universe(args.calib_candidate_limit)
    oos = build_oos_universe(args.oos_prelim_limit)
    if len(calib) != 10:
        raise RuntimeError(f"Expected 10 CALIB tickers, got {len(calib)}")
    if len(oos) != 10:
        raise RuntimeError(f"Expected 10 OOS tickers, got {len(oos)}")

    if SNAPSHOT_ROOT.exists():
        shutil.rmtree(SNAPSHOT_ROOT)
    paths: list[Path] = []
    for row in calib:
        paths.extend(snapshot_symbol("calib", row.ticker, CALIB_WINDOW[0], CALIB_WINDOW[1], include_robintrack=True))
    for row in oos:
        paths.extend(snapshot_symbol("oos", row.ticker, OOS_WINDOW[0], OOS_WINDOW[1], include_robintrack=False))

    write_universe_doc(calib, oos)
    write_json(DOC_MANIFEST, build_manifest(paths, args.gcs_root))
    leakage_spotcheck([row.ticker for row in calib], [row.ticker for row in oos])
    print(f"Wrote {DOC_UNIVERSES.relative_to(ROOT)}")
    print(f"Wrote {DOC_MANIFEST.relative_to(ROOT)} with {len(paths)} files")
    print(f"Wrote {DOC_SPOTCHECK.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
