from __future__ import annotations

import pandas as pd


def compute_factor_exposure(strategy_returns: pd.Series, factor_scores: pd.DataFrame) -> dict[str, float]:
    if strategy_returns.empty or factor_scores.empty:
        return {}
    exposures = {}
    aligned = factor_scores.reindex(strategy_returns.index).fillna(0.0)
    for column in aligned.columns:
        exposures[column] = float(strategy_returns.corr(aligned[column]))
    return exposures
