from __future__ import annotations


def compute_trade_statistics(trades: list[dict]) -> dict[str, float]:
    if not trades:
        return {"win_rate": 0.0, "profit_factor": 0.0, "average_trade_return": 0.0, "trade_count": 0}
    pnl = [float(trade.get("pnl", 0.0)) for trade in trades]
    wins = [value for value in pnl if value > 0]
    losses = [value for value in pnl if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "win_rate": len(wins) / len(pnl),
        "profit_factor": gross_profit / gross_loss if gross_loss else 0.0,
        "average_trade_return": sum(pnl) / len(pnl),
        "trade_count": len(pnl),
    }
