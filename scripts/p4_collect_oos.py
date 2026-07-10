"""Collect P4 OOS artifacts into reproducible RQ3 and G5 statistics."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agorasim.evals import (
    deflated_sharpe,
    diebold_mariano,
    hit_rate,
    information_coefficient,
)


SIGNALS = {
    "crowd_weighted": "flow_imbalance",
    "crowd_unweighted": "flow_imbalance_unweighted",
    "single_qwen": "single_model_signal",
    "momentum_1d": "momentum_1d",
    "momentum_5d": "momentum_5d",
    "momentum_20d": "momentum_20d",
    "ar1": "ar1_signal",
    "logistic": "logistic_signal",
}


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load_sim_rows(input_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(input_dir.rglob("sim.jsonl")):
        rows.extend(iter_jsonl(path))
    if not rows:
        raise FileNotFoundError(f"No sim.jsonl files found under {input_dir}")
    frame = pd.DataFrame(rows)
    required = {
        "ticker",
        "day",
        "next_day_return",
        "flow_imbalance",
        "flow_imbalance_unweighted",
        "decision_entropy",
        "model_flow_imbalance",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Missing P4 columns: {missing}")
    frame["day"] = pd.to_datetime(frame["day"])
    frame["single_model_signal"] = frame["model_flow_imbalance"].map(single_model_signal)
    return frame.sort_values(["ticker", "day"]).reset_index(drop=True)


def single_model_signal(model_flows: Any) -> float:
    if not isinstance(model_flows, dict) or not model_flows:
        return float("nan")
    preferred = [
        key for key in model_flows
        if "Qwen2.5-1.5B-Instruct" in key
    ]
    key = sorted(preferred or model_flows)[0]
    return float(model_flows[key])


def add_snapshot_features(frame: pd.DataFrame, snapshot_root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ticker in sorted(frame["ticker"].unique()):
        path = snapshot_root / "oos" / ticker / "bars_1d.jsonl"
        if not path.exists():
            continue
        for row in iter_jsonl(path):
            close = float(row["c"])
            rows.append({
                "ticker": ticker,
                "day": pd.to_datetime(str(row["t"])[:10]),
                "bar_volume": float(row["v"]),
                "bar_range": (float(row["h"]) - float(row["l"])) / close if close else 0.0,
            })
    if rows:
        frame = frame.merge(pd.DataFrame(rows), on=["ticker", "day"], how="left")
    else:
        frame["bar_volume"] = np.nan
        frame["bar_range"] = np.nan
    frame["volume_z20"] = frame.groupby("ticker", group_keys=False)["bar_volume"].transform(
        lambda values: (
            (values - values.rolling(20, min_periods=5).mean())
            / values.rolling(20, min_periods=5).std(ddof=0).replace(0, np.nan)
        )
    )
    return frame


def fit_linear(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), x])
    return np.linalg.lstsq(design, y, rcond=None)[0]


def add_ar1_signal(frame: pd.DataFrame, min_train: int = 20) -> pd.DataFrame:
    frame["real_return_1d"] = frame.groupby("ticker")["real_close"].pct_change()
    frame["ar1_signal"] = np.nan
    for _, group in frame.groupby("ticker", sort=False):
        indices = group.index.to_list()
        for pos, idx in enumerate(indices):
            train = frame.loc[indices[:pos], ["real_return_1d", "next_day_return"]].dropna()
            current = frame.at[idx, "real_return_1d"]
            if len(train) < min_train or pd.isna(current):
                continue
            beta = fit_linear(
                train["real_return_1d"].to_numpy(float),
                train["next_day_return"].to_numpy(float),
            )
            frame.at[idx, "ar1_signal"] = beta[0] + beta[1] * float(current)
    return frame


def logistic_predict(
    train_x: np.ndarray,
    train_y: np.ndarray,
    current_x: np.ndarray,
    ridge: float = 1e-3,
) -> float:
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    scale[scale == 0] = 1.0
    x = (train_x - mean) / scale
    current = (current_x - mean) / scale
    design = np.column_stack([np.ones(len(x)), x])
    beta = np.zeros(design.shape[1])
    penalty = np.eye(len(beta)) * ridge
    penalty[0, 0] = 0.0
    for _ in range(30):
        logits = np.clip(design @ beta, -30, 30)
        prob = 1.0 / (1.0 + np.exp(-logits))
        weights = np.maximum(prob * (1.0 - prob), 1e-6)
        hessian = design.T @ (weights[:, None] * design) + penalty
        gradient = design.T @ (train_y - prob) - penalty @ beta
        step = np.linalg.solve(hessian, gradient)
        beta += step
        if np.linalg.norm(step) < 1e-7:
            break
    current_design = np.r_[1.0, current]
    return float(1.0 / (1.0 + np.exp(-np.clip(current_design @ beta, -30, 30))) - 0.5)


def add_logistic_signal(frame: pd.DataFrame, min_train: int = 40) -> pd.DataFrame:
    features = ["momentum_1d", "momentum_5d", "momentum_20d", "bar_range", "volume_z20"]
    frame["logistic_signal"] = np.nan
    for _, group in frame.groupby("ticker", sort=False):
        indices = group.index.to_list()
        for pos, idx in enumerate(indices):
            train = frame.loc[indices[:pos], features + ["next_day_return"]].dropna()
            current = frame.loc[idx, features]
            if len(train) < min_train or current.isna().any():
                continue
            target = (train["next_day_return"].to_numpy(float) > 0).astype(float)
            if target.min() == target.max():
                frame.at[idx, "logistic_signal"] = float(target[0] - 0.5)
                continue
            frame.at[idx, "logistic_signal"] = logistic_predict(
                train[features].to_numpy(float),
                target,
                current.to_numpy(float),
            )
    return frame


def clean_arrays(group: pd.DataFrame, column: str) -> tuple[np.ndarray, np.ndarray]:
    subset = group[[column, "next_day_return"]].replace([np.inf, -np.inf], np.nan).dropna()
    return subset[column].to_numpy(float), subset["next_day_return"].to_numpy(float)


def annualized_sharpe(strategy_returns: np.ndarray) -> float:
    if len(strategy_returns) < 3 or np.std(strategy_returns, ddof=1) == 0:
        return 0.0
    return float(np.sqrt(252.0) * np.mean(strategy_returns) / np.std(strategy_returns, ddof=1))


def strategy_returns(group: pd.DataFrame, column: str) -> np.ndarray:
    subset = group[["day", column, "next_day_return"]].replace([np.inf, -np.inf], np.nan).dropna()
    subset = subset.assign(
        strategy_return=np.sign(subset[column].to_numpy(float)) * subset["next_day_return"].to_numpy(float)
    )
    return subset.groupby("day")["strategy_return"].mean().to_numpy(float)


def metric_values(group: pd.DataFrame, column: str) -> dict[str, float | int]:
    signal, returns = clean_arrays(group, column)
    strategy = strategy_returns(group, column)
    return {
        "n": len(signal),
        "ic": information_coefficient(signal, returns) if len(signal) >= 3 else 0.0,
        "hit_rate": hit_rate(signal, returns) if len(signal) else 0.5,
        "sharpe": annualized_sharpe(strategy),
        "mean_strategy_return": float(strategy.mean()) if len(strategy) else 0.0,
    }


def block_bootstrap_ci(
    group: pd.DataFrame,
    column: str,
    metric: Callable[[pd.DataFrame, str], float],
    *,
    block_size: int = 5,
    repetitions: int = 500,
    seed: int = 401,
) -> tuple[float, float]:
    if metric in {ic_stat, hit_stat}:
        return fast_block_bootstrap_ci(
            group,
            column,
            statistic="ic" if metric is ic_stat else "hit",
            block_size=block_size,
            repetitions=repetitions,
            seed=seed,
        )
    rng = np.random.default_rng(seed)
    ticker_groups = [part.reset_index(drop=True) for _, part in group.groupby("ticker")]
    estimates: list[float] = []
    for _ in range(repetitions):
        sampled: list[pd.DataFrame] = []
        for part in ticker_groups:
            chunks = []
            while sum(len(chunk) for chunk in chunks) < len(part):
                start = int(rng.integers(0, max(len(part) - block_size + 1, 1)))
                chunks.append(part.iloc[start:start + block_size])
            sampled.append(pd.concat(chunks, ignore_index=True).iloc[:len(part)])
        estimate = metric(pd.concat(sampled, ignore_index=True), column)
        if math.isfinite(estimate):
            estimates.append(estimate)
    if not estimates:
        return float("nan"), float("nan")
    return tuple(float(value) for value in np.quantile(estimates, [0.025, 0.975]))


def fast_block_bootstrap_ci(
    group: pd.DataFrame,
    column: str,
    *,
    statistic: str,
    block_size: int = 5,
    repetitions: int = 500,
    seed: int = 401,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    ticker_arrays: list[tuple[np.ndarray, np.ndarray]] = []
    for _, part in group.groupby("ticker", sort=False):
        subset = part[[column, "next_day_return"]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(subset):
            ticker_arrays.append((
                subset[column].to_numpy(float),
                subset["next_day_return"].to_numpy(float),
            ))
    estimates: list[float] = []
    for _ in range(repetitions):
        sampled_signals: list[np.ndarray] = []
        sampled_returns: list[np.ndarray] = []
        for signals, returns in ticker_arrays:
            n = len(signals)
            if n == 0:
                continue
            picks: list[np.ndarray] = []
            while sum(len(pick) for pick in picks) < n:
                start = int(rng.integers(0, max(n - block_size + 1, 1)))
                picks.append(np.arange(start, min(start + block_size, n)))
            indices = np.concatenate(picks)[:n]
            sampled_signals.append(signals[indices])
            sampled_returns.append(returns[indices])
        if not sampled_signals:
            continue
        signal = np.concatenate(sampled_signals)
        target = np.concatenate(sampled_returns)
        if statistic == "ic":
            estimate = information_coefficient(signal, target) if len(signal) >= 3 else float("nan")
        elif statistic == "hit":
            estimate = hit_rate(signal, target) if len(signal) else float("nan")
        else:
            raise ValueError(statistic)
        if math.isfinite(estimate):
            estimates.append(float(estimate))
    if not estimates:
        return float("nan"), float("nan")
    return tuple(float(value) for value in np.quantile(estimates, [0.025, 0.975]))


def ic_stat(group: pd.DataFrame, column: str) -> float:
    return float(metric_values(group, column)["ic"])


def hit_stat(group: pd.DataFrame, column: str) -> float:
    return float(metric_values(group, column)["hit_rate"])


def evaluate_signals(frame: pd.DataFrame, bootstrap_repetitions: int = 500) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scopes = [(ticker, group) for ticker, group in frame.groupby("ticker")]
    scopes.append(("ALL", frame))
    for scope, group in scopes:
        for signal_name, column in SIGNALS.items():
            values = metric_values(group, column)
            row: dict[str, Any] = {"scope": scope, "signal": signal_name, **values}
            if scope == "ALL":
                row["ic_ci_low"], row["ic_ci_high"] = block_bootstrap_ci(
                    group, column, ic_stat, repetitions=bootstrap_repetitions
                )
                row["hit_ci_low"], row["hit_ci_high"] = block_bootstrap_ci(
                    group, column, hit_stat, repetitions=bootstrap_repetitions, seed=402
                )
            rows.append(row)
    return rows


def dm_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    crowd_column = SIGNALS["crowd_weighted"]
    rows = []
    for baseline_name, baseline_column in SIGNALS.items():
        if baseline_name == "crowd_weighted":
            continue
        subset = frame[["day", crowd_column, baseline_column, "next_day_return"]].dropna()
        target_sign = np.sign(subset["next_day_return"].to_numpy(float))
        subset = subset.assign(
            crowd_loss=(np.sign(subset[crowd_column].to_numpy(float)) != target_sign).astype(float),
            baseline_loss=(np.sign(subset[baseline_column].to_numpy(float)) != target_sign).astype(float),
        )
        daily_loss = subset.groupby("day")[["crowd_loss", "baseline_loss"]].mean()
        crowd_loss = daily_loss["crowd_loss"].to_numpy(float)
        baseline_loss = daily_loss["baseline_loss"].to_numpy(float)
        dm, p_value = diebold_mariano(crowd_loss, baseline_loss)
        rows.append({
            "baseline": baseline_name,
            "n": len(daily_loss),
            "dm": dm,
            "p_value": p_value,
            "crowd_error": float(crowd_loss.mean()) if len(daily_loss) else float("nan"),
            "baseline_error": float(baseline_loss.mean()) if len(daily_loss) else float("nan"),
        })
    return rows


def count_registered_trials(path: Path) -> int:
    pattern = re.compile(r"^\|\s*(\d+)\s*\|")
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if pattern.match(line))


def dsr_rows(frame: pd.DataFrame, trials_path: Path) -> list[dict[str, Any]]:
    n_trials = count_registered_trials(trials_path)
    strategies: dict[str, np.ndarray] = {}
    sharpes = []
    for name, column in SIGNALS.items():
        strategy = strategy_returns(frame, column)
        strategies[name] = strategy
        sharpes.append(annualized_sharpe(strategy) / math.sqrt(252.0))
    variance = float(np.var(sharpes, ddof=1)) if len(sharpes) > 1 else 0.0
    rows = []
    for name, strategy in strategies.items():
        if len(strategy) < 3:
            rows.append({"signal": name, "n": len(strategy), "dsr": 0.0})
            continue
        daily_sr = annualized_sharpe(strategy) / math.sqrt(252.0)
        centered = strategy - strategy.mean()
        std = strategy.std(ddof=1)
        skew = float(np.mean((centered / std) ** 3)) if std else 0.0
        kurt = float(np.mean((centered / std) ** 4)) if std else 3.0
        rows.append({
            "signal": name,
            "n": len(strategy),
            "n_trials": n_trials,
            "annualized_sharpe": daily_sr * math.sqrt(252.0),
            "dsr": deflated_sharpe(daily_sr, len(strategy), skew, kurt, n_trials, variance),
        })
    return rows


def fmt(value: Any) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    lines = [
        "| " + " | ".join(title for title, _ in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(key)) for _, key in columns) + " |")
    return lines


def render_report(
    metrics: list[dict[str, Any]],
    dm: list[dict[str, Any]],
    dsr: list[dict[str, Any]],
    frame: pd.DataFrame,
) -> str:
    pooled = [row for row in metrics if row["scope"] == "ALL"]
    per_ticker = [row for row in metrics if row["scope"] != "ALL"]
    lines = [
        "# RQ3 OOS Prediction Report",
        "",
        "- Source: frozen P4 alias-arm Vertex artifacts.",
        "- Forecast target: next-trading-day close-to-close return.",
        "- DM loss: directional 0-1 loss; negative DM favors the crowd.",
        "- Baselines are walk-forward and use only information available by each decision date.",
        "",
        "## Pooled Results",
        "",
    ]
    lines.extend(table(pooled, [
        ("Signal", "signal"), ("N", "n"), ("IC", "ic"), ("IC 2.5%", "ic_ci_low"),
        ("IC 97.5%", "ic_ci_high"), ("Hit", "hit_rate"), ("Hit 2.5%", "hit_ci_low"),
        ("Hit 97.5%", "hit_ci_high"), ("Sharpe", "sharpe"),
    ]))
    lines += ["", "## Diebold-Mariano vs Crowd", ""]
    lines.extend(table(dm, [
        ("Baseline", "baseline"), ("N", "n"), ("DM", "dm"), ("p", "p_value"),
        ("Crowd error", "crowd_error"), ("Baseline error", "baseline_error"),
    ]))
    lines += ["", "## Deflated Sharpe", ""]
    lines.extend(table(dsr, [
        ("Signal", "signal"), ("N", "n"), ("Trials", "n_trials"),
        ("Annualized Sharpe", "annualized_sharpe"), ("DSR", "dsr"),
    ]))
    lines += ["", "## Per-Ticker Results", ""]
    lines.extend(table(per_ticker, [
        ("Ticker", "scope"), ("Signal", "signal"), ("N", "n"), ("IC", "ic"),
        ("Hit", "hit_rate"), ("Sharpe", "sharpe"),
    ]))
    lines += [
        "",
        "## Herding Diagnostics",
        "",
        f"- Mean daily decision entropy: `{frame['decision_entropy'].mean():.4f}` bits.",
        f"- Median daily decision entropy: `{frame['decision_entropy'].median():.4f}` bits.",
        f"- Minimum daily decision entropy: `{frame['decision_entropy'].min():.4f}` bits.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("runs/p4"))
    parser.add_argument("--snapshot-root", type=Path, default=Path("data/snapshots/g1"))
    parser.add_argument("--trials", type=Path, default=Path("docs/TRIALS.md"))
    parser.add_argument("--output", type=Path, default=Path("docs/RQ3_REPORT.md"))
    parser.add_argument("--bootstrap-repetitions", type=int, default=1000)
    args = parser.parse_args()

    frame = load_sim_rows(args.input_dir)
    frame = add_snapshot_features(frame, args.snapshot_root)
    frame = add_ar1_signal(frame)
    frame = add_logistic_signal(frame)
    metrics = evaluate_signals(frame, args.bootstrap_repetitions)
    dm = dm_rows(frame)
    dsr = dsr_rows(frame, args.trials)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(metrics, dm, dsr, frame), encoding="utf-8")
    print(json.dumps({
        "rows": len(frame),
        "tickers": int(frame["ticker"].nunique()),
        "registered_trials": count_registered_trials(args.trials),
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
