from __future__ import annotations

import numpy as np
import pandas as pd


def run_stress_tests(equity_curve: pd.Series) -> dict[str, float]:
    returns = equity_curve.pct_change().dropna()
    if returns.empty:
        return {"market_crash": 0.0, "rate_shock": 0.0, "vol_spike": 0.0, "commodity_shock": 0.0}
    return {
        "market_crash": float((1 + returns.mean() - 0.15) * equity_curve.iloc[-1] - equity_curve.iloc[-1]),
        "rate_shock": float((1 + returns.mean() - 0.03) * equity_curve.iloc[-1] - equity_curve.iloc[-1]),
        "vol_spike": float((1 + returns.mean() - 2 * returns.std()) * equity_curve.iloc[-1] - equity_curve.iloc[-1]),
        "commodity_shock": float((1 + returns.mean() - 0.07) * equity_curve.iloc[-1] - equity_curve.iloc[-1]),
    }
