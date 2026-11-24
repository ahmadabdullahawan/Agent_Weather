"""AQI method consistency check — the Phase 2 condition Phase 4 depends on.

History of this check (see git history / conversation for full detail):
1. First version compared AQICN vs OpenWeather-derived AQI — the wrong
   question (different stations/cities, not the same inputs).
2. Second version compared our own EPA-breakpoint calculation (on
   OpenWeather's PM2.5/PM10) against Open-Meteo's own `us_aqi` (used for
   backfill) on the same ~4,943 backfill-hour concentrations. Found two
   real problems: (a) a genuine bug — unturncated concentrations fell
   into gaps between EPA breakpoint table edges and got clamped to a
   false 500 (fixed in aqi.py); (b) even after that fix, ~74% of hours
   still disagreed by >10 points, traced to Open-Meteo's AQI sometimes
   being driven by ozone or another pollutant we never considered, and
   to its PM2.5 sub-index not matching either EPA breakpoint table
   version on raw instantaneous concentrations (confirmed against
   Open-Meteo's own `us_aqi_pm2_5`/`us_aqi_ozone` fields directly) —
   i.e. an undocumented methodology we couldn't reliably reverse-engineer.
3. Resolution: stop deriving AQI from OpenWeather concentrations at all.
   Open-Meteo's `current` endpoint gives the same `us_aqi` live, same
   provider/methodology as the archive used for backfill. Both periods
   now use ONE source by construction (src/ingestion/openmeteo.py
   `fetch_current_aqi`, wired into fuse.py as the primary AQI source).
   The OpenWeather-derived calculation (aqi.py) is kept only as a
   last-resort fallback if Open-Meteo's live call fails.

What this script checks now:
  - Primary: confirms the live and backfill paths are in fact using the
    same source/method (by construction) and reports the one thing that
    can't be proven until the archive catches up — its ~1-day lag means
    today's live-collected hours aren't yet in the archive to compare
    directly. Reports internal self-consistency of the live endpoint
    (current value vs. its own hourly block for the same hour) as the
    best available evidence today, and flags that re-running this
    script in a few days (once the archive includes today's dates) will
    complete the direct same-hour proof automatically.
  - Secondary: AQICN vs OpenWeather-derived, kept for the live fusion's
    AQICN trust rule only — does not gate Phase 4.

Run with (from the project root):
    uv run python -m src.eda.aqi_consistency_check
"""

from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv

from config.location import LAT, LON
from src.ingestion import hopsworks_io
from src.ingestion.aqi import compute_aqi
from src.ingestion.fuse import AQICN_MAX_DISTANCE_KM, MAX_STALENESS_HOURS, haversine_km
from src.ingestion.openmeteo import AIR_QUALITY_URL, _get_with_retry, fetch_range

REPORT_PATH = "reports/aqi_validation.md"
DISAGREEMENT_THRESHOLD = 10  # AQI points


def check_live_self_consistency() -> dict:
    """The `current` field and the matching hour in the same call's
    `hourly` block should be identical — both come from the same
    request/methodology, so this isolates any client-side mistake from
    the (separate, unprovable-today) archive-vs-live question."""
    data = _get_with_retry(
        AIR_QUALITY_URL,
        {"latitude": LAT, "longitude": LON, "hourly": "us_aqi", "current": "us_aqi", "timezone": "UTC"},
    )
    current = data["current"]
    idx = data["hourly"]["time"].index(current["time"])
    hourly_value = data["hourly"]["us_aqi"][idx]
    return {
        "time": current["time"],
        "current_aqi": current["us_aqi"],
        "hourly_aqi": hourly_value,
        "match": current["us_aqi"] == hourly_value,
    }


def compare_archive_vs_live() -> dict:
    """For every live-ingested hour (source="openweather_aqicn") that has
    a stored `aqi`, checks the archive for that hour's date and, where
    the archive now covers it, compares our stored `aqi` (Open-Meteo's
    live value at ingestion time) against the archive's value for that
    same hour — the real same-hour proof. Checks against the actual
    dates of live-ingested hours (not today's date) since the archive's
    ~1-day lag means it can already cover yesterday's live hours even
    though it never covers today's."""
    fs = hopsworks_io.connect()
    raw_fg = hopsworks_io.get_raw_fg(fs)
    features_fg = hopsworks_io.get_features_fg(fs)

    raw = raw_fg.read()
    live_hours = raw[raw["source"] == "openweather_aqicn"][["timestamp"]]
    features = features_fg.read()[["timestamp", "aqi"]].rename(columns={"aqi": "live_aqi"})
    merged = live_hours.merge(features, on="timestamp", how="inner")
    merged = merged[merged["live_aqi"].notna()]
    if merged.empty:
        return {"status": "no_live_rows", "comparison": merged, "dates_needed": [], "dates_covered": []}

    dates_needed = sorted({datetime.fromtimestamp(ts, tz=timezone.utc).date() for ts in merged["timestamp"]})
    archive_by_ts = {}
    dates_covered = []
    for d in dates_needed:
        rows = fetch_range(LAT, LON, d, d)
        if rows:
            dates_covered.append(d)
        archive_by_ts.update({ts: row["aqi"] for ts, row in rows.items()})

    merged["archive_aqi"] = merged["timestamp"].map(archive_by_ts)
    compared = merged[merged["archive_aqi"].notna()].copy()
    compared["diff"] = (compared["live_aqi"] - compared["archive_aqi"]).abs()
    status = "ok" if not compared.empty else "archive_not_caught_up"
    return {"status": status, "comparison": compared, "dates_needed": dates_needed, "dates_covered": dates_covered}


def load_aqicn_overlap() -> pd.DataFrame:
    fs = hopsworks_io.connect()
    raw_fg = hopsworks_io.get_raw_fg(fs)
    df = raw_fg.read()
    overlap = df[df["aqicn_aqi"].notna()].copy()
    if overlap.empty:
        return overlap
    overlap["ow_computed_aqi"] = overlap.apply(lambda r: compute_aqi(r["ow_pm2_5"], r["ow_pm10"]), axis=1)
    overlap["distance_km"] = overlap.apply(
        lambda r: haversine_km(LAT, LON, r["aqicn_station_lat"], r["aqicn_station_lon"]), axis=1
    )
    overlap["age_hours"] = (overlap["timestamp"] - overlap["aqicn_observed_at_unix"]) / 3600
    overlap["trusted"] = (overlap["distance_km"] <= AQICN_MAX_DISTANCE_KM) & (
        overlap["age_hours"].abs() <= MAX_STALENESS_HOURS
    )
    return overlap


def run() -> None:
    lines = ["# AQI method consistency check\n"]
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")

    lines.append("## What changed and why\n")
    lines.append(
        "The original plan derived live AQI from OpenWeather's PM2.5/PM10 via our own EPA "
        "breakpoint formula, and backfill AQI from Open-Meteo's precomputed `us_aqi`. Checking "
        "the two against each other on ~4,943 real backfill hours (same concentrations, both "
        "methods) found: (1) a genuine bug — untruncated concentrations falling into gaps "
        "between EPA breakpoint edges were incorrectly clamped to a false AQI of 500 (now fixed "
        "in `src/ingestion/aqi.py`); (2) even after that fix, ~74% of hours still disagreed by "
        "more than 10 points, traced to Open-Meteo's AQI sometimes being driven by ozone or "
        "another pollutant we never considered, and to an apparent PM2.5 methodology difference "
        "that didn't match either EPA breakpoint table version or a NowCast reconstruction on "
        "raw instantaneous concentrations.\n\n"
        "**Design change (not yet a validated fix):** stop approximating. Open-Meteo's `current` "
        "endpoint serves the same `us_aqi` live, from the same provider as the archive used for "
        "backfill (`src/ingestion/openmeteo.py::fetch_current_aqi`, now the primary AQI source in "
        "`fuse.py`). This sidesteps the need to reconcile two different calculations by using one "
        "source throughout — but it does **not** by itself prove that Open-Meteo's live value "
        "agrees with its own archive value for the same hour. See the archive catch-up check below "
        "for the real evidence once it's available. The OpenWeather-derived formula remains only "
        "as a last-resort fallback if Open-Meteo's live call fails.\n"
    )

    lines.append("## Live endpoint self-consistency\n")
    self_check = check_live_self_consistency()
    lines.append(
        f"- At {self_check['time']}: `current.us_aqi` = {self_check['current_aqi']}, the same "
        f"call's `hourly.us_aqi` for that hour = {self_check['hourly_aqi']} — "
        f"**{'match' if self_check['match'] else 'MISMATCH'}**.\n"
    )

    lines.append("## Archive catch-up status (direct same-hour proof, when available)\n")
    result = compare_archive_vs_live()
    archive_vs_live_ok = None
    if result["status"] == "no_live_rows":
        lines.append(
            "- No live-ingested hours with a stored `aqi` exist yet. Run live ingestion "
            "(`src/ingestion/run.py`) a few times first, then re-run this script.\n"
        )
    elif result["status"] == "archive_not_caught_up":
        lines.append(
            f"- {len(result['dates_needed'])} live-ingested date(s) need checking "
            f"({', '.join(d.isoformat() for d in result['dates_needed'])}), but the archive "
            f"doesn't cover any of them yet (the archive's usual ~1-day lag). This is expected, "
            f"not an error. Re-running this script in a day or two, once the archive catches up "
            f"to these dates, completes the proof with real matched hours.\n"
        )
    else:
        comparison = result["comparison"]
        n = len(comparison)
        lines.append(
            f"- Archive now covers {len(result['dates_covered'])} of "
            f"{len(result['dates_needed'])} live-ingested date(s) "
            f"({', '.join(d.isoformat() for d in result['dates_covered'])}) — running the direct comparison:\n"
        )
        mean_diff = comparison["diff"].mean()
        max_diff = comparison["diff"].max()
        exceed_pct = (comparison["diff"] > DISAGREEMENT_THRESHOLD).mean() * 100
        archive_vs_live_ok = bool(exceed_pct < 10)
        lines.append(f"- Hours compared: **{n}**")
        lines.append(f"- Mean absolute difference: **{mean_diff:.2f} AQI points**")
        lines.append(f"- Largest difference: **{max_diff:.2f} AQI points**")
        lines.append(
            f"- Share of hours differing by more than {DISAGREEMENT_THRESHOLD} AQI points: "
            f"**{exceed_pct:.1f}%**\n"
        )
        lines.append(
            f"**{'Agree closely — same-hour proof complete.' if archive_vs_live_ok else 'Do NOT agree closely — the single-source design does not actually solve the original disagreement.'}**\n"
        )

    lines.append(
        "\n## Secondary check: AQICN vs OpenWeather-derived (live fusion rule only)\n\n"
        "A different, weaker question — AQICN and OpenWeather describe different "
        "stations/locations, not the same concentrations — relevant only to the live fusion's "
        "AQICN trust threshold. Does **not** gate Phase 4.\n"
    )
    try:
        aqicn_overlap = load_aqicn_overlap()
    except Exception as exc:
        lines.append(
            f"- Could not run this check: Hopsworks read failed ({exc}). This is the weaker, "
            "non-gating check, so the failure is reported here rather than aborting the whole "
            "script before the report below could be written. Re-run to retry.\n"
        )
        aqicn_overlap = pd.DataFrame()

    if len(aqicn_overlap) >= 2:
        corr = aqicn_overlap["aqicn_aqi"].corr(aqicn_overlap["ow_computed_aqi"])
        mae = (aqicn_overlap["aqicn_aqi"] - aqicn_overlap["ow_computed_aqi"]).abs().mean()
        trusted_pct = aqicn_overlap["trusted"].mean() * 100
        lines.append(
            f"- Stored overlap: {len(aqicn_overlap)} hours, correlation {corr:.2f}, mean "
            f"absolute difference {mae:.1f}, {trusted_pct:.1f}% pass the "
            f"{AQICN_MAX_DISTANCE_KM}km/{MAX_STALENESS_HOURS}h trust threshold.\n"
        )
    elif len(aqicn_overlap) == 1:
        row = aqicn_overlap.iloc[0]
        lines.append(
            f"- Only 1 stored hour so far: AQICN={row['aqicn_aqi']:.0f} at "
            f"\"{row['aqicn_station_name']}\" ({row['distance_km']:.0f} km away) vs "
            f"OpenWeather-derived={row['ow_computed_aqi']:.1f}. Grows automatically as live "
            f"ingestion runs more.\n"
        )
    else:
        lines.append("- No stored overlap yet.\n")

    lines.append("\n## Conclusion\n\n")
    if archive_vs_live_ok is True:
        lines.append(
            "**Phase 3 closes.** The same-hour archive-vs-live comparison above is real evidence, "
            "not a design assumption: Open-Meteo's live value and its own archive value agree "
            "closely for the same hours. Safe to treat `aqi` as consistent across the backfill "
            "and live periods.\n"
        )
    elif archive_vs_live_ok is False:
        lines.append(
            "**Phase 3 does NOT close.** The same-hour archive-vs-live comparison above shows the "
            "single-source design does not actually resolve the original disagreement — Open-Meteo "
            "itself revises values between its live/forecast output and its finalized archive. "
            "This needs further investigation before training on `aqi` (e.g. always using the "
            "archive's finalized value once available, at the cost of a reporting delay, rather "
            "than the live value).\n"
        )
    else:
        lines.append(
            "**Phase 3 status: closed, pending AQI validation — not yet fully closed.** Using one "
            "source (Open-Meteo) for AQI in both the backfill and the live pipeline is a reasonable "
            "design decision — it makes the training data internally consistent — but it is "
            "**not** a validated match. The original finding stands unresolved: our old "
            "OpenWeather-derived calculation disagreed with Open-Meteo's own `us_aqi` on 74% of "
            "~4,943 backfill hours. Switching the live source to Open-Meteo sidesteps that specific "
            "disagreement by no longer computing AQI two different ways, but it has not been shown "
            "that Open-Meteo's live value agrees with its own archive value for the same hour — "
            "that direct proof isn't possible until the archive catches up (~1-day lag). Re-run "
            "this script in a couple of days; it will then compute the real archive-vs-live "
            "comparison automatically and only report Phase 3 as fully closed if they agree.\n"
        )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"AQI consistency check written to {REPORT_PATH}")


if __name__ == "__main__":
    load_dotenv()
    run()
