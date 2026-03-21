from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import sys
from datetime import datetime, timezone
from typing import Any

import numpy as np

from quantlab.types import BacktestConfig


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def stable_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(_normalize(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_config_hash(config: BacktestConfig) -> str:
    return stable_hash(
        {
            "symbols": sorted(config.symbols),
            "strategies": list(config.strategies),
            "start_date": config.start_date,
            "end_date": config.end_date,
            "interval": config.interval,
            "simulation_mode": config.simulation_mode,
            "initial_capital": config.initial_capital,
            "benchmark": config.benchmark,
            "commission_bps": config.commission_bps,
            "slippage_bps": config.slippage_bps,
            "market_impact_coefficient": config.market_impact_coefficient,
            "max_adv_percent": config.max_adv_percent,
            "latency_bars": config.latency_bars,
            "max_position_weight": config.max_position_weight,
            "max_gross_leverage": config.max_gross_leverage,
            "max_drawdown": config.max_drawdown,
            "seed": config.seed,
            "parameters": config.parameters,
            "metadata": config.metadata,
        }
    )


def seed_everything(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)


def runtime_snapshot() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
