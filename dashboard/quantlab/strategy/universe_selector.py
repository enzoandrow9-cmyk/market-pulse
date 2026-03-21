from __future__ import annotations


class UniverseSelector:
    def select(self, symbols: list[str]) -> list[str]:
        return sorted(set(symbols))
