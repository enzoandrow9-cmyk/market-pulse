from __future__ import annotations

from quantlab.core.deterministic_runtime import build_config_hash, runtime_snapshot


def build_reproducibility_record(config, dataset_version: str) -> dict:
    return {
        "config_hash": build_config_hash(config),
        "dataset_version": dataset_version,
        "runtime": runtime_snapshot(),
        "seed": config.seed,
    }
