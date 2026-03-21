from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf


REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def load_ohlcv_history(
    symbol: str,
    start_date: str,
    end_date: str,
    interval: str = "1d",
    auto_adjust: bool = True,
) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start_date, end=end_date, interval=interval, auto_adjust=auto_adjust)
    if df is None or df.empty:
        raise ValueError(f"No price history returned for {symbol}")

    frame = df.copy()
    frame.index = pd.to_datetime(frame.index).tz_localize(None)
    frame = frame.sort_index()
    missing = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"{symbol} missing required columns: {missing}")

    frame = frame[REQUIRED_COLUMNS].astype(float)
    frame["Return"] = frame["Close"].pct_change().fillna(0.0)
    frame["DollarVolume"] = frame["Close"] * frame["Volume"]
    frame["ADV20"] = frame["Volume"].rolling(20, min_periods=1).mean()
    frame["ADV20_DOLLARS"] = frame["DollarVolume"].rolling(20, min_periods=1).mean()
    frame.index.name = "Timestamp"
    return frame


def load_asset_info(symbol: str) -> dict[str, Any]:
    info = {}
    try:
        raw = yf.Ticker(symbol).info or {}
    except Exception:
        raw = {}

    keys = [
        "longName",
        "shortName",
        "sector",
        "industry",
        "marketCap",
        "averageVolume",
        "beta",
        "currency",
        "quoteType",
        "country",
    ]
    for key in keys:
        if key in raw:
            info[key] = raw[key]
    info["symbol"] = symbol
    return info
