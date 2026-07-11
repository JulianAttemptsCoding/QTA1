"""Plot simulated auction price against actual close for P3/P4 splits."""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


RUN_RE = re.compile(
    r"^(?P<prefix>calib-2019|oos-2025)-g1-"
    r"(?:(?P<experiment>scaling|news_off|personas_off)-)?"
    r"(?P<ticker>[a-z]+)-(?P<arm>[a-z]+)"
    r"(?:-n(?P<n_agents>\d+))?-v(?P<version>\d+)$"
)


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def discover_sim_paths(root: Path) -> list[Path]:
    split_roots = [
        root / "p3",
        root / "p4" / "main",
        root / "p4" / "scaling",
        root / "p4" / "news-off",
        root / "p4" / "personas-off",
    ]
    paths: list[Path] = []
    for split_root in split_roots:
        if split_root.exists():
            paths.extend(sorted(split_root.rglob("sim.jsonl")))
    return sorted(paths)


def classify_run(run_id: str) -> dict[str, Any]:
    match = RUN_RE.match(run_id)
    if not match:
        raise ValueError(f"Unrecognized run_id: {run_id}")
    prefix = match.group("prefix")
    experiment = match.group("experiment") or "main"
    n_agents = int(match.group("n_agents") or (200 if prefix == "oos-2025" else 100))
    split = "calib-2019" if prefix == "calib-2019" else "oos-2025-main"
    if prefix == "oos-2025" and experiment != "main":
        split = "oos-2025-followups"
    config = "main_n200" if experiment == "main" and prefix == "oos-2025" else experiment
    if experiment != "main":
        config = f"{experiment}_n{n_agents}"
    elif prefix == "calib-2019":
        config = match.group("arm")
    return {
        "split": split,
        "is_oos": prefix == "oos-2025",
        "experiment": experiment,
        "config": config,
        "ticker": match.group("ticker").upper(),
        "arm": match.group("arm"),
        "n_agents": n_agents,
    }


def load_run(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = pd.DataFrame(iter_jsonl(path))
    if frame.empty:
        raise ValueError(f"Empty sim file: {path}")
    run_id = str(frame["run_id"].iloc[0])
    meta = classify_run(run_id)
    meta["run_id"] = run_id
    meta["path"] = path
    frame["day"] = pd.to_datetime(frame["day"])
    frame = frame.sort_values("day").reset_index(drop=True)
    frame["actual_return"] = frame["real_close"].pct_change()
    frame["sim_return"] = frame["auction_price"].pct_change()
    if "next_day_return" in frame.columns and frame["next_day_return"].notna().any():
        frame["next_return"] = frame["next_day_return"]
    else:
        frame["next_return"] = frame["real_close"].pct_change().shift(-1)
    frame["mispricing"] = (frame["auction_price"] / frame["real_close"]) - 1.0
    frame["spread_position"] = np.sign(frame["mispricing"].to_numpy(float))
    return frame, meta


def pearson(left: pd.Series, right: pd.Series) -> float:
    subset = pd.concat([left, right], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(subset) < 3:
        return float("nan")
    a = subset.iloc[:, 0].to_numpy(float)
    b = subset.iloc[:, 1].to_numpy(float)
    if np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def annualized_sharpe(returns: pd.Series) -> float:
    values = returns.replace([np.inf, -np.inf], np.nan).dropna().to_numpy(float)
    if len(values) < 3 or np.std(values, ddof=1) == 0:
        return 0.0
    return float(np.sqrt(252.0) * np.mean(values) / np.std(values, ddof=1))


def hit_rate(signal: pd.Series, target: pd.Series) -> float:
    subset = pd.concat([signal, target], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if subset.empty:
        return float("nan")
    sig = subset.iloc[:, 0].to_numpy(float)
    tgt = subset.iloc[:, 1].to_numpy(float)
    mask = sig != 0
    if not mask.any():
        return 0.5
    return float((np.sign(sig[mask]) == np.sign(tgt[mask])).mean())


def spread_strategy(frame: pd.DataFrame, cost_bps: float) -> pd.Series:
    pos = frame["spread_position"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    turnover = (pos - pos.shift(1).fillna(0.0)).abs()
    cost = turnover * (cost_bps / 10000.0)
    return pos * frame["next_return"] - cost


def metrics_for_run(frame: pd.DataFrame, meta: dict[str, Any], figure: Path, cost_bps: float) -> dict[str, Any]:
    actual_ret = frame["real_close"].pct_change()
    sim_ret = frame["auction_price"].pct_change()
    spread_net = spread_strategy(frame, cost_bps)
    return {
        **{key: meta[key] for key in ["split", "is_oos", "ticker", "arm", "config", "n_agents", "run_id"]},
        "days": int(len(frame)),
        "start": str(frame["day"].min().date()),
        "end": str(frame["day"].max().date()),
        "actual_start": float(frame["real_close"].iloc[0]),
        "actual_end": float(frame["real_close"].iloc[-1]),
        "sim_start": float(frame["auction_price"].iloc[0]),
        "sim_end": float(frame["auction_price"].iloc[-1]),
        "level_corr": pearson(frame["auction_price"], frame["real_close"]),
        "return_corr": pearson(sim_ret, actual_ret),
        "sim_return_hit": hit_rate(sim_ret, actual_ret),
        "spread_next_hit": hit_rate(frame["mispricing"], frame["next_return"]),
        "spread_net_mean_bps": float(spread_net.replace([np.inf, -np.inf], np.nan).dropna().mean() * 10000.0),
        "spread_net_sharpe": annualized_sharpe(spread_net),
        "figure": figure.as_posix(),
    }


def points(values: list[float], width: int, height: int, margin: int, y_min: float, y_max: float) -> str:
    if len(values) == 1:
        x_values = [margin + (width - 2 * margin) / 2]
    else:
        x_values = [
            margin + idx * (width - 2 * margin) / (len(values) - 1)
            for idx in range(len(values))
        ]
    scale = y_max - y_min if y_max > y_min else 1.0
    pairs = []
    for x, value in zip(x_values, values):
        y = height - margin - ((value - y_min) / scale) * (height - 2 * margin)
        pairs.append(f"{x:.1f},{y:.1f}")
    return " ".join(pairs)


def write_price_svg(frame: pd.DataFrame, meta: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    width, height, margin = 920, 420, 58
    actual = frame["real_close"].astype(float).to_list()
    sim = frame["auction_price"].astype(float).to_list()
    y_values = actual + sim
    y_min, y_max = min(y_values), max(y_values)
    pad = (y_max - y_min) * 0.08 or max(abs(y_max), 1.0) * 0.05
    y_min -= pad
    y_max += pad
    title = (
        f"{meta['split']} {meta['ticker']} {meta['config']} "
        f"({meta['arm']}, {frame['day'].min().date()} to {frame['day'].max().date()})"
    )
    grid = []
    for idx in range(5):
        y = margin + idx * (height - 2 * margin) / 4
        value = y_max - idx * (y_max - y_min) / 4
        grid.append(
            f'<line x1="{margin}" y1="{y:.1f}" x2="{width - margin}" y2="{y:.1f}" stroke="#e6e8ef"/>'
        )
        grid.append(
            f'<text x="12" y="{y + 4:.1f}" font-size="12" fill="#4b5563">{value:.2f}</text>'
        )
    svg = "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{margin}" y="28" font-size="18" font-family="Arial" font-weight="700" fill="#111827">{html.escape(title)}</text>',
        *grid,
        f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#111827"/>',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#111827"/>',
        f'<polyline points="{points(actual, width, height, margin, y_min, y_max)}" fill="none" stroke="#2563eb" stroke-width="2.4"/>',
        f'<polyline points="{points(sim, width, height, margin, y_min, y_max)}" fill="none" stroke="#dc2626" stroke-width="2.4"/>',
        f'<text x="{margin}" y="{height - 20}" font-size="12" fill="#4b5563">{frame["day"].min().date()}</text>',
        f'<text x="{width - margin - 82}" y="{height - 20}" font-size="12" fill="#4b5563">{frame["day"].max().date()}</text>',
        f'<rect x="{width - 245}" y="44" width="14" height="14" fill="#2563eb"/>',
        f'<text x="{width - 224}" y="56" font-size="13" fill="#111827">actual close</text>',
        f'<rect x="{width - 245}" y="68" width="14" height="14" fill="#dc2626"/>',
        f'<text x="{width - 224}" y="80" font-size="13" fill="#111827">sim auction price</text>',
        "</svg>",
    ])
    output.write_text(svg, encoding="utf-8")


def fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if not math.isfinite(value):
            return "NA"
        return f"{value:.4f}"
    return str(value)


def markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    lines = [
        "| " + " | ".join(title for title, _ in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        cells = []
        for _, key in columns:
            value = row.get(key, "")
            cells.append(fmt(value).replace("|", r"\|"))
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def render_report(rows: list[dict[str, Any]], cost_bps: float) -> str:
    split_rows = []
    for split, group in pd.DataFrame(rows).groupby("split", sort=True):
        split_rows.append({
            "split": split,
            "oos": bool(group["is_oos"].iloc[0]),
            "runs": int(len(group)),
            "tickers": int(group["ticker"].nunique()),
            "start": str(group["start"].min()),
            "end": str(group["end"].max()),
            "configs": ", ".join(sorted(group["config"].unique())),
        })
    lines = [
        "# Simulated Price vs Actual Price",
        "",
        "Yes, the project has OOS data. P4 main and P4 follow-up runs are OOS; P3 is the 2019 calibration split.",
        "",
        "The simulated price is the LLM-agent auction-clearing price (`auction_price`) and the actual price is the archived daily close (`real_close`). This charting pass is diagnostic: the original RQ3 prediction track tested flow imbalance, not the auction price as a fair-value model.",
        "",
        "## Data Splits",
        "",
    ]
    lines.extend(markdown_table(split_rows, [
        ("Split", "split"), ("OOS", "oos"), ("Runs", "runs"), ("Tickers", "tickers"),
        ("Start", "start"), ("End", "end"), ("Configs", "configs"),
    ]))
    lines += [
        "",
        "## Run-Level Price Tracking Metrics",
        "",
        f"`spread_net_*` is an exploratory close-to-close diagnostic using `sign(auction_price / real_close - 1)` with `{cost_bps:.1f}` bps one-way turnover cost. It is not an arbitrage claim.",
        "",
    ]
    lines.extend(markdown_table(rows, [
        ("Split", "split"), ("Ticker", "ticker"), ("Arm", "arm"), ("Config", "config"),
        ("Days", "days"), ("Start", "start"), ("End", "end"),
        ("Level corr", "level_corr"), ("Return corr", "return_corr"),
        ("Sim ret hit", "sim_return_hit"), ("Spread next hit", "spread_next_hit"),
        ("Spread net mean bps", "spread_net_mean_bps"), ("Spread net Sharpe", "spread_net_sharpe"),
        ("Figure", "figure"),
    ]))
    lines += [
        "",
        "## Interpretation Guardrails",
        "",
        "- A flat or weakly correlated auction path is expected for some runs because the auction track was designed for realism diagnostics, not direct price forecasting.",
        "- A positive spread diagnostic can be a post-hoc artifact unless it survives pre-registration, costs, borrow/shortability constraints, capacity, and multiple-testing correction.",
        "- Treat these plots as model diagnostics and inputs to a future registered trading test, not investment advice.",
    ]
    return "\n".join(lines) + "\n"


def collect(root: Path, figure_dir: Path, cost_bps: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in discover_sim_paths(root):
        frame, meta = load_run(path)
        rel = Path(meta["split"]) / f"{meta['run_id']}.svg"
        figure = figure_dir / rel
        write_price_svg(frame, meta, figure)
        rows.append(metrics_for_run(frame, meta, figure, cost_bps))
    return sorted(rows, key=lambda row: (row["split"], row["ticker"], row["config"], row["arm"]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", type=Path, default=Path("runs"))
    parser.add_argument("--figure-dir", type=Path, default=Path("docs/figures/price_tracking"))
    parser.add_argument("--output", type=Path, default=Path("docs/PRICE_TRACKING_REPORT.md"))
    parser.add_argument("--cost-bps", type=float, default=25.0)
    args = parser.parse_args()

    rows = collect(args.runs_root, args.figure_dir, args.cost_bps)
    if not rows:
        raise FileNotFoundError(f"No sim.jsonl files found under {args.runs_root}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(rows, args.cost_bps), encoding="utf-8")
    print(json.dumps({
        "figures": len(rows),
        "output": str(args.output),
        "splits": sorted({row["split"] for row in rows}),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
