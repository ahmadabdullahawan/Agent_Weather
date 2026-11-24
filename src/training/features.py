"""Shared tabular feature matrix for the classical-ML and deep-learning
families.

AQI columns are dropped entirely -- not just as a target, but as an
input too. Phase 3's AQI validation hasn't closed (plan.md's Phase 3
status note, reports/aqi_validation.md), so its values shouldn't leak
into other metrics' models until that's settled either.

Missing values are imputed with the TRAIN set's own median, applied
unchanged to validation/test, so no information from later splits
leaks into the imputation.
"""

import numpy as np
import pandas as pd

from src.ingestion.features import ROLLING_WINDOWS_HOURS
from src.training.data import METRICS_FOR_TRAINING

TIME_FEATURE_COLUMNS = ["hour", "day", "month", "day_of_week"]


def feature_columns() -> list[str]:
    cols = list(TIME_FEATURE_COLUMNS)
    for metric in METRICS_FOR_TRAINING:
        cols.append(metric)
        cols.append(f"{metric}_is_imputed")
        cols.append(f"{metric}_change_1h")
        for window in ROLLING_WINDOWS_HOURS:
            cols.append(f"{metric}_avg_{window}h")
    return cols


def build_full_matrix(df: pd.DataFrame, train_end: int) -> np.ndarray:
    """Builds the feature matrix for the WHOLE (chronologically sorted)
    dataframe in one pass, imputing with medians learned only from rows
    before `train_end`. Keeping it as one matrix (rather than building
    train/val/test separately) lets the LSTM's lookback windows see
    real history across split boundaries instead of starting cold at
    the top of validation/test."""
    cols = feature_columns()
    X = df[cols].copy()
    for col in X.columns:
        if X[col].dtype == bool:
            X[col] = X[col].astype(float)
    medians = X.iloc[:train_end].median(numeric_only=True)
    X = X.fillna(medians)
    return X.to_numpy(dtype=float)
