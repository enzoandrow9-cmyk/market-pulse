from __future__ import annotations

import pandas as pd


def combine_alphas(factor_frame: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.Series:
    if factor_frame.empty:
        return pd.Series(dtype=float)
    weights = weights or {column: 1.0 / len(factor_frame.columns) for column in factor_frame.columns}
    combined = pd.Series(0.0, index=factor_frame.index)
    for column, weight in weights.items():
        if column not in factor_frame:
            continue
        z = (factor_frame[column] - factor_frame[column].mean()) / (factor_frame[column].std() or 1.0)
        combined = combined + z.fillna(0.0) * weight
    return combined
