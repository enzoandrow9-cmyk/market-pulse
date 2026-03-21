from __future__ import annotations

import pandas as pd


class SimulationClock:
    def __init__(self, timeline: list[pd.Timestamp]) -> None:
        self.timeline = list(timeline)

    def __iter__(self):
        return iter(self.timeline)
