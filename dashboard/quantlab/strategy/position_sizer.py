from __future__ import annotations


class PositionSizer:
    def __init__(self, max_position_weight: float = 0.15) -> None:
        self.max_position_weight = float(max_position_weight)

    def size_from_signal(self, direction: int, confidence: float) -> float:
        bounded_confidence = max(0.0, min(1.0, confidence))
        return float(direction) * self.max_position_weight * bounded_confidence
