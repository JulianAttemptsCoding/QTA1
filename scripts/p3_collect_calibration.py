"""Collect P3 calibration run artifacts into RQ1/RQ2 reports."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agorasim.evals import stylized_fact_report


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_sim_rows(input_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(input_dir.rglob("sim.jsonl")):
        rows.extend(iter_jsonl(path))
    if not rows:
        raise FileNotFoundError(f"No sim.jsonl files found under {input_dir}")
    df = pd.DataFrame(rows)
    df["day"] = pd.to_datetime(df["day"])
    return df.sort_values(["ticker", "arm", "day"]).reset_index(drop=True)


def sign(value: float) -> int:
    if pd.isna(value) or value == 0:
        return 0
    return 1 if value > 0 else -1


def spearman(x: pd.Series, y: pd.Series) -> float:
    mask = x.notna() & y.notna()
    if mask.sum() < 3:
        return float("nan")
    return float(x[mask].rank().corr(y[mask].rank()))


def sign_agreement(x: pd.Series, y: pd.Series) -> float:
    mask = x.notna() & y.notna()
    if mask.sum() == 0:
        return float("nan")
    xs = x[mask].map(sign)
    ys = y[mask].map(sign)
    return float((xs == ys).mean())


def rq1_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for (ticker, arm), group in df.groupby(["ticker", "arm"]):
        group = group.sort_values("day")
        returns = group["auction_price"].pct_change().dropna().to_numpy()
        volume = group["auction_volume"].iloc[1:].to_numpy() if len(group) > 1 else np.array([])
        report = stylized_fact_report(returns, volume=volume if len(volume) == len(returns) else None)
        report.update({
            "ticker": ticker,
            "arm": arm,
            "median_abs_return": float(np.median(np.abs(returns))) if len(returns) else 0.0,
            "total_auction_volume": int(group["auction_volume"].sum()),
            "mean_abs_imbalance": float(group["flow_imbalance"].abs().mean()),
            "median_entropy": float(group["decision_entropy"].median()),
        })
        rows.append(report)
    return rows


def rq2_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for (ticker, arm), group in df.groupby(["ticker", "arm"]):
        rows.append({
            "scope": "ticker",
            "ticker": ticker,
            "arm": arm,
            "n": int(group[["flow_imbalance", "robintrack_d_holders"]].dropna().shape[0]),
            "spearman": spearman(group["flow_imbalance"], group["robintrack_d_holders"]),
            "sign_agreement": sign_agreement(group["flow_imbalance"], group["robintrack_d_holders"]),
            "mean_entropy": float(group["decision_entropy"].mean()),
        })
    for arm, group in df.groupby("arm"):
        rows.append({
            "scope": "pooled",
            "ticker": "ALL",
            "arm": arm,
            "n": int(group[["flow_imbalance", "robintrack_d_holders"]].dropna().shape[0]),
            "spearman": spearman(group["flow_imbalance"], group["robintrack_d_holders"]),
            "sign_agreement": sign_agreement(group["flow_imbalance"], group["robintrack_d_holders"]),
            "mean_entropy": float(group["decision_entropy"].mean()),
        })
    return rows


def fmt_float(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    return f"{float(value):.3f}"


def markdown_cell(value: Any) -> str:
    text = fmt_float(value) if isinstance(value, float) else str(value)
    return text.replace("|", r"\|")


def markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    lines = [
        "| " + " | ".join(markdown_cell(title) for title, _ in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = [markdown_cell(row.get(key)) for _, key in columns]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def render_rq1(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# RQ1 Calibration Realism Report",
        "",
        "- Source: P3 Vertex calibration `sim.jsonl` artifacts.",
        "- Scope: auction-track paths by ticker and anonymization arm.",
        "",
    ]
    lines.extend(markdown_table(rows, [
        ("Ticker", "ticker"),
        ("Arm", "arm"),
        ("N returns", "n"),
        ("Excess kurtosis", "excess_kurtosis"),
        ("ACF r lag1", "acf_r_lag1"),
        ("ACF |r| lag1", "acf_abs_r_lag1"),
        ("Vol-|r| corr", "corr_volume_absr"),
        ("Med |ret|", "median_abs_return"),
        ("Auction volume", "total_auction_volume"),
        ("Med entropy", "median_entropy"),
    ]))
    return "\n".join(lines) + "\n"


def named_alias_gap(rows: list[dict[str, Any]]) -> list[str]:
    pooled = {row["arm"]: row for row in rows if row["scope"] == "pooled"}
    if "named" not in pooled or "alias" not in pooled:
        return ["- Named-vs-alias gap: unavailable until both arms complete."]
    sign_gap = pooled["named"]["sign_agreement"] - pooled["alias"]["sign_agreement"]
    corr_gap = pooled["named"]["spearman"] - pooled["alias"]["spearman"]
    return [
        f"- Named-vs-alias sign-agreement gap: `{fmt_float(sign_gap)}`.",
        f"- Named-vs-alias Spearman gap: `{fmt_float(corr_gap)}`.",
    ]


def g3_gate_summary(rq1: list[dict[str, Any]], rq2: list[dict[str, Any]]) -> str:
    pooled = {row["arm"]: row for row in rq2 if row["scope"] == "pooled"}
    both_sign_low = all((pooled.get(arm, {}).get("sign_agreement", 0.0) <= 0.52) for arm in ("named", "alias"))
    stylized_absent = all(row.get("total_auction_volume", 0) == 0 and row.get("median_abs_return", 0.0) == 0.0 for row in rq1)
    if both_sign_low and stylized_absent:
        return "G3-KILL condition fires: sign agreement <= 52% in both arms and stylized facts qualitatively absent."
    return "G3 kill condition does not fire on the available P3 artifacts."


def render_rq2(rows: list[dict[str, Any]], rq1: list[dict[str, Any]], fig_dir: Path) -> str:
    lines = [
        "# RQ2 Calibration Fidelity Report",
        "",
        "- Source: P3 Vertex calibration `sim.jsonl` artifacts.",
        "- Target: daily simulated flow imbalance vs Robintrack daily holder-count change.",
        "",
    ]
    lines.extend(markdown_table(rows, [
        ("Scope", "scope"),
        ("Ticker", "ticker"),
        ("Arm", "arm"),
        ("N", "n"),
        ("Spearman", "spearman"),
        ("Sign agree", "sign_agreement"),
        ("Mean entropy", "mean_entropy"),
    ]))
    lines += ["", "## Named vs Alias", ""]
    lines.extend(named_alias_gap(rows))
    lines += ["", "## Gate G3", "", f"- {g3_gate_summary(rq1, rows)}", "", "## Figures", ""]
    for path in sorted(fig_dir.glob("*.svg")):
        lines.append(f"- `{path.as_posix()}`")
    return "\n".join(lines) + "\n"


def top_news_days(snapshot_root: Path, ticker: str, limit: int = 5) -> list[str]:
    path = snapshot_root / "calib" / ticker / "news.jsonl"
    if not path.exists():
        return []
    counts = Counter()
    for row in iter_jsonl(path):
        ts = str(row.get("created_at") or row.get("updated_at") or "")
        if ts:
            counts[ts[:10]] += 1
    return [day for day, _ in counts.most_common(limit)]


def scale(values: list[float], height: int, pad: int) -> list[float]:
    clean = [v for v in values if not math.isnan(v)]
    if not clean:
        return [height / 2 for _ in values]
    lo, hi = min(clean), max(clean)
    if lo == hi:
        return [height / 2 for _ in values]
    return [height - pad - (v - lo) / (hi - lo) * (height - 2 * pad) if not math.isnan(v) else height / 2 for v in values]


def svg_polyline(points: list[tuple[float, float]], color: str) -> str:
    return f'<polyline fill="none" stroke="{color}" stroke-width="2" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in points) + '" />'


def write_event_svgs(df: pd.DataFrame, snapshot_root: Path, fig_dir: Path) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    width, height, pad = 720, 220, 28
    for (ticker, arm), group in df.groupby(["ticker", "arm"]):
        group = group.sort_values("day").reset_index(drop=True)
        if group.empty:
            continue
        x = [pad + i * (width - 2 * pad) / max(len(group) - 1, 1) for i in range(len(group))]
        flow = group["flow_imbalance"].astype(float).tolist()
        holders = group["robintrack_d_holders"].astype(float).fillna(0.0).tolist()
        flow_points = list(zip(x, scale(flow, height, pad)))
        holder_points = list(zip(x, scale(holders, height, pad)))
        day_to_x = {day.strftime("%Y-%m-%d"): xval for day, xval in zip(group["day"], x)}
        event_lines = []
        for day in top_news_days(snapshot_root, ticker):
            if day in day_to_x:
                xpos = day_to_x[day]
                event_lines.append(f'<line x1="{xpos:.1f}" y1="{pad}" x2="{xpos:.1f}" y2="{height-pad}" stroke="#999" stroke-dasharray="4 3" />')
        svg = "\n".join([
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="white" />',
            f'<text x="{pad}" y="18" font-family="Arial" font-size="13">{ticker} {arm}: flow vs Robintrack d_holders</text>',
            *event_lines,
            svg_polyline(holder_points, "#6666cc"),
            svg_polyline(flow_points, "#cc6633"),
            f'<text x="{pad}" y="{height-8}" font-family="Arial" font-size="11" fill="#cc6633">flow imbalance</text>',
            f'<text x="{pad+130}" y="{height-8}" font-family="Arial" font-size="11" fill="#6666cc">Robintrack d_holders</text>',
            "</svg>",
        ])
        (fig_dir / f"p3_event_{ticker}_{arm}.svg").write_text(svg)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("runs/p3"))
    parser.add_argument("--snapshot-root", type=Path, default=Path("data/snapshots/g1"))
    parser.add_argument("--fig-dir", type=Path, default=Path("docs/figures"))
    parser.add_argument("--rq1-out", type=Path, default=Path("docs/RQ1_REPORT.md"))
    parser.add_argument("--rq2-out", type=Path, default=Path("docs/RQ2_REPORT.md"))
    args = parser.parse_args()

    df = load_sim_rows(args.input_dir)
    rq1 = rq1_rows(df)
    rq2 = rq2_rows(df)
    write_event_svgs(df, args.snapshot_root, args.fig_dir)
    args.rq1_out.write_text(render_rq1(rq1))
    args.rq2_out.write_text(render_rq2(rq2, rq1, args.fig_dir))
    print(g3_gate_summary(rq1, rq2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
