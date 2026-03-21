from __future__ import annotations

import pandas as pd

from quantlab.strategy.base_strategy import BaseStrategy


class MomentumBreakoutStrategy(BaseStrategy):
    name = "momentum_breakout"

    def generate_signals(self, timestamp: pd.Timestamp, symbol: str, history: pd.DataFrame, portfolio_state: dict) -> list:
        lookback = int(self.parameters.get("lookback", 55))
        exit_window = int(self.parameters.get("exit_window", 20))
        if len(history) < max(lookback, exit_window) + 1:
            return []

        close = history["Close"].iloc[-1]
        breakout = history["High"].shift(1).rolling(lookback).max().iloc[-1]
        exit_level = history["Low"].shift(1).rolling(exit_window).min().iloc[-1]
        direction = 1 if close > breakout else 0
        if close < exit_level:
            direction = 0
        confidence = min(1.0, max(0.0, (close - breakout) / max(close, 1e-9) * 40.0))
        return [self._signal(symbol, timestamp, direction, confidence, f"Momentum breakout over {lookback}-bar high")]
