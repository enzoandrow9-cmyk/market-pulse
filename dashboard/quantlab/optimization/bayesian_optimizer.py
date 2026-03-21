from __future__ import annotations

import random


def bayesian_search(space: dict[str, list], objective, iterations: int = 20, seed: int = 42):
    rng = random.Random(seed)
    keys = sorted(space)
    incumbent = {key: space[key][0] for key in keys}
    best_score = objective(incumbent)
    history = [{"params": dict(incumbent), "score": best_score}]
    for _ in range(max(0, iterations - 1)):
        candidate = {}
        for key in keys:
            values = list(space[key])
            best_index = values.index(incumbent[key]) if incumbent[key] in values else 0
            candidate[key] = values[min(len(values) - 1, max(0, best_index + rng.choice([-1, 0, 1])))]
        score = objective(candidate)
        history.append({"params": candidate, "score": score})
        if score > best_score:
            best_score = score
            incumbent = candidate
    return {"best_params": incumbent, "best_score": best_score, "results": history}
