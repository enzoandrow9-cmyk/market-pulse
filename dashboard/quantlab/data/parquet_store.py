from __future__ import annotations

from pathlib import Path

import pandas as pd


class ParquetStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, symbol: str, interval: str) -> Path:
        return self.root / f"{symbol}_{interval}.parquet"

    def save(self, symbol: str, interval: str, frame: pd.DataFrame) -> Path:
        path = self.path_for(symbol, interval)
        try:
            frame.to_parquet(path)
        except Exception:
            frame.to_csv(path.with_suffix(".csv"))
            return path.with_suffix(".csv")
        return path

    def load(self, symbol: str, interval: str) -> pd.DataFrame | None:
        path = self.path_for(symbol, interval)
        if path.exists():
            return pd.read_parquet(path)
        csv_path = path.with_suffix(".csv")
        if csv_path.exists():
            frame = pd.read_csv(csv_path, index_col=0, parse_dates=True)
            frame.index.name = "Timestamp"
            return frame
        return None
