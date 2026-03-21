from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioLimits:
    max_position_weight: float = 0.15
    max_gross_leverage: float = 1.5
    max_drawdown: float = 0.2
