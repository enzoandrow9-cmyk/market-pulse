from __future__ import annotations

import numpy as np


class AlphaModel:
    def score(self, values: list[float]) -> list[float]:
        if not values:
            return []
        arr = np.asarray(values, dtype=float)
        std = arr.std()
        if std == 0:
            return [0.0 for _ in values]
        z = (arr - arr.mean()) / std
        return z.tolist()
