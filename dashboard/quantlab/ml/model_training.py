from __future__ import annotations

import numpy as np


def train_linear_model(features, target):
    x = np.asarray(features, dtype=float)
    y = np.asarray(target, dtype=float)
    if len(x.shape) == 1:
        x = x.reshape(-1, 1)
    x = np.c_[np.ones(len(x)), x]
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    return {"coefficients": beta.tolist()}
