# AQI method consistency check

Generated: 2026-11-22T22:52:29.902986+00:00

## What changed and why

The original plan derived live AQI from OpenWeather's PM2.5/PM10 via our own EPA breakpoint formula, and backfill AQI from Open-Meteo's precomputed `us_aqi`. Checking the two against each other on ~4,943 real backfill hours (same concentrations, both methods) found: (1) a genuine bug — untruncated concentrations falling into gaps between EPA breakpoint edges were incorrectly clamped to a false AQI of 500 (now fixed in `src/ingestion/aqi.py`); (2) even after that fix, ~74% of hours still disagreed by more than 10 points, traced to Open-Meteo's AQI sometimes being driven by ozone or another pollutant we never considered, and to an apparent PM2.5 methodology difference that didn't match either EPA breakpoint table version or a NowCast reconstruction on raw instantaneous concentrations.

**Design change (not yet a validated fix):** stop approximating. Open-Meteo's `current` endpoint serves the same `us_aqi` live, from the same provider as the archive used for backfill (`src/ingestion/openmeteo.py::fetch_current_aqi`, now the primary AQI source in `fuse.py`). This sidesteps the need to reconcile two different calculations by using one source throughout — but it does **not** by itself prove that Open-Meteo's live value agrees with its own archive value for the same hour. See the archive catch-up check below for the real evidence once it's available. The OpenWeather-derived formula remains only as a last-resort fallback if Open-Meteo's live call fails.

## Live endpoint self-consistency

- At 2026-11-22T22:00: `current.us_aqi` = 137, the same call's `hourly.us_aqi` for that hour = 137 — **match**.

## Archive catch-up status (direct same-hour proof, when available)

- As of this run, the archive does not yet have data for 2026-11-22 (the archive's usual ~1-day lag). This is expected, not an error. The live hours being ingested now (`src/ingestion/run.py`, and Phase 8's hourly job once set up) will become directly comparable against the archive once it catches up in a day or two — re-running this script then completes the proof with real matched hours.


## Secondary check: AQICN vs OpenWeather-derived (live fusion rule only)

A different, weaker question — AQICN and OpenWeather describe different stations/locations, not the same concentrations — relevant only to the live fusion's AQICN trust threshold. Does **not** gate Phase 4.

- Only 1 stored hour so far: AQICN=70 at "Rajbagh, Srinagar, India" (169 km away) vs OpenWeather-derived=209.9. Grows automatically as live ingestion runs more.


## Conclusion


**Phase 3 status: closed, pending AQI validation — not yet fully closed.** Using one source (Open-Meteo) for AQI in both the backfill and the live pipeline is a reasonable design decision — it makes the training data internally consistent — but it is **not** a validated match. The original finding stands unresolved: our old OpenWeather-derived calculation disagreed with Open-Meteo's own `us_aqi` on 74% of ~4,943 backfill hours. Switching the live source to Open-Meteo sidesteps that specific disagreement by no longer computing AQI two different ways, but it has not been shown that Open-Meteo's live value agrees with its own archive value for the same hour — that direct proof isn't possible until the archive catches up (~1-day lag). Re-run this script in a couple of days; it will then compute the real archive-vs-live comparison automatically and only report Phase 3 as fully closed if they agree.

