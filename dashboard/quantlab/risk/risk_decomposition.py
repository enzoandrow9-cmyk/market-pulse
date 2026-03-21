from __future__ import annotations

import numpy as np
import pandas as pd


def decompose_risk(returns: pd.DataFrame, weights: dict[str, float]) -> dict[str, float]:
    if returns.empty or not weights:
        return {}
    cov = returns.cov()
    total_var = 0.0
    contrib = {}
    for symbol, weight in weights.items():
        if symbol not in cov.index:
            continue
        marginal = float(sum(cov.loc[symbol, other] * weights.get(other, 0.0) for other in cov.columns))
        rc = weight * marginal
        contrib[symbol] = rc
        total_var += rc
    if total_var == 0:
        return {symbol: 0.0 for symbol in contrib}
    return {symbol: value / total_var for symbol, value in contrib.items()}
