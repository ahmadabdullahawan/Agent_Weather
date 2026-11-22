"""Historical backfill source: Open-Meteo's archive APIs.

Neither OpenWeather nor AQICN offer historical data on a free-tier key
(verified live: OpenWeather's timemachine endpoints both 401, AQICN's
/feed/ endpoint silently ignores a date parameter). Open-Meteo's
archive APIs are free, keyless, and do have real historical data for
Islamabad.

Two gaps, confirmed empty on every date tested: `uv_index` and
`precipitation_probability` are not available historically at all (only
as forecast-only products), so backfilled rows leave `uv_index` and
`rain_probability_pct` as None.
"""

import time
from datetime import date, datetime, timezone

import requests

WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
MAX_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = (5, 15, 30)

KMH_TO_MS = 1 / 3.6


def _parse_utc(iso_local_naive: str) -> int:
    # Requested with timezone=UTC, so these strings are already UTC,
    # just missing the offset suffix.
    return int(datetime.fromisoformat(iso_local_naive).replace(tzinfo=timezone.utc).timestamp())


def _get_with_retry(url: str, params: dict) -> dict:
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            r = requests.get(url, params=params, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            last_error = e
            if attempt < MAX_ATTEMPTS - 1:
                delay = RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)]
                print(f"  WARNING: {url} failed ({e}); retrying in {delay}s...", flush=True)
                time.sleep(delay)
    raise RuntimeError(f"Giving up on {url} after {MAX_ATTEMPTS} attempts") from last_error


def fetch_current_aqi(lat: float, lon: float) -> dict:
    """Open-Meteo's own live `us_aqi`, from the same provider/methodology
    as the historical archive used for backfill. Used instead of deriving
    our own approximate AQI from OpenWeather's raw concentrations — that
    approach was checked against Open-Meteo's archive on ~4,943 backfill
    hours and found to disagree substantially (see
    reports/aqi_validation.md), because Open-Meteo's AQI calculation
    isn't a simple instantaneous PM2.5/PM10 breakpoint lookup (it also
    weighs other pollutants like ozone, and doesn't match either EPA
    breakpoint table version on raw instantaneous PM2.5 — likely some
    smoothing/correction we couldn't reverse-engineer reliably). Using
    the same source for both periods sidesteps that entirely."""
    data = _get_with_retry(
        AIR_QUALITY_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "current": "us_aqi,pm2_5,pm10",
            "timezone": "UTC",
        },
    )["current"]
    return {
        "aqi": data.get("us_aqi"),
        "om_pm2_5": data.get("pm2_5"),
        "om_pm10": data.get("pm10"),
        "observed_at_unix": _parse_utc(data["time"]),
    }


def fetch_range(lat: float, lon: float, start_date: date, end_date: date) -> dict[int, dict]:
    """Returns {timestamp_unix: {metric: value}} for every hour in
    [start_date, end_date] (inclusive), already in our METRICS naming."""
    w = _get_with_retry(
        WEATHER_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m",
            "timezone": "UTC",
        },
    )["hourly"]

    aq = _get_with_retry(
        AIR_QUALITY_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "hourly": "pm2_5,pm10,us_aqi",
            "timezone": "UTC",
        },
    )["hourly"]

    aq_by_ts = {_parse_utc(t): i for i, t in enumerate(aq["time"])}

    rows = {}
    for i, t in enumerate(w["time"]):
        ts = _parse_utc(t)
        aq_i = aq_by_ts.get(ts)
        rows[ts] = {
            "aqi": aq["us_aqi"][aq_i] if aq_i is not None else None,
            "temperature_c": w["temperature_2m"][i],
            "rain_mm": w["precipitation"][i],
            "rain_probability_pct": None,  # not available historically
            "humidity_pct": w["relative_humidity_2m"][i],
            "uv_index": None,  # not available historically
            "wind_speed_ms": (w["wind_speed_10m"][i] * KMH_TO_MS) if w["wind_speed_10m"][i] is not None else None,
            "wind_deg": w["wind_direction_10m"][i],
            "om_pm2_5": aq["pm2_5"][aq_i] if aq_i is not None else None,
            "om_pm10": aq["pm10"][aq_i] if aq_i is not None else None,
        }
    return rows
