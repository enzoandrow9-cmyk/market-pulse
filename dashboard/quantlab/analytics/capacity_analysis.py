from __future__ import annotations

import pandas as pd


def estimate_capacity(price_frames: dict[str, pd.DataFrame], max_adv_percent: float) -> dict[str, float]:
    capacity = {}
    for symbol, frame in price_frames.items():
        if frame.empty:
            capacity[symbol] = 0.0
            continue
        adv_dollars = frame["ADV20_DOLLARS"].iloc[-1] if "ADV20_DOLLARS" in frame.columns else (frame["Close"] * frame["Volume"]).rolling(20).mean().iloc[-1]
        capacity[symbol] = float(adv_dollars * max_adv_percent)
    return capacity
