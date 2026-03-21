from __future__ import annotations

from quantlab.research.feature_pipeline import build_feature_matrix


def engineer_features(frame):
    return build_feature_matrix(frame)
