"""Checks that each API key in .env is valid, without ever printing the key itself.

Run with:
    uv run python scripts/verify_api_keys.py
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

LAT, LON = 33.6844, 73.0479  # Islamabad


def check_openweather():
    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        return False, "missing from .env"
    r = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"lat": LAT, "lon": LON, "appid": key},
        timeout=10,
    )
    if r.status_code == 200:
        return True, "OK"
    if r.status_code == 401:
        return False, "invalid key, or new key not yet activated (can take up to ~2h)"
    return False, f"HTTP {r.status_code}: {r.text[:200]}"


def check_aqicn():
    token = os.getenv("AQICN_TOKEN")
    if not token:
        return False, "missing from .env"
    r = requests.get(
        f"https://api.waqi.info/feed/geo:{LAT};{LON}/",
        params={"token": token},
        timeout=10,
    )
    data = r.json()
    if r.status_code == 200 and data.get("status") == "ok":
        return True, "OK"
    return False, f"status={data.get('status')}, data={str(data.get('data'))[:200]}"


def check_hopsworks():
    key = os.getenv("HOPSWORKS_API_KEY")
    if not key:
        return False, "missing from .env"
    r = requests.get(
        "https://app.hopsworks.ai/hopsworks-api/api/project",
        headers={"Authorization": f"ApiKey {key}"},
        timeout=10,
    )
    if r.status_code == 200:
        return True, "OK"
    return False, f"HTTP {r.status_code}: {r.text[:200]}"


def check_openai():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return False, "missing from .env"
    r = requests.get(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {key}"},
        timeout=10,
    )
    if r.status_code == 200:
        return True, "OK"
    if r.status_code == 401:
        return False, "invalid key"
    if r.status_code == 429:
        return False, "key valid but no billing/quota set up"
    return False, f"HTTP {r.status_code}: {r.text[:200]}"


def main():
    checks = {
        "OPENWEATHER_API_KEY": check_openweather,
        "AQICN_TOKEN": check_aqicn,
        "HOPSWORKS_API_KEY": check_hopsworks,
        "OPENAI_API_KEY": check_openai,
    }
    print(f"{'Key':<20} {'Result':<6} Detail")
    print("-" * 60)
    for name, fn in checks.items():
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"error: {e}"
        print(f"{name:<20} {'PASS' if ok else 'FAIL':<6} {detail}")


if __name__ == "__main__":
    main()
