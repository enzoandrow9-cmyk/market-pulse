from __future__ import annotations

import random

import numpy as np


def bootstrap_trade_sequences(trade_pnl: list[float], iterations: int = 500, seed: int = 42) -> dict[str, float]:
    if not trade_pnl:
        return {"risk_of_ruin": 0.0, "worst_drawdown": 0.0, "median_terminal_pnl": 0.0}
    rng = random.Random(seed)
    paths = []
    for _ in range(iterations):
        sample = [rng.choice(trade_pnl) for _ in range(len(trade_pnl))]
        cumulative = np.cumsum(sample)
        peak = np.maximum.accumulate(cumulative)
        drawdown = np.min(cumulative - peak)
        paths.append((float(cumulative[-1]), float(drawdown)))
    terminal = [value for value, _ in paths]
    drawdowns = [value for _, value in paths]
    return {
        "risk_of_ruin": float(sum(value < 0 for value in terminal) / len(terminal)),
        "worst_drawdown": float(min(drawdowns)),
        "median_terminal_pnl": float(np.median(terminal)),
    }
