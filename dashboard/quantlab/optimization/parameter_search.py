from __future__ import annotations

import itertools
import random


def grid_search(space: dict[str, list], objective):
    keys = sorted(space)
    best_score = None
    best_params = None
    results = []
    for values in itertools.product(*(space[key] for key in keys)):
        params = dict(zip(keys, values))
        score = objective(params)
        results.append({"params": params, "score": score})
        if best_score is None or score > best_score:
            best_score = score
            best_params = params
    return {"best_params": best_params or {}, "best_score": best_score or 0.0, "results": results}


def random_search(space: dict[str, list], objective, iterations: int = 25, seed: int = 42):
    rng = random.Random(seed)
    keys = sorted(space)
    seen = set()
    results = []
    best_score = None
    best_params = None
    while len(results) < iterations:
        params = {key: rng.choice(space[key]) for key in keys}
        frozen = tuple((key, params[key]) for key in keys)
        if frozen in seen:
            continue
        seen.add(frozen)
        score = objective(params)
        results.append({"params": params, "score": score})
        if best_score is None or score > best_score:
            best_score = score
            best_params = params
        if len(seen) >= len(list(itertools.product(*(space[key] for key in keys)))):
            break
    return {"best_params": best_params or {}, "best_score": best_score or 0.0, "results": results}
