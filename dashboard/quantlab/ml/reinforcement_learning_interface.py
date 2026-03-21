from __future__ import annotations

from typing import Protocol


class ReinforcementLearningPolicy(Protocol):
    def act(self, state: dict) -> dict:
        ...
