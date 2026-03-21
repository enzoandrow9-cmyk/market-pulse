from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class PointInTimeDatabase:
    frames: dict[str, pd.DataFrame] = field(default_factory=dict)

    def register(self, symbol: str, frame: pd.DataFrame) -> None:
        self.frames[symbol] = frame.sort_index().copy()

    def symbols(self) -> list[str]:
        return sorted(self.frames)

    def bar_at(self, symbol: str, timestamp: pd.Timestamp) -> pd.Series | None:
        frame = self.frames.get(symbol)
        if frame is None or timestamp not in frame.index:
            return None
        return frame.loc[timestamp]

    def history_until(
        self,
        symbol: str,
        timestamp: pd.Timestamp,
        lookback: int | None = None,
    ) -> pd.DataFrame:
        frame = self.frames.get(symbol)
        if frame is None:
            return pd.DataFrame()
        hist = frame.loc[frame.index <= timestamp].copy()
        if lookback is not None:
            hist = hist.tail(lookback)
        return hist

    def timeline(self) -> list[pd.Timestamp]:
        stamps: set[pd.Timestamp] = set()
        for frame in self.frames.values():
            stamps.update(frame.index.tolist())
        return sorted(stamps)
