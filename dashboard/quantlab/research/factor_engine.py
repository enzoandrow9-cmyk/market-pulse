from __future__ import annotations

import pandas as pd

from quantlab.research.factor_library import compute_cross_sectional_scores, compute_time_series_factors


class FactorEngine:
    def evaluate(self, price_frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        time_series = {symbol: compute_time_series_factors(frame) for symbol, frame in price_frames.items()}
        ranking = compute_cross_sectional_scores(price_frames)
        return {"time_series": time_series, "ranking": ranking}
