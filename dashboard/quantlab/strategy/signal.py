from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StrategySignal:
    strategy_id: str
    symbol: str
    timestamp: str
    direction: int
    target_weight: float
    confidence: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)
