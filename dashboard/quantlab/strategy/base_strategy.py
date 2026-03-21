from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from quantlab.strategy.position_sizer import PositionSizer
from quantlab.strategy.signal import StrategySignal


class BaseStrategy(ABC):
    name = "base_strategy"

    def __init__(self, strategy_id: str, parameters: dict[str, Any] | None = None, max_position_weight: float = 0.15) -> None:
        self.strategy_id = strategy_id
        self.parameters = parameters or {}
        self.sizer = PositionSizer(max_position_weight=max_position_weight)

    @abstractmethod
    def generate_signals(
        self,
        timestamp: pd.Timestamp,
        symbol: str,
        history: pd.DataFrame,
        portfolio_state: dict[str, Any],
    ) -> list[StrategySignal]:
        raise NotImplementedError

    def vectorized_weights(self, history: pd.DataFrame) -> pd.Series:
        weights = []
        for timestamp in history.index:
            hist = history.loc[history.index <= timestamp]
            signals = self.generate_signals(timestamp, "", hist, {})
            if not signals:
                weights.append(0.0)
            else:
                weights.append(signals[-1].target_weight)
        return pd.Series(weights, index=history.index, name=f"{self.strategy_id}_weight")

    def _signal(
        self,
        symbol: str,
        timestamp: pd.Timestamp,
        direction: int,
        confidence: float,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> StrategySignal:
        target_weight = self.sizer.size_from_signal(direction=direction, confidence=confidence)
        return StrategySignal(
            strategy_id=self.strategy_id,
            symbol=symbol,
            timestamp=timestamp.isoformat(),
            direction=direction,
            target_weight=target_weight,
            confidence=confidence,
            reason=reason,
            metadata=metadata or {},
        )
