from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.strategy.base_strategy import BaseStrategy


class VolatilityTargetingStrategy(BaseStrategy):
    name = "volatility_targeting"

    def generate_signals(self, timestamp: pd.Timestamp, symbol: str, history: pd.DataFrame, portfolio_state: dict) -> list:
        vol_window = int(self.parameters.get("vol_window", 20))
        trend_window = int(self.parameters.get("trend_window", 50))
        target_vol = float(self.parameters.get("target_vol", 0.15))
        if len(history) < max(vol_window, trend_window) + 2:
            return []

        returns = history["Close"].pct_change().dropna()
        realized_vol = returns.tail(vol_window).std() * np.sqrt(252)
        trend = history["Close"].rolling(trend_window).mean().iloc[-1]
        direction = 1 if history["Close"].iloc[-1] >= trend else 0
        confidence = 0.0 if realized_vol <= 0 else min(1.0, target_vol / realized_vol)
        return [self._signal(symbol, timestamp, direction, confidence, f"Vol-targeted trend following ({realized_vol:.2%} vol)")]
