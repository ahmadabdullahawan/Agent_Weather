"""Hopsworks Feature Store connection and feature group access.

Two feature groups, both keyed and deduplicated on "timestamp" (unix
seconds, floored to the hour): raw observations are stored as received
from each source, and engineered features are stored separately, per
the Phase 1 "store raw and features separately" requirement. Hopsworks
upserts on the primary key, so re-running the ingestion script for an
hour that's already stored updates that row instead of duplicating it.
"""

import os

import hopsworks

RAW_FG_NAME = "islamabad_raw_observations"
FEATURES_FG_NAME = "islamabad_features"
FG_VERSION = 1


def connect():
    project = hopsworks.login(
        api_key_value=os.environ["HOPSWORKS_API_KEY"],
        project=os.environ.get("HOPSWORKS_PROJECT", "Agent_Weather_Isb"),
    )
    return project.get_feature_store()


def get_raw_fg(fs):
    return fs.get_or_create_feature_group(
        name=RAW_FG_NAME,
        version=FG_VERSION,
        description="Raw hourly OpenWeather + AQICN observations for Islamabad",
        primary_key=["timestamp"],
        event_time="timestamp",
        online_enabled=False,
        time_travel_format="HUDI",
    )


def get_features_fg(fs):
    return fs.get_or_create_feature_group(
        name=FEATURES_FG_NAME,
        version=FG_VERSION,
        description="Engineered hourly features for Islamabad (time/change/rolling)",
        primary_key=["timestamp"],
        event_time="timestamp",
        online_enabled=False,
        time_travel_format="HUDI",
    )


def read_recent_features(fg, since_unix: int) -> list[dict]:
    """Reads feature rows with timestamp >= since_unix, sorted oldest
    first. Used to build change/rolling features without reading the
    whole (ever-growing) table every run."""
    if not fg.features:
        # Freshly created feature group, nothing has been inserted yet.
        return []
    query = fg.filter(fg.timestamp >= since_unix)
    df = query.read()
    if df.empty:
        return []
    return df.sort_values("timestamp").to_dict("records")
