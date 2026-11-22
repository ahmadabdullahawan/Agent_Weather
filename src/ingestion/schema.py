"""Explicit column dtypes for both feature groups.

Without this, a column that happens to be all-None on a given run (e.g.
"<metric>_change_1h" on the very first run ever, before any history
exists) gets inferred by pandas/pyarrow as an untyped null column, which
Hopsworks rejects. Casting to an explicit dtype makes the schema stable
regardless of which values happen to be missing on a given run.
"""

import pandas as pd

from src.ingestion.features import ROLLING_WINDOWS_HOURS
from src.ingestion.fuse import METRICS

RAW_SCHEMA = {
    "timestamp": "int64",
    "source": "object",  # "openweather_aqicn" (live) or "open_meteo" (backfill)
    "ow_temperature_c": "float64",
    "ow_humidity_pct": "float64",
    "ow_wind_speed_ms": "float64",
    "ow_wind_deg": "float64",
    "ow_rain_mm_1h": "float64",
    "ow_rain_probability_pct": "float64",
    "ow_uv_index": "float64",
    "ow_pm2_5": "float64",
    "ow_pm10": "float64",
    "ow_co": "float64",
    "ow_no2": "float64",
    "ow_o3": "float64",
    "ow_so2": "float64",
    "ow_nh3": "float64",
    "aqicn_aqi": "float64",
    "aqicn_station_name": "object",
    "aqicn_station_lat": "float64",
    "aqicn_station_lon": "float64",
    "aqicn_observed_at_unix": "float64",
    "om_pm2_5": "float64",
    "om_pm10": "float64",
}

FEATURES_SCHEMA = {
    "timestamp": "int64",
    "hour": "int64",
    "day": "int64",
    "month": "int64",
    "day_of_week": "int64",
    **{metric: "float64" for metric in METRICS},
    **{f"{metric}_is_imputed": "bool" for metric in METRICS},
    **{f"{metric}_change_1h": "float64" for metric in METRICS},
    **{
        f"{metric}_avg_{window}h": "float64"
        for metric in METRICS
        for window in ROLLING_WINDOWS_HOURS
    },
    # The observed value 24h after this row's timestamp, used as the
    # training target. Left as None for the newest 24h (Phase 2).
    **{f"{metric}_target_24h": "float64" for metric in METRICS},
}


def to_dataframe(row: dict, schema: dict) -> pd.DataFrame:
    return to_dataframe_many([row], schema)


def to_dataframe_many(rows: list[dict], schema: dict) -> pd.DataFrame:
    df = pd.DataFrame([{col: row.get(col) for col in schema} for row in rows])
    return df.astype(schema)
