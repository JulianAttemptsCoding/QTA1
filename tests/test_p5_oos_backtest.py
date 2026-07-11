import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p5_oos_backtest.py"
SPEC = importlib.util.spec_from_file_location("p5_oos_backtest", SCRIPT)
backtest = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = backtest
SPEC.loader.exec_module(backtest)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_daily_returns_apply_cost_and_equity(tmp_path):
    rows = []
    for ticker in ["AAA", "BBB"]:
        for idx, day in enumerate(["2025-01-02", "2025-01-03", "2025-01-06"]):
            rows.append({
                "run_id": f"oos-2025-g1-{ticker.lower()}-alias-v1",
                "ticker": ticker,
                "arm": "alias",
                "day": day,
                "real_close": 10.0 + idx,
                "auction_price": 11.0 + idx,
                "flow_imbalance": 1.0,
                "flow_imbalance_unweighted": 1.0,
                "momentum_1d": 1.0,
                "next_day_return": 0.01,
            })
    write_jsonl(tmp_path / "runs" / "p4" / "main" / "oos-2025-g1-aaa-alias-v1" / "sim.jsonl", rows[:3])
    write_jsonl(tmp_path / "runs" / "p4" / "main" / "oos-2025-g1-bbb-alias-v1" / "sim.jsonl", rows[3:])

    frame = backtest.load_oos_frame(tmp_path / "runs")
    daily = backtest.strategy_daily_returns(frame, cost_bps=25)
    flow = daily[daily["strategy"] == "flow_weighted"].sort_values("day")

    assert len(flow) == 3
    assert round(float(flow.iloc[0]["daily_return"]), 4) == 0.0075
    assert float(flow.iloc[-1]["equity"]) > 1.0


def test_run_backtest_writes_csv_and_svg(tmp_path):
    rows = []
    for idx, day in enumerate(["2025-01-02", "2025-01-03", "2025-01-06"]):
        rows.append({
            "run_id": "oos-2025-g1-tlry-alias-v1",
            "ticker": "TLRY",
            "arm": "alias",
            "day": day,
            "real_close": [10.0, 11.0, 12.0][idx],
            "auction_price": [11.0, 12.0, 13.0][idx],
            "flow_imbalance": 1.0,
            "flow_imbalance_unweighted": 1.0,
            "momentum_1d": 1.0,
            "next_day_return": 0.01,
        })
    write_jsonl(tmp_path / "runs" / "p4" / "main" / "one" / "sim.jsonl", rows)

    summaries, figures, daily = backtest.run_backtest(
        tmp_path / "runs",
        tmp_path / "figures",
        tmp_path / "returns.csv",
        cost_bps=25,
    )

    assert summaries
    assert figures and figures[0].exists()
    assert (tmp_path / "returns.csv").exists()
    assert not daily.empty
