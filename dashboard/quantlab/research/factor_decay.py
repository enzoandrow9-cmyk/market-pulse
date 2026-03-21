from __future__ import annotations

import pandas as pd


def compute_factor_decay(factors: pd.DataFrame, close: pd.Series, horizons: list[int] | None = None) -> dict[str, float]:
    if horizons is None:
        horizons = [1, 5, 10, 20]
    if factors.empty or close.empty:
        return {str(h): 0.0 for h in horizons}
    base = factors.iloc[:, 0]
    decay = {}
    for horizon in horizons:
        forward = close.pct_change(horizon).shift(-horizon)
        decay[str(horizon)] = float(base.corr(forward))
    return decay
