from __future__ import annotations

from quantlab.risk.portfolio_limits import PortfolioLimits


class RiskEngine:
    def __init__(self, limits: PortfolioLimits) -> None:
        self.limits = limits
        self.high_water_mark: float | None = None
        self.is_halted = False

    def update_drawdown(self, equity: float) -> float:
        if self.high_water_mark is None:
            self.high_water_mark = equity
        self.high_water_mark = max(self.high_water_mark, equity)
        drawdown = 0.0 if not self.high_water_mark else 1.0 - equity / self.high_water_mark
        if drawdown >= self.limits.max_drawdown:
            self.is_halted = True
        return drawdown

    def validate_target_weight(self, target_weight: float, gross_exposure: float, current_equity: float) -> tuple[bool, str]:
        if self.is_halted:
            return False, "risk_halt_active"
        if abs(target_weight) > self.limits.max_position_weight:
            return False, "position_limit_breached"
        if gross_exposure > self.limits.max_gross_leverage:
            return False, "gross_leverage_breached"
        if current_equity <= 0:
            return False, "equity_depleted"
        return True, "pass"
