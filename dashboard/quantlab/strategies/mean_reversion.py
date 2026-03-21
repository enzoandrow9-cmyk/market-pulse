from __future__ import annotations

import pandas as pd

from quantlab.strategy.base_strategy import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    name = "mean_reversion"

    def generate_signals(self, timestamp: pd.Timestamp, symbol: str, history: pd.DataFrame, portfolio_state: dict) -> list:
        lookback = int(self.parameters.get("lookback", 20))
        entry_z = float(self.parameters.get("entry_z", 1.5))
        exit_z = float(self.parameters.get("exit_z", 0.5))
        if len(history) < lookback:
            return []

        close = history["Close"]
        mean = close.rolling(lookback).mean().iloc[-1]
        std = close.rolling(lookback).std().iloc[-1]
        if not std or pd.isna(std):
            return []

        zscore = (close.iloc[-1] - mean) / std
        if zscore <= -entry_z:
            direction = 1
        elif zscore >= entry_z:
            direction = -1
        elif abs(zscore) <= exit_z:
            direction = 0
        else:
            direction = 0
        confidence = min(1.0, abs(zscore) / max(entry_z, 1e-9))
        return [self._signal(symbol, timestamp, direction, confidence, f"Mean reversion z-score {zscore:.2f}")]
