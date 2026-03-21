from __future__ import annotations

from quantlab.portfolio.position import Position


class AccountingEngine:
    def apply_fill(self, position: Position, signed_quantity: float, fill_price: float) -> Position:
        if position.quantity == 0 or position.quantity * signed_quantity > 0:
            new_qty = position.quantity + signed_quantity
            if new_qty == 0:
                position.average_price = 0.0
            else:
                total_cost = position.average_price * position.quantity + fill_price * signed_quantity
                position.average_price = total_cost / new_qty
            position.quantity = new_qty
            return position

        closing_qty = min(abs(position.quantity), abs(signed_quantity))
        pnl = closing_qty * (fill_price - position.average_price)
        if position.quantity < 0:
            pnl *= -1
        position.realized_pnl += pnl
        position.quantity += signed_quantity
        if position.quantity == 0:
            position.average_price = 0.0
        else:
            position.average_price = fill_price
        return position
