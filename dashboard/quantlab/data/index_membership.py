from __future__ import annotations

import pandas as pd


def infer_index_membership(symbols: list[str], start_date: str, end_date: str) -> pd.DataFrame:
    if not symbols:
        return pd.DataFrame(columns=["symbol", "start_date", "end_date", "index"])
    rows = [
        {"symbol": symbol, "start_date": start_date, "end_date": end_date, "index": "USER_UNIVERSE"}
        for symbol in sorted(set(symbols))
    ]
    return pd.DataFrame(rows)
