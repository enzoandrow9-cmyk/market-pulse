from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ResultsDatabase:
    def save(self, path: str | Path, payload: dict[str, Any]) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return str(path)
