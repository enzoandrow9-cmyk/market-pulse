from __future__ import annotations


class ExposureTracker:
    def snapshot(self, positions: dict, price_map: dict[str, float], equity: float) -> dict:
        gross = 0.0
        net = 0.0
        by_symbol = {}
        for symbol, position in positions.items():
            price = price_map.get(symbol, 0.0)
            value = position.market_value(price)
            gross += abs(value)
            net += value
            by_symbol[symbol] = value / equity if equity else 0.0
        return {
            "gross_exposure": gross / equity if equity else 0.0,
            "net_exposure": net / equity if equity else 0.0,
            "symbol_weights": by_symbol,
        }
