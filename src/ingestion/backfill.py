"""Historical backfill entry point (Phase 2).

Fetches Islamabad's historical weather + air quality from Open-Meteo's
archive APIs (OpenWeather and AQICN have no historical access on a
free-tier key — verified live, see openmeteo.py) in ~30-day chunks,
builds the same engineered features as the live hourly pipeline, adds
the 24h-ahead target for each metric, and inserts each chunk as one
batch into the same Hopsworks feature groups the hourly ingestion
writes to.

Run with (from the project root):
    uv run python -m src.ingestion.backfill --start 2026-05-01 --end 2026-11-01
"""

import argparse
import os
import time as time_module
from datetime import date, datetime, timedelta, timezone
from datetime import time as dt_time

from dotenv import load_dotenv

from config.location import LAT, LON, TIMEZONE
from src.ingestion import hopsworks_io, openmeteo
from src.ingestion.features import build_features
from src.ingestion.fuse import METRICS, fill_gaps
from src.ingestion.schema import FEATURES_SCHEMA, RAW_SCHEMA, to_dataframe_many

CHUNK_DAYS = 30
DAY_SECONDS = 24 * 3600


def month_chunks(start: date, end: date):
    cur = start
    while cur <= end:
        chunk_end = min(cur + timedelta(days=CHUNK_DAYS - 1), end)
        yield cur, chunk_end
        cur = chunk_end + timedelta(days=1)


def add_targets(rows_by_ts: dict) -> None:
    """Mutates each row in place, adding "<metric>_target_24h" = the
    observed value of that metric 24h later, if that hour was fetched."""
    for ts, row in rows_by_ts.items():
        future = rows_by_ts.get(ts + DAY_SECONDS)
        for metric in METRICS:
            row[f"{metric}_target_24h"] = future.get(metric) if future else None


def run(start: date, end: date, report_path: str = "reports/backfill_gap_report.md") -> None:
    fs = hopsworks_io.connect()
    raw_fg = hopsworks_io.get_raw_fg(fs)
    features_fg = hopsworks_io.get_features_fg(fs)

    history: list[dict] = []

    report_is_new = not os.path.exists(report_path)
    report_file = open(report_path, "a")
    if report_is_new:
        report_file.write("# Backfill gap report\n\n")
        report_file.write(
            "`uv_index` and `rain_probability_pct` are expected to be missing for every "
            "row (Open-Meteo's historical archive doesn't have them at all).\n\n"
        )
    report_file.write(f"Range requested: {start} to {end}\n\n")
    report_file.flush()

    for chunk_start, chunk_end in month_chunks(start, end):
        chunk_start_ts = int(datetime.combine(chunk_start, dt_time.min, timezone.utc).timestamp())
        chunk_end_ts = chunk_start_ts + (chunk_end - chunk_start).days * DAY_SECONDS + 23 * 3600

        # Open-Meteo's archive lags ~1 day behind today, so the lookahead
        # day (used only for computing targets) can't go past yesterday.
        latest_available = date.today() - timedelta(days=1)
        fetch_end = min(chunk_end + timedelta(days=1), latest_available)

        print(f"Fetching {chunk_start} to {fetch_end} (lookahead for targets capped at {latest_available})...", flush=True)
        om_rows = openmeteo.fetch_range(LAT, LON, chunk_start, fetch_end)
        add_targets(om_rows)

        timestamps = sorted(ts for ts in om_rows if chunk_start_ts <= ts <= chunk_end_ts)
        feature_rows = []
        raw_rows = []
        missing_counts = dict.fromkeys(METRICS, 0)

        for ts in timestamps:
            fused = om_rows[ts]
            last_known = history[-1] if history else None
            filled = fill_gaps(fused, last_known, ts)
            filled["timestamp"] = ts

            feature_row = build_features(filled, history, TIMEZONE)
            feature_rows.append(feature_row)

            history.append(feature_row)
            del history[: max(0, len(history) - 48)]  # keep ~48h, enough for the 24h rolling window

            raw_rows.append(
                {
                    "timestamp": ts,
                    "source": "open_meteo",
                    "om_pm2_5": fused.get("om_pm2_5"),
                    "om_pm10": fused.get("om_pm10"),
                }
            )
            for metric in METRICS:
                if filled.get(metric) is None:
                    missing_counts[metric] += 1

        raw_fg.insert(to_dataframe_many(raw_rows, RAW_SCHEMA), write_options={"wait_for_job": True})
        features_fg.insert(to_dataframe_many(feature_rows, FEATURES_SCHEMA), write_options={"wait_for_job": True})

        summary = ", ".join(f"{m}={c}" for m, c in missing_counts.items() if c > 0)
        line = f"- {chunk_start} to {chunk_end}: {len(timestamps)} hours inserted. Missing: {summary or 'none'}"
        print(line, flush=True)
        report_file.write(line + "\n")
        report_file.flush()

        time_module.sleep(3)  # be polite to Open-Meteo's free API between chunks

    report_file.close()
    print(f"Gap report written to {report_path}", flush=True)


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    run(args.start, args.end)
