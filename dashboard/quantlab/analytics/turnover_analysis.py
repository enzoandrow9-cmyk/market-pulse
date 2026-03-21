from __future__ import annotations

import pandas as pd


def compute_turnover(weight_history: pd.DataFrame) -> dict[str, float]:
    if weight_history.empty:
        return {"average_turnover": 0.0}
    turnover = weight_history.diff().abs().sum(axis=1).dropna()
    return {"average_turnover": float(turnover.mean() if not turnover.empty else 0.0)}
