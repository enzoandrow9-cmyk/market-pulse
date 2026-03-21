from __future__ import annotations

import pandas as pd


def attribute_performance(symbol_returns: pd.DataFrame, weight_history: pd.DataFrame) -> dict[str, float]:
    if symbol_returns.empty or weight_history.empty:
        return {}
    aligned_weights = weight_history.reindex(symbol_returns.index).ffill().fillna(0.0)
    contrib = (aligned_weights.shift(1).fillna(0.0) * symbol_returns).sum()
    return {symbol: float(value) for symbol, value in contrib.to_dict().items()}
