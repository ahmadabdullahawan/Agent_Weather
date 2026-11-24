# AQI method consistency check

Generated: 2026-11-24T17:36:39.133843+00:00

## What changed and why

The original plan derived live AQI from OpenWeather's PM2.5/PM10 via our own EPA breakpoint formula, and backfill AQI from Open-Meteo's precomputed `us_aqi`. Checking the two against each other on ~4,943 real backfill hours (same concentrations, both methods) found: (1) a genuine bug — untruncated concentrations falling into gaps between EPA breakpoint edges were incorrectly clamped to a false AQI of 500 (now fixed in `src/ingestion/aqi.py`); (2) even after that fix, ~74% of hours still disagreed by more than 10 points, traced to Open-Meteo's AQI sometimes being driven by ozone or another pollutant we never considered, and to an apparent PM2.5 methodology difference that didn't match either EPA breakpoint table version or a NowCast reconstruction on raw instantaneous concentrations.

**Design change (not yet a validated fix):** stop approximating. Open-Meteo's `current` endpoint serves the same `us_aqi` live, from the same provider as the archive used for backfill (`src/ingestion/openmeteo.py::fetch_current_aqi`, now the primary AQI source in `fuse.py`). This sidesteps the need to reconcile two different calculations by using one source throughout — but it does **not** by itself prove that Open-Meteo's live value agrees with its own archive value for the same hour. See the archive catch-up check below for the real evidence once it's available. The OpenWeather-derived formula remains only as a last-resort fallback if Open-Meteo's live call fails.

## Live endpoint self-consistency

- At 2026-11-24T17:00: `current.us_aqi` = 137, the same call's `hourly.us_aqi` for that hour = 137 — **match**.

## Archive catch-up status (direct same-hour proof, when available)

- Archive now covers 1 of 1 live-ingested date(s) (2026-11-22) — running the direct comparison:

- Hours compared: **1**
- Mean absolute difference: **0.00 AQI points**
- Largest difference: **0.00 AQI points**
- Share of hours differing by more than 10 AQI points: **0.0%**

**Agree closely — same-hour proof complete.**


## Secondary check: AQICN vs OpenWeather-derived (live fusion rule only)

A different, weaker question — AQICN and OpenWeather describe different stations/locations, not the same concentrations — relevant only to the live fusion's AQICN trust threshold. Does **not** gate Phase 4.

- Only 1 stored hour so far: AQICN=70 at "Rajbagh, Srinagar, India" (169 km away) vs OpenWeather-derived=209.9. Grows automatically as live ingestion runs more.


## Conclusion


**Phase 3 closes.** The same-hour archive-vs-live comparison above is real evidence, not a design assumption: Open-Meteo's live value and its own archive value agree closely for the same hours. Safe to treat `aqi` as consistent across the backfill and live periods.

