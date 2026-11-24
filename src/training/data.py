"""Loads engineered features from Hopsworks and builds the 24h-ahead
target for each metric.

Targets are recomputed here by self-joining each row against the row
24h later, rather than trusting any stored "<metric>_target_24h" column:
only backfilled rows get that column filled in (see
src/ingestion/backfill.py::add_targets) -- live-ingested rows never get
it backfilled once 24h passes, since nothing re-visits them. Recomputing
from the raw metric values works uniformly for both.
"""

import pandas as pd

from src.ingestion import hopsworks_io
from src.ingestion.fuse import METRICS

DAY_SECONDS = 24 * 3600

# AQI is excluded from training until Phase 3's AQI validation fully
# closes -- see plan.md's Phase 3 status note and reports/aqi_validation.md.
# Add "aqi" back to this list once that check is re-run with a larger
# sample and confirms the live/archive values agree closely.
METRICS_FOR_TRAINING = [m for m in METRICS if m != "aqi"]


def load_features() -> pd.DataFrame:
    fs = hopsworks_io.connect()
    fg = hopsworks_io.get_features_fg(fs)
    return fg.read().sort_values("timestamp").reset_index(drop=True)


def add_targets(df: pd.DataFrame, metrics: list[str] = METRICS_FOR_TRAINING) -> pd.DataFrame:
    """Adds "<metric>_target_24h" = that metric's own value at
    timestamp + 24h. Rows with no row at +24h yet (the newest 24 hours)
    get NaN -- by design, per Phase 2: those hours are forecast-only."""
    df = df.copy()
    future_ts = df["timestamp"] + DAY_SECONDS
    for metric in metrics:
        by_ts = df.set_index("timestamp")[metric]
        df[f"{metric}_target_24h"] = future_ts.map(by_ts)
    return df


# Below this many real (non-imputed-from-nothing) training observations,
# a metric has no meaningful history to fit any model on -- this is
# exactly the known gap documented in the README: Open-Meteo's archive
# has no `uv_index` or `rain_probability_pct` history at all, so those
# two are ~100% missing until enough live-ingested hours accumulate.
MIN_TRAIN_OBSERVATIONS = 100


def trainable_metrics(train: pd.DataFrame, metrics: list[str] = METRICS_FOR_TRAINING) -> list[str]:
    """Metrics with enough real history in `train` to fit a model at
    all. Callers should skip (not crash on) metrics this excludes."""
    return [m for m in metrics if train[m].notna().sum() >= MIN_TRAIN_OBSERVATIONS]
