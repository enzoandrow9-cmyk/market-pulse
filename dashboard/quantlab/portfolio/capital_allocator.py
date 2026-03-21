from __future__ import annotations


class CapitalAllocator:
    def allocate(self, strategy_ids: list[str]) -> dict[str, float]:
        ordered = sorted(set(strategy_ids))
        if not ordered:
            return {}
        weight = 1.0 / len(ordered)
        return {strategy_id: weight for strategy_id in ordered}
