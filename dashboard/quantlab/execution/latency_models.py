from __future__ import annotations


class LatencyModel:
    def __init__(self, latency_bars: int = 0) -> None:
        self.latency_bars = max(0, int(latency_bars))
