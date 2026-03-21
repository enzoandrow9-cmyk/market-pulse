from __future__ import annotations

import pandas as pd


def apply_survivorship_controls(price_frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    cleaned: dict[str, pd.DataFrame] = {}
    for symbol, frame in price_frames.items():
        if frame is None or frame.empty:
            continue
        cleaned[symbol] = frame.sort_index().copy()
    return cleaned
