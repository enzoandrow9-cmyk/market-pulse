from __future__ import annotations

import pandas as pd

from quantlab.strategy.base_strategy import BaseStrategy


class SMACrossoverStrategy(BaseStrategy):
    name = "sma_crossover"

    def generate_signals(self, timestamp: pd.Timestamp, symbol: str, history: pd.DataFrame, portfolio_state: dict) -> list:
        short_window = int(self.parameters.get("short_window", 20))
        long_window = int(self.parameters.get("long_window", 50))
        allow_short = bool(self.parameters.get("allow_short", False))
        if len(history) < long_window:
            return []

        close = history["Close"]
        fast = close.rolling(short_window).mean().iloc[-1]
        slow = close.rolling(long_window).mean().iloc[-1]
        direction = 1 if fast > slow else (-1 if allow_short and fast < slow else 0)
        confidence = min(1.0, abs(fast - slow) / max(close.iloc[-1], 1e-9) * 50.0)
        return [self._signal(symbol, timestamp, direction, confidence, f"SMA {short_window}/{long_window} crossover")]
