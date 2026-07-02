"""Robintrack loader: hourly-ish Robinhood holder counts per ticker, 2018-05-02 .. 2020-08-13
(public archive; used ONLY for the calibration/behavior-fidelity track, never as an
OOS alpha source -- that era is inside every candidate model's training data).

Convention (following Welch 2022): one observation per ticker-day = last UTC record of the day.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_ticker_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["timestamp"])
    if not {"timestamp", "users_holding"}.issubset(df.columns):
        raise ValueError(f"{path.name}: expected columns timestamp, users_holding")
    df = df.sort_values("timestamp")
    daily = (df.set_index("timestamp")
               .resample("1D").last()
               .dropna(subset=["users_holding"]))
    daily["users_holding"] = daily["users_holding"].astype(int)
    daily["d_holders"] = daily["users_holding"].diff()
    return daily.reset_index()
