from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OrderRequest:
    strategy_id: str
    symbol: str
    timestamp: str
    quantity: float
    side: str
    order_type: str = "market"
    reference_price: float = 0.0
    limit_price: float | None = None
    stop_price: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
