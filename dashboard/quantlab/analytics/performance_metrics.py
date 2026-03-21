from __future__ import annotations

import numpy as np
import pandas as pd


def compute_performance_metrics(equity_curve: pd.Series) -> dict[str, float]:
    if equity_curve.empty:
        return {}
    returns = equity_curve.pct_change().dropna()
    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1.0
    ann_return = (1.0 + total_return) ** (252 / max(len(returns), 1)) - 1.0 if len(returns) else total_return
    vol = returns.std() * np.sqrt(252) if len(returns) else 0.0
    downside = returns[returns < 0].std() * np.sqrt(252) if (returns < 0).any() else 0.0
    sharpe = ann_return / vol if vol else 0.0
    sortino = ann_return / downside if downside else 0.0
    return {
        "total_return": float(total_return),
        "annualized_return": float(ann_return),
        "volatility": float(vol),
        "sharpe_ratio": float(sharpe),
        "sortino_ratio": float(sortino),
    }
