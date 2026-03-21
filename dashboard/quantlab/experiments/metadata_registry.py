from __future__ import annotations

from pathlib import Path


class MetadataRegistry:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def experiment_dir(self, experiment_id: str) -> Path:
        path = self.root / experiment_id
        path.mkdir(parents=True, exist_ok=True)
        return path
