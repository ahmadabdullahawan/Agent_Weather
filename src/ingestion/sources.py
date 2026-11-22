"""Raw fetchers for OpenWeather and AQICN. Each returns a flat dict of
raw fields, or raises requests.RequestException if the source is down —
the caller decides how to handle a failed source."""

import requests

OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"
AQICN_BASE = "https://api.waqi.info"

TIMEOUT = 10


def fetch_openweather(lat: float, lon: float, api_key: str) -> dict:
    """Current conditions + UV index + nearest-slot rain probability +
    pollutant concentrations (used to derive an EPA AQI, see aqi.py)."""
    current = requests.get(
        f"{OPENWEATHER_BASE}/weather",
        params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
        timeout=TIMEOUT,
    )
    current.raise_for_status()
    c = current.json()

    uvi = requests.get(
        f"{OPENWEATHER_BASE}/uvi",
        params={"lat": lat, "lon": lon, "appid": api_key},
        timeout=TIMEOUT,
    )
    uvi.raise_for_status()
    uv_value = uvi.json().get("value")

    forecast = requests.get(
        f"{OPENWEATHER_BASE}/forecast",
        params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
        timeout=TIMEOUT,
    )
    forecast.raise_for_status()
    nearest_slot = forecast.json()["list"][0]
    rain_probability_pct = nearest_slot.get("pop", 0.0) * 100

    pollution = requests.get(
        f"{OPENWEATHER_BASE}/air_pollution",
        params={"lat": lat, "lon": lon, "appid": api_key},
        timeout=TIMEOUT,
    )
    pollution.raise_for_status()
    components = pollution.json()["list"][0]["components"]

    return {
        "ow_temperature_c": c["main"]["temp"],
        "ow_humidity_pct": c["main"]["humidity"],
        "ow_wind_speed_ms": c["wind"]["speed"],
        "ow_wind_deg": c["wind"].get("deg"),
        "ow_rain_mm_1h": c.get("rain", {}).get("1h", 0.0),
        "ow_rain_probability_pct": rain_probability_pct,
        "ow_uv_index": uv_value,
        "ow_pm2_5": components["pm2_5"],
        "ow_pm10": components["pm10"],
        "ow_co": components["co"],
        "ow_no2": components["no2"],
        "ow_o3": components["o3"],
        "ow_so2": components["so2"],
        "ow_nh3": components["nh3"],
    }


def fetch_aqicn(lat: float, lon: float, token: str) -> dict:
    """Nearest AQICN station's reported AQI (EPA 0-500 scale) plus enough
    metadata (distance, observation time) for fuse.py to decide whether
    it's fresh and close enough to trust."""
    r = requests.get(
        f"{AQICN_BASE}/feed/geo:{lat};{lon}/",
        params={"token": token},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("status") != "ok":
        raise ValueError(f"AQICN returned status={body.get('status')}")

    data = body["data"]
    station_lat, station_lon = data["city"]["geo"]
    return {
        "aqicn_aqi": data.get("aqi"),
        "aqicn_station_name": data["city"]["name"],
        "aqicn_station_lat": station_lat,
        "aqicn_station_lon": station_lon,
        "aqicn_observed_at_unix": data["time"]["v"],
    }
