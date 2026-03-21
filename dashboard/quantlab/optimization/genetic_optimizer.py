from __future__ import annotations

import random


def genetic_search(space: dict[str, list], objective, population_size: int = 8, generations: int = 5, seed: int = 42):
    rng = random.Random(seed)
    keys = sorted(space)

    def sample_one():
        return {key: rng.choice(space[key]) for key in keys}

    population = [sample_one() for _ in range(population_size)]
    history = []
    best = population[0]
    best_score = objective(best)
    history.append({"params": dict(best), "score": best_score})

    for _ in range(generations):
        scored = sorted(((objective(params), params) for params in population), key=lambda item: item[0], reverse=True)
        elites = [params for _, params in scored[: max(2, population_size // 2)]]
        if scored[0][0] > best_score:
            best_score, best = scored[0]
        history.extend({"params": dict(params), "score": score} for score, params in scored[:2])
        population = elites[:]
        while len(population) < population_size:
            left, right = rng.sample(elites, 2)
            child = {key: rng.choice([left[key], right[key]]) for key in keys}
            mutate_key = rng.choice(keys)
            child[mutate_key] = rng.choice(space[mutate_key])
            population.append(child)
    return {"best_params": best, "best_score": best_score, "results": history}
