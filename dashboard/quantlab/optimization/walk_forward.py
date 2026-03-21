from __future__ import annotations

import pandas as pd


def walk_forward_splits(index: pd.Index, train_size: int, test_size: int):
    splits = []
    start = 0
    while start + train_size + test_size <= len(index):
        train = index[start : start + train_size]
        test = index[start + train_size : start + train_size + test_size]
        splits.append((train, test))
        start += test_size
    return splits
