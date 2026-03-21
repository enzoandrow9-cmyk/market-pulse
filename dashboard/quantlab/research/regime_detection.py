from __future__ import annotations

import pandas as pd


def detect_market_regime(frame: pd.DataFrame) -> dict[str, float | str]:
    if frame.empty or len(frame) < 30:
        return {"regime": "unknown", "trend_score": 0.0, "volatility_score": 0.0}
    close = frame["Close"]
    trend = close.rolling(20).mean().iloc[-1] - close.rolling(60).mean().iloc[-1]
    vol = close.pct_change().rolling(20).std().iloc[-1]
    if trend > 0 and vol < close.pct_change().rolling(60).std().median():
        regime = "trending"
    elif trend < 0 and vol > close.pct_change().rolling(60).std().median():
        regime = "high_volatility"
    elif abs(trend) < close.iloc[-1] * 0.01:
        regime = "mean_reverting"
    else:
        regime = "low_volatility"
    return {
        "regime": regime,
        "trend_score": float(trend),
        "volatility_score": float(vol if pd.notna(vol) else 0.0),
    }
