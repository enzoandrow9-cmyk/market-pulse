from __future__ import annotations

import pandas as pd
import yfinance as yf


def load_corporate_actions(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    try:
        actions = yf.Ticker(symbol).actions
    except Exception:
        return pd.DataFrame(columns=["Dividends", "Stock Splits"])

    if actions is None or actions.empty:
        return pd.DataFrame(columns=["Dividends", "Stock Splits"])

    frame = actions.copy()
    frame.index = pd.to_datetime(frame.index).tz_localize(None)
    return frame.loc[(frame.index >= start_date) & (frame.index <= end_date)].copy()
