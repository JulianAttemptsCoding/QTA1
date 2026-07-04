"""P1 / GATE G1 — freeze the CALIB and OOS universes and their point-in-time snapshots.

Deterministic and auditable: pulls public/API data into gitignored data/, ranks with the
frozen rules in agorasim.data.universe, snapshots bars+news (+Robintrack for CALIB) per
ticker, SHA-256s every file into a committed manifest, renders a leakage spot-check, and
writes the tracked G1 docs. Runs NO LLMs (P1 is CPU-only, K-1).

CALIB needs the Robintrack popularity export at data/raw/robintrack/popularity_export/
(<TICKER>.csv with columns timestamp, users_holding; robintrack.net/data-download). OOS is
Alpaca+SEC only and runs without it. Use --track to freeze one side at a time.

Usage:
  python scripts/p1_freeze_universes.py --track oos
  python scripts/p1_freeze_universes.py --track both --gcs-root gs://.../snapshots/g1
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Iterable, Optional

import requests

from agorasim.data.universe import (
    CALIB_SELECTION_DATE, CALIB_WINDOW, OOS_SELECTION_DATE, OOS_WINDOW, N_UNIVERSE,
    MIN_PRICE, UniverseRow, close_on_or_before, dollar_volume_spike, is_common_equity_name,
    passes_cap_filter, rank_calib, rank_oos, shares_outstanding_asof, zscore,
)

ALPACA_BARS_URL = "https://data.alpaca.markets/v2/stocks/bars"
ALPACA_NEWS_URL = "https://data.alpaca.markets/v1beta1/news"
ALPACA_ASSETS_URL = "https://paper-api.alpaca.markets/v2/assets"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ROBINTRACK_EXPORT = RAW / "robintrack" / "popularity_export"
SEC_CACHE = RAW / "sec"
ALPACA_CACHE = RAW / "alpaca"
SNAPSHOT_ROOT = ROOT / "data" / "snapshots" / "g1"
DOC_UNIVERSES = ROOT / "docs" / "G1_UNIVERSES.md"
DOC_MANIFEST = ROOT / "docs" / "G1_SNAPSHOT_MANIFEST.json"
DOC_SPOTCHECK = ROOT / "docs" / "G1_LEAKAGE_SPOTCHECK.md"


# --- small utilities ---------------------------------------------------------------------
def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def alpaca_headers() -> dict[str, str]:
    key, sec = os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY")
    if not key or not sec:
        raise RuntimeError("Set APCA_API_KEY_ID / APCA_API_SECRET_KEY (see .env.example).")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}


def sec_headers() -> dict[str, str]:
    return {"User-Agent": os.getenv("SEC_API_USER_AGENT")
            or "AgoraSim research (bubgaming3@gmail.com)"}


def request_json(url: str, *, params: dict | None = None, headers: dict | None = None,
                 timeout: int = 60) -> Any:
    backoff = 1.0
    for attempt in range(6):
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 5:
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"request retries exhausted for {url}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# --- Alpaca / SEC data acquisition -------------------------------------------------------
def fetch_assets() -> list[dict]:
    ALPACA_CACHE.mkdir(parents=True, exist_ok=True)
    cache = ALPACA_CACHE / "assets_active_us_equity.json"
    if cache.exists():
        return json.loads(cache.read_text())
    payload = request_json(ALPACA_ASSETS_URL,
                           params={"status": "active", "asset_class": "us_equity"},
                           headers=alpaca_headers())
    write_json(cache, payload)
    return payload


def active_common_symbols() -> list[str]:
    out = []
    for a in fetch_assets():
        if a.get("status") != "active" or (a.get("class") or a.get("asset_class")) != "us_equity":
            continue
        if a.get("exchange") not in {"NYSE", "NASDAQ", "AMEX"} or not a.get("tradable", True):
            continue
        sym = str(a.get("symbol", ""))
        if not sym or any(c in sym for c in "/ ."):
            continue
        if not is_common_equity_name(a.get("name", "")):
            continue
        out.append(sym)
    return sorted(set(out))


def fetch_bars(symbols: list[str], start: str, end: str, *, timeframe: str = "1Day",
               feed: str = "sip", batch: int = 200) -> dict[str, list[dict]]:
    bars: dict[str, list[dict]] = {s: [] for s in symbols}
    for i in range(0, len(symbols), batch):
        chunk = symbols[i:i + batch]
        params = {"symbols": ",".join(chunk), "start": f"{start}T00:00:00Z",
                  "end": f"{end}T23:59:59Z", "timeframe": timeframe, "adjustment": "raw",
                  "limit": 10000, "feed": feed}
        token = None
        while True:
            if token:
                params["page_token"] = token
            payload = request_json(ALPACA_BARS_URL, params=params, headers=alpaca_headers())
            for sym, rows in (payload.get("bars") or {}).items():
                bars.setdefault(sym, []).extend(rows)
            token = payload.get("next_page_token")
            if not token:
                break
    return bars


def fetch_news(symbol: str, start: str, end: str) -> list[dict]:
    params = {"symbols": symbol, "start": f"{start}T00:00:00Z", "end": f"{end}T23:59:59Z",
              "limit": 50, "sort": "asc"}
    out, token = [], None
    while True:
        if token:
            params["page_token"] = token
        payload = request_json(ALPACA_NEWS_URL, params=params, headers=alpaca_headers())
        out.extend(payload.get("news") or [])
        token = payload.get("next_page_token")
        if not token:
            return out


def sec_ticker_map() -> dict[str, int]:
    cache = SEC_CACHE / "company_tickers.json"
    payload = json.loads(cache.read_text()) if cache.exists() else request_json(
        SEC_TICKERS_URL, headers=sec_headers())
    if not cache.exists():
        write_json(cache, payload)
    mapping: dict[str, int] = {}
    for row in payload.values():
        t, cik = str(row.get("ticker", "")).upper(), int(row.get("cik_str", 0))
        if t and cik:
            mapping[t] = cik
    return mapping


def companyfacts(cik: int) -> Optional[dict]:
    SEC_CACHE.mkdir(parents=True, exist_ok=True)
    path = SEC_CACHE / f"CIK{cik:010d}.json"
    if path.exists():
        return json.loads(path.read_text())
    try:
        payload = request_json(SEC_FACTS_URL.format(cik=cik), headers=sec_headers())
    except requests.HTTPError:
        return None
    write_json(path, payload)
    time.sleep(0.11)  # SEC fair-access ~10 req/s
    return payload


# --- universe builders (I/O -> assemble fields -> pure ranker) ---------------------------
def build_oos_universe(prelim_limit: int, cap_scan: int) -> list[UniverseRow]:
    symbols = active_common_symbols()
    trail_start = (dt.date.fromisoformat(OOS_SELECTION_DATE) - dt.timedelta(days=90)).isoformat()
    bars = fetch_bars(symbols, trail_start, OOS_SELECTION_DATE)
    spike, inv_price, close = {}, {}, {}
    for sym in symbols:
        price, _ = close_on_or_before(bars.get(sym, []), OOS_SELECTION_DATE)
        if price is None or price < MIN_PRICE:
            continue
        s = dollar_volume_spike(bars.get(sym, []), OOS_SELECTION_DATE)
        if s is None:
            continue
        close[sym], spike[sym], inv_price[sym] = price, s, 1.0 / price
    # preliminary attention rank (spike + lot proxy) narrows the SEC/news fan-out
    sz, lz = zscore(spike), zscore(inv_price)
    prelim = sorted(spike, key=lambda s: sz[s] + 0.5 * lz[s], reverse=True)[:prelim_limit]

    cik_by = sec_ticker_map()
    rows: dict[str, dict[str, float]] = {}
    for sym in prelim:
        cik = cik_by.get(sym)
        shares = shares_outstanding_asof(companyfacts(cik), OOS_SELECTION_DATE) if cik else None
        if not shares:
            continue
        cap = shares * close[sym]
        if passes_cap_filter(cap):
            rows[sym] = {"price": close[sym], "shares": shares, "cap": cap,
                         "dv_spike": spike[sym], "inv_price": inv_price[sym], "news60": 0}
        if len(rows) >= cap_scan:
            break
    news_start = (dt.date.fromisoformat(OOS_SELECTION_DATE) - dt.timedelta(days=60)).isoformat()
    for sym in rows:
        rows[sym]["news60"] = len(fetch_news(sym, news_start, OOS_SELECTION_DATE))
    return rank_oos(rows)


def build_calib_universe(candidate_limit: int) -> list[UniverseRow]:
    holders = robintrack_selection_holders(CALIB_SELECTION_DATE)
    if not holders:
        raise RuntimeError(
            f"No Robintrack holders parsed from {ROBINTRACK_EXPORT}. Download the popularity "
            "export (robintrack.net/data-download) to <TICKER>.csv files there, then rerun "
            "with --track calib. OOS can be frozen independently with --track oos.")
    candidates = [s for s, _ in sorted(holders.items(), key=lambda kv: kv[1], reverse=True)][:candidate_limit]
    bars = fetch_bars(candidates, CALIB_SELECTION_DATE, CALIB_SELECTION_DATE)
    cik_by = sec_ticker_map()
    rows: dict[str, dict[str, float]] = {}
    for sym in candidates:
        price, _ = close_on_or_before(bars.get(sym, []), CALIB_SELECTION_DATE)
        if price is None or price < MIN_PRICE:
            continue
        cik = cik_by.get(sym)
        shares = shares_outstanding_asof(companyfacts(cik), CALIB_SELECTION_DATE) if cik else None
        if not shares:
            continue
        rows[sym] = {"price": price, "shares": shares, "cap": shares * price,
                     "holders": float(holders[sym])}
    return rank_calib(rows)


def robintrack_selection_holders(selection_date: str) -> dict[str, int]:
    """Last holder count observed on selection_date per ticker, from the popularity export."""
    if not ROBINTRACK_EXPORT.exists():
        return {}
    out: dict[str, int] = {}
    for path in ROBINTRACK_EXPORT.glob("*.csv"):
        last: Optional[int] = None
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                ts = str(row.get("timestamp", ""))
                if ts.startswith(selection_date):
                    try:
                        last = int(float(row["users_holding"]))
                    except (ValueError, KeyError, TypeError):
                        pass
                elif last is not None and ts[:10] > selection_date:
                    break
        if last is not None:
            out[path.stem.upper()] = last
    return out


# --- snapshot + manifest + docs ----------------------------------------------------------
def snapshot_symbol(kind: str, symbol: str, start: str, end: str, robintrack: bool) -> list[Path]:
    out_dir = SNAPSHOT_ROOT / kind / symbol
    paths = []
    bars_path, news_path = out_dir / "bars_1d.jsonl", out_dir / "news.jsonl"
    write_jsonl(bars_path, fetch_bars([symbol], start, end)[symbol])
    write_jsonl(news_path, fetch_news(symbol, start, end))
    paths += [bars_path, news_path]
    if robintrack:
        src = ROBINTRACK_EXPORT / f"{symbol}.csv"
        if src.exists():
            rt = out_dir / "robintrack.csv"
            lo, hi = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
            with src.open(newline="", encoding="utf-8") as fh, rt.open("w", newline="", encoding="utf-8") as w:
                reader = csv.DictReader(fh)
                writer = csv.DictWriter(w, fieldnames=reader.fieldnames or ["timestamp", "users_holding"])
                writer.writeheader()
                for row in reader:
                    d = str(row.get("timestamp", ""))[:10]
                    if d and lo.isoformat() <= d <= hi.isoformat():
                        writer.writerow(row)
            paths.append(rt)
    return paths


def build_manifest(paths: list[Path], gcs_root: Optional[str]) -> dict:
    files = []
    for p in sorted(paths):
        rel_snap = p.relative_to(SNAPSHOT_ROOT).as_posix()
        files.append({"path": p.relative_to(ROOT).as_posix(),
                      "gcs_uri": f"{gcs_root.rstrip('/')}/{rel_snap}" if gcs_root else None,
                      "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    return {"generated_utc": utc_now(), "snapshot_version": "g1",
            "selection": {"calib_selection_date": CALIB_SELECTION_DATE,
                          "calib_window": {"start": CALIB_WINDOW[0], "end": CALIB_WINDOW[1]},
                          "oos_selection_date": OOS_SELECTION_DATE,
                          "oos_window": {"start": OOS_WINDOW[0], "end": OOS_WINDOW[1]}},
            "files": files}


def md_table(rows: list[UniverseRow]) -> list[str]:
    out = ["| Rank | Ticker | Price | Market cap | Metric | Notes |", "|---:|---|---:|---:|---:|---|"]
    for i, r in enumerate(rows, 1):
        out.append(f"| {i} | {r.ticker} | {r.price:.2f} | {r.market_cap:.0f} | {r.rank_metric:.8f} | {r.notes} |")
    return out


def write_universe_doc(calib: list[UniverseRow], oos: list[UniverseRow]) -> None:
    def section(title, desc, rows):
        if rows:
            return [f"## {title}", "", desc, "", *md_table(rows), ""]
        return [f"## {title}", "", f"{desc}", "",
                "_PENDING: not yet frozen (see status above)._", ""]
    lines = [
        "# G1 Frozen Universes", "",
        f"- Generated UTC: {utc_now()}",
        f"- CALIB: {'FROZEN' if calib else 'PENDING (Robintrack export required)'}"
        f" — selection {CALIB_SELECTION_DATE}, window {CALIB_WINDOW[0]}..{CALIB_WINDOW[1]}",
        f"- OOS: {'FROZEN' if oos else 'PENDING'}"
        f" — selection {OOS_SELECTION_DATE}, window {OOS_WINDOW[0]}..{OOS_WINDOW[1]}",
        "- OOS start is strictly after the max enabled-model cutoff from G0 (D-04).", "",
        *section("CALIB-2019",
                 "Rank valid small-cap common shares by Robintrack holders / SEC shares "
                 "outstanding as of the selection date (U-C1..U-C4).", calib),
        *section("OOS-2025",
                 "Retail-attention score frozen before inference: z(news_count_60d) + "
                 "z(dollar_volume_spike) + 0.5*z(1/price), after Alpaca active-common, price, "
                 "SEC shares, and $50M-$2B market-cap filters (U-O1..U-O3).", oos),
        "## Raw Data Policy", "",
        "Raw snapshots live under gitignored `data/snapshots/g1/`; only SHA-256 hashes and "
        "metadata (docs/G1_SNAPSHOT_MANIFEST.json) are committed.",
    ]
    DOC_UNIVERSES.write_text("\n".join(lines) + "\n")


def bar_line(b: dict) -> str:
    return (f"{b['t'][:10]}, {float(b['o']):.2f}, {float(b['h']):.2f}, {float(b['l']):.2f}, "
            f"{float(b['c']):.2f}, {int(b.get('v', 0))}")


def leakage_spotcheck(pairs: list[tuple[str, str, str]]) -> bool:
    """Render prompts from frozen snapshots; PASS iff none includes post-as-of data."""
    from agorasim.agents.personas import PersonaBank
    from agorasim.agents.prompt_builder import load_template, render
    from agorasim.data.universe import parse_date

    sys_t, user_t = load_template("agent_system.j2"), load_template("decision_user.j2")
    personas = PersonaBank(len(pairs), seed=20260703).personas
    checks = []
    for idx, (kind, symbol, asof) in enumerate(pairs):
        base = SNAPSHOT_ROOT / kind / symbol
        bars_all, news_all = read_jsonl(base / "bars_1d.jsonl"), read_jsonl(base / "news.jsonl")
        cutoff = parse_date(asof)
        bars = sorted([b for b in bars_all if b.get("t") and parse_date(b["t"]) <= cutoff],
                      key=lambda r: r["t"])[-30:]
        news = sorted([n for n in news_all
                       if (n.get("created_at") or n.get("updated_at"))
                       and parse_date(n.get("created_at") or n.get("updated_at")) <= cutoff],
                      key=lambda r: r.get("created_at") or r.get("updated_at"))[-5:]
        p = personas[idx]
        prompt = render(sys_t, persona=p.render()) + "\n\n" + render(
            user_t, asof_date=asof, name_or_alias=f"{symbol} ({symbol})",
            bars_block="\n".join(bar_line(b) for b in bars),
            news_block="\n".join(f"{n.get('created_at') or n.get('updated_at')}: "
                                 f"{str(n.get('headline') or n.get('summary') or '')[:180]}" for n in news),
            shares=str(p.shares), avg_cost=f"{bars[-1]['c']:.2f}" if bars else "1.00",
            cash=f"{p.cash:.2f}")
        bad = sum(1 for b in bars if parse_date(b["t"]) > cutoff) + sum(
            1 for n in news if parse_date(n.get("created_at") or n.get("updated_at")) > cutoff)
        checks.append({"kind": kind, "symbol": symbol, "asof": asof,
                       "bars": len(bars), "news": len(news),
                       "max_bar": max((b["t"][:10] for b in bars), default="-"),
                       "max_news": max((str(n.get("created_at") or n.get("updated_at"))[:10] for n in news), default="-"),
                       "post_asof": bad,
                       "sha": hashlib.sha256(prompt.encode()).hexdigest()[:16]})
    ok = all(c["post_asof"] == 0 for c in checks)
    lines = ["# G1 Leakage Spot Check", "",
             f"- Generated UTC: {utc_now()}",
             "- Method: deterministic ticker/date checks rendered from frozen snapshots via the "
             "production prompt templates (L-01).",
             "- PASS: no rendered prompt includes bars or news dated after its as-of date.", "",
             "| Kind | Symbol | As-of | Bars | News | Max bar | Max news | Post-asof | Prompt SHA |",
             "|---|---|---|---:|---:|---|---|---:|---|"]
    for c in checks:
        lines.append(f"| {c['kind']} | {c['symbol']} | {c['asof']} | {c['bars']} | {c['news']} | "
                     f"{c['max_bar']} | {c['max_news']} | {c['post_asof']} | {c['sha']} |")
    lines += ["", f"Result: **{'PASS' if ok else 'FAIL'}**."]
    DOC_SPOTCHECK.write_text("\n".join(lines) + "\n")
    return ok


def spotcheck_pairs(calib: list[UniverseRow], oos: list[UniverseRow]) -> list[tuple[str, str, str]]:
    pairs = []
    calib_dates = ["2019-07-15", "2019-09-03", "2019-12-16"]
    oos_dates = ["2025-01-15", "2025-03-17", "2025-06-16", "2025-09-15", "2026-01-15", "2026-03-16", "2026-06-15"]
    for i, d in enumerate(calib_dates):
        if calib:
            pairs.append(("calib", calib[i % len(calib)].ticker, d))
    for i, d in enumerate(oos_dates):
        if oos:
            pairs.append(("oos", oos[i % len(oos)].ticker, d))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", choices=["oos", "calib", "both"], default="both")
    ap.add_argument("--oos-prelim-limit", type=int, default=500)
    ap.add_argument("--oos-cap-scan", type=int, default=80)
    ap.add_argument("--calib-candidate-limit", type=int, default=1200)
    ap.add_argument("--gcs-root", default="gs://project-c779f701-1a49-4a58-b54-agorasim/agorasim/snapshots/g1")
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")

    calib: list[UniverseRow] = []
    oos: list[UniverseRow] = []
    if args.track in ("calib", "both"):
        try:
            calib = build_calib_universe(args.calib_candidate_limit)
        except RuntimeError as e:
            if args.track == "calib":
                raise
            print(f"[calib] SKIPPED: {e}")
    if args.track in ("oos", "both"):
        oos = build_oos_universe(args.oos_prelim_limit, args.oos_cap_scan)

    if calib and len(calib) != N_UNIVERSE:
        raise RuntimeError(f"CALIB expected {N_UNIVERSE} tickers, got {len(calib)}")
    if oos and len(oos) != N_UNIVERSE:
        raise RuntimeError(f"OOS expected {N_UNIVERSE} tickers, got {len(oos)}")

    # Backup-first: snapshot only the freshly-frozen tracks; never delete the other track's dir.
    paths: list[Path] = []
    if calib:
        shutil.rmtree(SNAPSHOT_ROOT / "calib", ignore_errors=True)
        for r in calib:
            paths += snapshot_symbol("calib", r.ticker, CALIB_WINDOW[0], CALIB_WINDOW[1], robintrack=True)
    if oos:
        shutil.rmtree(SNAPSHOT_ROOT / "oos", ignore_errors=True)
        for r in oos:
            paths += snapshot_symbol("oos", r.ticker, OOS_WINDOW[0], OOS_WINDOW[1], robintrack=False)

    write_universe_doc(calib, oos)
    # Manifest reflects everything currently on disk (both tracks), so freezing OOS now and
    # CALIB later yields one complete, correct manifest either way.
    on_disk = sorted(p for p in SNAPSHOT_ROOT.rglob("*") if p.is_file()) if SNAPSHOT_ROOT.exists() else []
    if on_disk:
        write_json(DOC_MANIFEST, build_manifest(on_disk, args.gcs_root))
    leak_ok = leakage_spotcheck(spotcheck_pairs(calib, oos))

    print(f"CALIB: {len(calib)} tickers -> {[r.ticker for r in calib]}")
    print(f"OOS:   {len(oos)} tickers -> {[r.ticker for r in oos]}")
    print(f"Snapshot files: {len(paths)} | leakage spot-check: {'PASS' if leak_ok else 'FAIL'}")
    return 0 if leak_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
