"""Builds the derived features from a fused row plus recent history:
  - Time features: hour, day, month, day-of-week (Islamabad local time).
  - Change features: difference from the previous hour, per metric.
  - Rolling features: 3-hour and 24-hour trailing averages, per metric.

`history` is a list of previous feature rows (each a dict with
"timestamp" plus the METRICS columns), oldest first, not including the
current row.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.ingestion.fuse import METRICS

ROLLING_WINDOWS_HOURS = (3, 24)


def time_features(timestamp_unix: int, tz_name: str) -> dict:
    local_dt = datetime.fromtimestamp(timestamp_unix, tz=ZoneInfo(tz_name))
    return {
        "hour": local_dt.hour,
        "day": local_dt.day,
        "month": local_dt.month,
        "day_of_week": local_dt.weekday(),
    }


def change_features(current: dict, history: list[dict]) -> dict:
    previous = history[-1] if history else None
    changes = {}
    for metric in METRICS:
        current_value = current.get(metric)
        previous_value = previous.get(metric) if previous else None
        if current_value is not None and previous_value is not None:
            changes[f"{metric}_change_1h"] = current_value - previous_value
        else:
            changes[f"{metric}_change_1h"] = None
    return changes


def rolling_features(current: dict, history: list[dict]) -> dict:
    rows = history + [current]
    now_ts = current["timestamp"]
    rolling = {}
    for window_hours in ROLLING_WINDOWS_HOURS:
        cutoff = now_ts - window_hours * 3600
        window_rows = [r for r in rows if r["timestamp"] >= cutoff]
        for metric in METRICS:
            values = [r[metric] for r in window_rows if r.get(metric) is not None]
            rolling[f"{metric}_avg_{window_hours}h"] = sum(values) / len(values) if values else None
    return rolling


def build_features(current: dict, history: list[dict], tz_name: str) -> dict:
    row = dict(current)
    row.update(time_features(current["timestamp"], tz_name))
    row.update(change_features(current, history))
    row.update(rolling_features(current, history))
    return row
