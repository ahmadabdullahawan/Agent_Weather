"""Hourly ingestion entry point.

Fetches current OpenWeather + AQICN data for Islamabad, fuses them into
one row, fills any gaps from the last known value, computes time/change/
rolling features, and stores raw observations and features as separate
rows in the Hopsworks Feature Store.

Run with (from the project root):
    uv run python -m src.ingestion.run
"""

import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from config.location import LAT, LON, TIMEZONE
from src.ingestion import hopsworks_io
from src.ingestion.features import build_features
from src.ingestion.fuse import combine, fill_gaps
from src.ingestion.openmeteo import fetch_current_aqi
from src.ingestion.schema import FEATURES_SCHEMA, RAW_SCHEMA, to_dataframe
from src.ingestion.sources import fetch_aqicn, fetch_openweather

AQICN_RAW_PLACEHOLDER = {
    "aqicn_aqi": None,
    "aqicn_station_name": None,
    "aqicn_station_lat": None,
    "aqicn_station_lon": None,
    "aqicn_observed_at_unix": None,
}
OPENMETEO_RAW_PLACEHOLDER = {"om_pm2_5": None, "om_pm10": None}


def floor_to_hour(dt: datetime) -> int:
    return int(dt.replace(minute=0, second=0, microsecond=0).timestamp())


def run(api_keys: dict | None = None) -> None:
    keys = api_keys or {
        "openweather": os.environ["OPENWEATHER_API_KEY"],
        "aqicn": os.environ["AQICN_TOKEN"],
    }

    now = datetime.now(timezone.utc)
    timestamp_unix = floor_to_hour(now)

    try:
        ow = fetch_openweather(LAT, LON, keys["openweather"])
    except Exception as e:
        print(f"WARNING: OpenWeather fetch failed ({e}); metrics will be gap-filled.", file=sys.stderr)
        ow = {}

    try:
        aqicn = fetch_aqicn(LAT, LON, keys["aqicn"])
    except Exception as e:
        print(f"WARNING: AQICN fetch failed ({e}); stored for reference only, not used for AQI.", file=sys.stderr)
        aqicn = None

    try:
        openmeteo_live = fetch_current_aqi(LAT, LON)
    except Exception as e:
        print(f"WARNING: Open-Meteo live AQI fetch failed ({e}); falling back to OpenWeather-derived AQI.", file=sys.stderr)
        openmeteo_live = None

    fused = combine(ow, aqicn, LAT, LON, now_utc=now, openmeteo_live=openmeteo_live)

    fs = hopsworks_io.connect()
    raw_fg = hopsworks_io.get_raw_fg(fs)
    features_fg = hopsworks_io.get_features_fg(fs)

    history = hopsworks_io.read_recent_features(features_fg, since_unix=timestamp_unix - 25 * 3600)
    last_known = history[-1] if history else None

    filled = fill_gaps(fused, last_known, timestamp_unix)
    filled["timestamp"] = timestamp_unix

    feature_row = build_features(filled, history, TIMEZONE)

    raw_row = {
        **AQICN_RAW_PLACEHOLDER,
        **OPENMETEO_RAW_PLACEHOLDER,
        **ow,
        **(aqicn or {}),
        **({"om_pm2_5": openmeteo_live["om_pm2_5"], "om_pm10": openmeteo_live["om_pm10"]} if openmeteo_live else {}),
        "timestamp": timestamp_unix,
        "source": "openweather_aqicn",
    }

    raw_fg.insert(to_dataframe(raw_row, RAW_SCHEMA), write_options={"wait_for_job": True})
    features_fg.insert(to_dataframe(feature_row, FEATURES_SCHEMA), write_options={"wait_for_job": True})

    print(f"Ingested Islamabad data for {datetime.fromtimestamp(timestamp_unix, tz=timezone.utc)} UTC")
    print(f"AQI={feature_row.get('aqi')} Temp={feature_row.get('temperature_c')}C")


if __name__ == "__main__":
    load_dotenv()
    run()
