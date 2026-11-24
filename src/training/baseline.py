"""The naive baseline (plan.md Phase 4 task 2): "the value from 24
hours ago" -- i.e. predict the 24h-ahead target with the metric's
current value, since the current value IS the observation from 24
hours before the thing being predicted.
"""

import pandas as pd


def naive_predictions(df: pd.DataFrame, metric: str) -> pd.Series:
    return df[metric]
