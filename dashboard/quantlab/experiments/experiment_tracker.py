from __future__ import annotations

from datetime import datetime, timezone

from quantlab.experiments.metadata_registry import MetadataRegistry
from quantlab.experiments.reproducibility_manager import build_reproducibility_record
from quantlab.experiments.results_database import ResultsDatabase


class ExperimentTracker:
    def __init__(self, root: str) -> None:
        self.registry = MetadataRegistry(root)
        self.database = ResultsDatabase()

    def record(self, config, dataset_version: str, payload: dict) -> dict:
        reproducibility = build_reproducibility_record(config, dataset_version)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        experiment_id = f"{stamp}_{reproducibility['config_hash'][:10]}"
        directory = self.registry.experiment_dir(experiment_id)
        path = directory / "result.json"
        saved_path = self.database.save(
            path,
            {
                "experiment_id": experiment_id,
                "created_at": stamp,
                "reproducibility": reproducibility,
                "payload": payload,
            },
        )
        return {
            "experiment_id": experiment_id,
            "results_path": saved_path,
            "reproducibility": reproducibility,
        }
