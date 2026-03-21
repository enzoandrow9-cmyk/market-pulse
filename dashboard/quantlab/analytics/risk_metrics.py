from __future__ import annotations

import numpy as np
import pandas as pd


def compute_risk_metrics(equity_curve: pd.Series, confidence: float = 0.95) -> dict[str, float]:
    if equity_curve.empty:
        return {}
    returns = equity_curve.pct_change().dropna()
    rolling_max = equity_curve.cummax()
    drawdown = equity_curve / rolling_max - 1.0
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0
    annualized_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (252 / max(len(returns), 1)) - 1.0 if len(returns) else 0.0
    calmar = annualized_return / abs(max_drawdown) if max_drawdown else 0.0
    if returns.empty:
        var = es = 0.0
    else:
        var = float(np.quantile(returns, 1 - confidence))
        es = float(returns[returns <= var].mean()) if (returns <= var).any() else var
    return {
        "max_drawdown": max_drawdown,
        "calmar_ratio": float(calmar),
        "value_at_risk": var,
        "expected_shortfall": es,
    }
