from __future__ import annotations


class OrderBookSimulator:
    def estimate_spread_bps(self, volume: float) -> float:
        if volume <= 0:
            return 10.0
        if volume < 1_000_000:
            return 4.0
        return 1.0
