from __future__ import annotations

import numpy as np
import pandas as pd


def compute_time_series_factors(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    factors = pd.DataFrame(index=frame.index)
    factors["momentum_20"] = frame["Close"].pct_change(20)
    factors["momentum_60"] = frame["Close"].pct_change(60)
    factors["mean_reversion_5"] = -frame["Close"].pct_change(5)
    factors["low_volatility"] = -frame["Close"].pct_change().rolling(20).std()
    factors["volume_trend"] = frame["Volume"].pct_change(20).replace([np.inf, -np.inf], np.nan)
    return factors.fillna(0.0)


def compute_cross_sectional_scores(price_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for symbol, frame in price_frames.items():
        if frame.empty:
            continue
        latest = frame.iloc[-1]
        rows.append(
            {
                "symbol": symbol,
                "momentum": frame["Close"].pct_change(60).iloc[-1] if len(frame) > 60 else 0.0,
                "size": latest.get("DollarVolume", 0.0),
                "quality": frame["Return"].rolling(60).mean().iloc[-1] if len(frame) > 60 else 0.0,
                "low_volatility": -frame["Return"].rolling(20).std().iloc[-1] if len(frame) > 20 else 0.0,
                "value": -frame["Close"].pct_change(252).iloc[-1] if len(frame) > 252 else 0.0,
            }
        )
    scored = pd.DataFrame(rows)
    if scored.empty:
        return scored
    for col in ["momentum", "size", "quality", "low_volatility", "value"]:
        ranked = scored[col].rank(pct=True)
        scored[f"{col}_rank"] = ranked
    return scored.sort_values("momentum_rank", ascending=False)
