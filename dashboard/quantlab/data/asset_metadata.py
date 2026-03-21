from __future__ import annotations

from quantlab.data.loaders import load_asset_info


def build_asset_metadata(symbols: list[str]) -> dict[str, dict]:
    return {symbol: load_asset_info(symbol) for symbol in sorted(set(symbols))}
