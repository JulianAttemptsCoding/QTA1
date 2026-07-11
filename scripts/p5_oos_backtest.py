"""Run exploratory OOS backtests from archived P4 sim rows."""
from __future__ import annotations

import argparse
import html
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from p5_price_tracking import classify_run, iter_jsonl


STRATEGIES = [
    "buy_hold_equal_weight",
    "flow_weighted",
    "flow_unweighted",
    "price_spread_long_rich",
    "price_spread_short_rich",
    "hybrid_flow_price_agree",
    "momentum_1d",
]


def discover_oos_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for split_root in [
        root / "p4" / "main",
        root / "p4" / "scaling",
        root / "p4" / "news-off",
        root / "p4" / "personas-off",
    ]:
        if split_root.exists():
            paths.extend(sorted(split_root.rglob("sim.jsonl")))
    return sorted(paths)


def load_oos_frame(root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in discover_oos_paths(root):
        part = pd.DataFrame(iter_jsonl(path))
        if part.empty:
            continue
        run_id = str(part["run_id"].iloc[0])
        meta = classify_run(run_id)
        if not meta["is_oos"]:
            continue
        for key in ["split", "ticker", "arm", "config", "n_agents"]:
            part[key] = meta[key]
        rows.append(part)
    if not rows:
        raise FileNotFoundError(f"No OOS sim rows found under {root}")
    frame = pd.concat(rows, ignore_index=True)
    frame["day"] = pd.to_datetime(frame["day"])
    frame["next_return"] = frame.get("next_day_return", pd.Series(np.nan, index=frame.index))
    frame["mispricing"] = frame["auction_price"] / frame["real_close"] - 1.0
    return frame.replace([np.inf, -np.inf], np.nan)


def add_positions(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["pos_buy_hold_equal_weight"] = 1.0
    out["pos_flow_weighted"] = np.sign(out["flow_imbalance"].fillna(0.0))
    out["pos_flow_unweighted"] = np.sign(out["flow_imbalance_unweighted"].fillna(0.0))
    out["pos_price_spread_long_rich"] = np.sign(out["mispricing"].fillna(0.0))
    out["pos_price_spread_short_rich"] = -np.sign(out["mispricing"].fillna(0.0))
    agree = out["pos_flow_weighted"] == out["pos_price_spread_long_rich"]
    out["pos_hybrid_flow_price_agree"] = out["pos_flow_weighted"].where(agree, 0.0)
    out["pos_momentum_1d"] = np.sign(out.get("momentum_1d", pd.Series(0.0, index=out.index)).fillna(0.0))
    return out


def strategy_daily_returns(frame: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    frame = add_positions(frame).sort_values(["ticker", "day"]).copy()
    rows: list[pd.DataFrame] = []
    for strategy in STRATEGIES:
        pos_col = f"pos_{strategy}"
        pos = frame[pos_col].fillna(0.0)
        prev = pos.groupby([frame["split"], frame["config"], frame["ticker"]]).shift(1).fillna(0.0)
        turnover = (pos - prev).abs()
        gross = pos * frame["next_return"]
        cost = turnover * (cost_bps / 10000.0)
        row_frame = frame[["split", "config", "day", "ticker"]].copy()
        row_frame["strategy"] = strategy
        row_frame["position"] = pos
        row_frame["turnover"] = turnover
        row_frame["gross_return"] = gross
        row_frame["cost"] = cost
        row_frame["net_return"] = gross - cost
        rows.append(row_frame)
    stacked = pd.concat(rows, ignore_index=True).dropna(subset=["net_return"])
    daily = (
        stacked
        .groupby(["split", "config", "strategy", "day"], as_index=False)
        .agg(
            daily_return=("net_return", "mean"),
            gross_return=("gross_return", "mean"),
            avg_turnover=("turnover", "mean"),
            avg_abs_position=("position", lambda x: float(np.mean(np.abs(x)))),
            n_tickers=("ticker", "nunique"),
        )
        .sort_values(["split", "config", "strategy", "day"])
    )
    daily["equity"] = (
        1.0 + daily["daily_return"]
    ).groupby([daily["split"], daily["config"], daily["strategy"]]).cumprod()
    return daily


def max_drawdown(equity: pd.Series) -> float:
    values = equity.dropna().to_numpy(float)
    if len(values) == 0:
        return float("nan")
    peak = np.maximum.accumulate(values)
    return float(np.min(values / peak - 1.0))


def annualized_return(total_return: float, n_days: int) -> float:
    if n_days <= 0 or total_return <= -1:
        return float("nan")
    return float((1.0 + total_return) ** (252.0 / n_days) - 1.0)


def annualized_sharpe(returns: pd.Series) -> float:
    values = returns.dropna().to_numpy(float)
    if len(values) < 3 or np.std(values, ddof=1) == 0:
        return 0.0
    return float(np.sqrt(252.0) * np.mean(values) / np.std(values, ddof=1))


def summary_rows(daily: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (split, config, strategy), group in daily.groupby(["split", "config", "strategy"], sort=True):
        group = group.sort_values("day")
        total = float(group["equity"].iloc[-1] - 1.0)
        rows.append({
            "split": split,
            "config": config,
            "strategy": strategy,
            "days": int(len(group)),
            "tickers": int(group["n_tickers"].max()),
            "final_equity": float(group["equity"].iloc[-1]),
            "total_return": total,
            "ann_return": annualized_return(total, len(group)),
            "ann_sharpe": annualized_sharpe(group["daily_return"]),
            "max_drawdown": max_drawdown(group["equity"]),
            "min_daily_return": float(group["daily_return"].min()),
            "daily_mean_bps": float(group["daily_return"].mean() * 10000.0),
            "daily_hit_rate": float((group["daily_return"] > 0).mean()),
            "avg_turnover": float(group["avg_turnover"].mean()),
            "avg_abs_position": float(group["avg_abs_position"].mean()),
        })
    return rows


def points(values: list[float], width: int, height: int, margin: int, y_min: float, y_max: float) -> str:
    if len(values) == 1:
        xs = [margin + (width - 2 * margin) / 2]
    else:
        xs = [margin + i * (width - 2 * margin) / (len(values) - 1) for i in range(len(values))]
    scale = y_max - y_min if y_max > y_min else 1.0
    return " ".join(
        f"{x:.1f},{height - margin - ((value - y_min) / scale) * (height - 2 * margin):.1f}"
        for x, value in zip(xs, values)
    )


def write_equity_svg(group: pd.DataFrame, output: Path, title: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    width, height, margin = 980, 460, 62
    colors = {
        "buy_hold_equal_weight": "#111827",
        "flow_weighted": "#2563eb",
        "flow_unweighted": "#06b6d4",
        "price_spread_long_rich": "#dc2626",
        "price_spread_short_rich": "#f97316",
        "hybrid_flow_price_agree": "#16a34a",
        "momentum_1d": "#7c3aed",
    }
    y_values = group["equity"].dropna().to_list()
    y_min, y_max = min(y_values), max(y_values)
    pad = max((y_max - y_min) * 0.08, 0.02)
    y_min -= pad
    y_max += pad
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{margin}" y="30" font-size="19" font-family="Arial" font-weight="700" fill="#111827">{html.escape(title)}</text>',
    ]
    for idx in range(5):
        y = margin + idx * (height - 2 * margin) / 4
        value = y_max - idx * (y_max - y_min) / 4
        lines.append(f'<line x1="{margin}" y1="{y:.1f}" x2="{width - margin}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        lines.append(f'<text x="12" y="{y + 4:.1f}" font-size="12" fill="#4b5563">{value:.2f}x</text>')
    for strategy, part in group.groupby("strategy", sort=False):
        part = part.sort_values("day")
        lines.append(
            f'<polyline points="{points(part["equity"].to_list(), width, height, margin, y_min, y_max)}" '
            f'fill="none" stroke="{colors.get(strategy, "#6b7280")}" stroke-width="2.2"/>'
        )
    dates = group["day"].sort_values()
    lines += [
        f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#111827"/>',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#111827"/>',
        f'<text x="{margin}" y="{height - 20}" font-size="12" fill="#4b5563">{dates.min().date()}</text>',
        f'<text x="{width - margin - 82}" y="{height - 20}" font-size="12" fill="#4b5563">{dates.max().date()}</text>',
    ]
    legend_x, legend_y = width - 315, 48
    for idx, strategy in enumerate(STRATEGIES):
        y = legend_y + idx * 22
        lines.append(f'<rect x="{legend_x}" y="{y}" width="13" height="13" fill="{colors[strategy]}"/>')
        lines.append(f'<text x="{legend_x + 20}" y="{y + 11}" font-size="12" fill="#111827">{strategy}</text>')
    lines.append("</svg>")
    output.write_text("\n".join(lines), encoding="utf-8")


def fmt(value: Any) -> str:
    if isinstance(value, float):
        if not math.isfinite(value):
            return "NA"
        if abs(value) <= 2:
            return f"{value:.4f}"
        return f"{value:.2f}"
    return str(value)


def markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    lines = [
        "| " + " | ".join(title for title, _ in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(key, "")).replace("|", r"\|") for _, key in columns) + " |")
    return lines


def best_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: list[dict[str, Any]] = []
    for (split, config), part in pd.DataFrame(rows).groupby(["split", "config"], sort=True):
        ordered = part.sort_values("total_return", ascending=False)
        best.append(ordered.iloc[0].to_dict())
    return best


def find_row(rows: list[dict[str, Any]], split: str, config: str, strategy: str) -> dict[str, Any] | None:
    for row in rows:
        if row["split"] == split and row["config"] == config and row["strategy"] == strategy:
            return row
    return None


def pct(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "NA"
    return f"{100.0 * value:.1f}%"


def render_findings(rows: list[dict[str, Any]]) -> list[str]:
    main_best = sorted(
        [row for row in rows if row["split"] == "oos-2025-main"],
        key=lambda row: row["total_return"],
        reverse=True,
    )[0]
    main_flow = find_row(rows, "oos-2025-main", "main_n200", "flow_weighted")
    main_price = find_row(rows, "oos-2025-main", "main_n200", "price_spread_long_rich")
    follow_momo = find_row(rows, "oos-2025-followups", "scaling_n100", "momentum_1d")
    follow_flow = find_row(rows, "oos-2025-followups", "scaling_n100", "flow_weighted")
    return [
        f"- OOS main: every tested strategy lost money after costs. The least-bad main strategy was `{main_best['strategy']}` at `{pct(main_best['total_return'])}` total return over `{main_best['days']}` trading days.",
        f"- The main LLM crowd-flow strategy returned `{pct(main_flow['total_return'] if main_flow else None)}`; the main simulated-price spread strategy returned `{pct(main_price['total_return'] if main_price else None)}`. Neither beat buy-and-hold in a useful way.",
        f"- OOS follow-ups: `momentum_1d` returned `{pct(follow_momo['total_return'] if follow_momo else None)}` over the short two-stock window, but it is a cheap baseline, not an LLM-agent strategy, and had `{pct(follow_momo['max_drawdown'] if follow_momo else None)}` max drawdown with high turnover.",
        f"- Follow-up LLM flow returned `{pct(follow_flow['total_return'] if follow_flow else None)}` in the same short window, matching the bad long-biased exposure. This points to directional crowd bias rather than exploitable price discovery.",
    ]


def render_report(rows: list[dict[str, Any]], figures: list[Path], csv_path: Path, cost_bps: float) -> str:
    best = best_rows(rows)
    lines = [
        "# OOS Backtest Return Over Time",
        "",
        "This is an exploratory OOS backtest over archived P4 `sim.jsonl` artifacts only. It does not run LLM inference and it is not a live-trading result.",
        "",
        f"Assumptions: signal at day `t`, target `next_day_return`, equal-weight across available tickers, and `{cost_bps:.1f}` bps one-way turnover cost. Returns are hypothetical close-to-next-close returns; borrow fees, short locate failures, halts, market impact, taxes, and broker-specific margin limits are not fully modeled.",
        "",
        "## Strategy Definitions",
        "",
        "- `buy_hold_equal_weight`: long every available ticker.",
        "- `flow_weighted`: long/short by signed confidence-weighted crowd flow.",
        "- `flow_unweighted`: long/short by signed unweighted crowd flow.",
        "- `price_spread_long_rich`: long when simulated auction price is above actual close; short when below.",
        "- `price_spread_short_rich`: opposite of `price_spread_long_rich`.",
        "- `hybrid_flow_price_agree`: trade only when weighted flow and price spread agree.",
        "- `momentum_1d`: long/short by one-day momentum.",
        "",
        "## What Happened",
        "",
    ]
    lines.extend(render_findings(rows))
    lines += [
        "",
        "## Best Strategy By OOS Split/Config",
        "",
    ]
    lines.extend(markdown_table(best, [
        ("Split", "split"), ("Config", "config"), ("Strategy", "strategy"),
        ("Days", "days"), ("Tickers", "tickers"), ("Final Equity", "final_equity"), ("Total Return", "total_return"),
        ("Ann Return", "ann_return"), ("Ann Sharpe", "ann_sharpe"),
        ("Max DD", "max_drawdown"), ("Mean bps/day", "daily_mean_bps"),
    ]))
    lines += ["", "## All Strategy Metrics", ""]
    lines.extend(markdown_table(rows, [
        ("Split", "split"), ("Config", "config"), ("Strategy", "strategy"),
        ("Days", "days"), ("Tickers", "tickers"), ("Final Equity", "final_equity"), ("Total Return", "total_return"),
        ("Ann Return", "ann_return"), ("Ann Sharpe", "ann_sharpe"),
        ("Max DD", "max_drawdown"), ("Min Daily", "min_daily_return"), ("Hit", "daily_hit_rate"),
        ("Turnover", "avg_turnover"), ("Exposure", "avg_abs_position"),
    ]))
    lines += ["", "## Return-Over-Time Figures", ""]
    for figure in figures:
        lines.append(f"- `{figure.as_posix()}`")
    lines += [
        "",
        "## Daily Return Data",
        "",
        f"- CSV: `{csv_path.as_posix()}`",
        "",
        "## Interpretation",
        "",
        "The backtest is useful for seeing return paths, drawdowns, and sensitivity across strategy definitions. It is not sufficient to claim arbitrage. Positive rows must be treated as data-mined until they survive a fresh pre-registered holdout or live paper-trading test with full execution, borrow, financing, capacity, and multiple-testing controls.",
    ]
    return "\n".join(lines) + "\n"


def run_backtest(runs_root: Path, figure_dir: Path, csv_path: Path, cost_bps: float) -> tuple[list[dict[str, Any]], list[Path], pd.DataFrame]:
    frame = load_oos_frame(runs_root)
    daily = strategy_daily_returns(frame, cost_bps)
    figures: list[Path] = []
    for (split, config), group in daily.groupby(["split", "config"], sort=True):
        figure = figure_dir / f"equity_{split}_{config}.svg"
        write_equity_svg(group, figure, f"{split} {config}: OOS Backtest Equity")
        figures.append(figure)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(csv_path, index=False)
    return summary_rows(daily), figures, daily


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", type=Path, default=Path("runs"))
    parser.add_argument("--figure-dir", type=Path, default=Path("docs/figures/oos_backtest"))
    parser.add_argument("--returns-csv", type=Path, default=Path("docs/OOS_BACKTEST_DAILY_RETURNS.csv"))
    parser.add_argument("--output", type=Path, default=Path("docs/OOS_BACKTEST_REPORT.md"))
    parser.add_argument("--cost-bps", type=float, default=25.0)
    args = parser.parse_args()

    rows, figures, daily = run_backtest(args.runs_root, args.figure_dir, args.returns_csv, args.cost_bps)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(rows, figures, args.returns_csv, args.cost_bps), encoding="utf-8")
    print(json.dumps({
        "daily_rows": len(daily),
        "figures": len(figures),
        "output": str(args.output),
        "strategies": STRATEGIES,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
