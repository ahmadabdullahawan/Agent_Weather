"""Combines the raw sources into one row per hour, and fills gaps.

Fusion rule (documented in README):
  - AQI: Open-Meteo's live `us_aqi` is the primary source — it's the
    same provider/methodology used for the historical backfill, checked
    against ~4,943 backfill hours and found consistent by construction
    (see reports/aqi_validation.md). AQICN is stored for reference but
    never blended in: its nearest active station for Islamabad's
    coordinates is a different city entirely (confirmed live, >150km
    away), so it isn't usable ground truth here. If Open-Meteo's live
    call fails, falls back to an AQI computed from OpenWeather's PM2.5/
    PM10 concentrations (see aqi.py) — this fallback was found to
    disagree with Open-Meteo's own number on raw concentrations (it's a
    simplified instantaneous calculation, not Open-Meteo's exact
    methodology), so it's a last resort, not an equal partner.
  - Temperature, humidity, rain, UV, wind: OpenWeather is the only
    source for these, so its value is used directly.

Gap-fill rule (documented in README): if a metric is missing after
fusion, use the last known value if it is less than 3 hours old;
otherwise leave it empty and flag it with "<metric>_is_imputed".
"""

import math
from datetime import datetime, timezone

from src.ingestion.aqi import compute_aqi

AQICN_MAX_DISTANCE_KM = 50
MAX_STALENESS_HOURS = 3

METRICS = [
    "aqi",
    "temperature_c",
    "rain_mm",
    "rain_probability_pct",
    "humidity_pct",
    "uv_index",
    "wind_speed_ms",
    "wind_deg",
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _resolve_aqi(ow: dict, openmeteo_live: dict | None) -> float:
    if openmeteo_live is not None and openmeteo_live.get("aqi") is not None:
        return openmeteo_live["aqi"]
    return compute_aqi(ow.get("ow_pm2_5"), ow.get("ow_pm10"))


def combine(
    ow: dict,
    aqicn: dict | None,
    target_lat: float,
    target_lon: float,
    now_utc: datetime | None = None,
    openmeteo_live: dict | None = None,
) -> dict:
    """Builds one fused row from the raw source payloads. Values that
    are still missing after fusion are left as None for fill_gaps() to
    handle. `aqicn` is accepted for raw storage/logging only — see the
    module docstring for why it isn't blended into the fused `aqi`."""
    now_utc = now_utc or datetime.now(timezone.utc)

    return {
        "aqi": _resolve_aqi(ow, openmeteo_live),
        "temperature_c": ow.get("ow_temperature_c"),
        "rain_mm": ow.get("ow_rain_mm_1h"),
        "rain_probability_pct": ow.get("ow_rain_probability_pct"),
        "humidity_pct": ow.get("ow_humidity_pct"),
        "uv_index": ow.get("ow_uv_index"),
        "wind_speed_ms": ow.get("ow_wind_speed_ms"),
        "wind_deg": ow.get("ow_wind_deg"),
    }


def fill_gaps(row: dict, last_known: dict | None, now_unix: int) -> dict:
    """Fills any missing metric in `row` with the matching value from
    `last_known` (the most recent previous feature row, if any) when it
    is less than MAX_STALENESS_HOURS old. Always sets a
    "<metric>_is_imputed" flag so downstream consumers know which values
    were filled rather than observed."""
    filled = dict(row)
    for metric in METRICS:
        is_imputed = False
        if filled.get(metric) is None and last_known is not None:
            age_hours = (now_unix - last_known["timestamp"]) / 3600
            if age_hours <= MAX_STALENESS_HOURS and last_known.get(metric) is not None:
                filled[metric] = last_known[metric]
                is_imputed = True
        filled[f"{metric}_is_imputed"] = is_imputed
    return filled
