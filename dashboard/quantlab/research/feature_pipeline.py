from __future__ import annotations

import pandas as pd

from quantlab.research.factor_library import compute_time_series_factors


def build_feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    factors = compute_time_series_factors(frame)
    features = frame[["Close", "Volume", "Return"]].copy()
    return features.join(factors, how="left").fillna(0.0)
