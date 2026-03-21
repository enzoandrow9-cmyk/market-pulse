from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BacktestConfig:
    symbols: list[str]
    strategies: list[str]
    start_date: str
    end_date: str
    interval: str = "1d"
    simulation_mode: str = "event"
    initial_capital: float = 1_000_000.0
    benchmark: str = "SPY"
    commission_bps: float = 1.0
    slippage_bps: float = 2.0
    market_impact_coefficient: float = 0.1
    max_adv_percent: float = 0.05
    latency_bars: int = 0
    max_position_weight: float = 0.15
    max_gross_leverage: float = 1.5
    max_drawdown: float = 0.2
    seed: int = 42
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def strategy_parameters(self, strategy_name: str) -> dict[str, Any]:
        raw = self.parameters.get(strategy_name, {})
        return raw if isinstance(raw, dict) else {}


@dataclass(frozen=True)
class BarSnapshot:
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    average_daily_volume: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeRecord:
    symbol: str
    side: str
    quantity: float
    fill_price: float
    timestamp: str
    fees: float = 0.0
    slippage_cost: float = 0.0
    market_impact_cost: float = 0.0
    strategy_id: str = "portfolio"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentRecord:
    experiment_id: str
    config_hash: str
    created_at: str
    dataset_version: str
    runtime: dict[str, Any]
    results_path: str
    metadata: dict[str, Any] = field(default_factory=dict)
