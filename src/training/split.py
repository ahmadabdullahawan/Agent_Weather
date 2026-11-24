"""Time-based train/validation/test split (plan.md Phase 4 task 1).

Never shuffled -- split purely on chronological order, since shuffling
would let the model train on hours that come after the ones it's
validated or tested on.
"""

import pandas as pd

TRAIN_FRACTION = 0.70
VAL_FRACTION = 0.15
# Test gets the remainder (~0.15).


def split_bounds(n: int) -> tuple[int, int]:
    """Row-position boundaries (train_end, val_end) for a dataframe of
    length n, sorted oldest-first. Exposed separately from
    time_based_split() so callers that need lookback context across a
    split boundary (e.g. the LSTM) can build one continuous matrix and
    slice it by these same positions."""
    train_end = int(n * TRAIN_FRACTION)
    val_end = train_end + int(n * VAL_FRACTION)
    return train_end, val_end


def time_based_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = df.sort_values("timestamp").reset_index(drop=True)
    train_end, val_end = split_bounds(len(df))
    return df.iloc[:train_end], df.iloc[train_end:val_end], df.iloc[val_end:]
