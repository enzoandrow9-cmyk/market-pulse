from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quantlab.core.deterministic_runtime import stable_hash
from quantlab.data.asset_metadata import build_asset_metadata
from quantlab.data.corporate_actions import load_corporate_actions
from quantlab.data.index_membership import infer_index_membership
from quantlab.data.loaders import load_ohlcv_history
from quantlab.data.point_in_time_database import PointInTimeDatabase
from quantlab.data.survivorship_handler import apply_survivorship_controls


@dataclass
class LoadedMarketData:
    prices: dict[str, pd.DataFrame]
    pit_db: PointInTimeDatabase
    metadata: dict[str, dict]
    corporate_actions: dict[str, pd.DataFrame]
    index_membership: pd.DataFrame
    dataset_version: str


class MarketDataHandler:
    def load(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
        interval: str = "1d",
    ) -> LoadedMarketData:
        raw_prices = {
            symbol: load_ohlcv_history(symbol, start_date, end_date, interval=interval)
            for symbol in sorted(set(symbols))
        }
        prices = apply_survivorship_controls(raw_prices)
        pit_db = PointInTimeDatabase()
        for symbol, frame in prices.items():
            pit_db.register(symbol, frame)

        metadata = build_asset_metadata(list(prices))
        actions = {
            symbol: load_corporate_actions(symbol, start_date, end_date)
            for symbol in prices
        }
        membership = infer_index_membership(list(prices), start_date, end_date)
        dataset_version = stable_hash(
            {
                "symbols": list(prices),
                "interval": interval,
                "start_date": start_date,
                "end_date": end_date,
                "rows": {symbol: int(len(frame)) for symbol, frame in prices.items()},
            }
        )
        return LoadedMarketData(
            prices=prices,
            pit_db=pit_db,
            metadata=metadata,
            corporate_actions=actions,
            index_membership=membership,
            dataset_version=dataset_version,
        )
