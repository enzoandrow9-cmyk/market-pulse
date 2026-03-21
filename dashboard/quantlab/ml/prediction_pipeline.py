from __future__ import annotations

import numpy as np


def predict_linear_model(model, features):
    x = np.asarray(features, dtype=float)
    if len(x.shape) == 1:
        x = x.reshape(-1, 1)
    x = np.c_[np.ones(len(x)), x]
    beta = np.asarray(model["coefficients"], dtype=float)
    return x @ beta
