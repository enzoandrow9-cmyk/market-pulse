from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from quantlab.data.point_in_time_database import PointInTimeDatabase


@dataclass
class MarketEnvironment:
    pit_db: PointInTimeDatabase
    latest_bars: dict[str, pd.Series] = field(default_factory=dict)

    def update(self, symbol: str, timestamp: pd.Timestamp) -> pd.Series | None:
        bar = self.pit_db.bar_at(symbol, timestamp)
        if bar is not None:
            self.latest_bars[symbol] = bar
        return bar

    def price_map(self) -> dict[str, float]:
        return {symbol: float(bar["Close"]) for symbol, bar in self.latest_bars.items()}
