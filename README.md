# AgentWeather: Islamabad Weather and Air Quality Forecast

AgentWeather predicts the weather and air quality in Islamabad for the next 24 hours.

It predicts six things:
- Air Quality Index (AQI)
- Temperature
- Rain (amount and chance)
- Humidity
- UV Index
- Wind (speed and direction)

The system collects data every hour, trains its own forecasting model, and uses AI helpers to write warnings and a short weather report. It also checks itself, so it knows when its forecasts are getting worse.

## How it works

1. **Collect data (every hour):** A script gets the current weather and air quality for Islamabad from OpenWeather and AQICN. It cleans the data and saves it.
2. **Build history:** The same script can run for past dates to create a history of data to learn from.
3. **Train the model (every day):** The model learns from the history and is tested on data it hasn't seen. The best model is saved. A new model only replaces the old one if it is more accurate.
4. **Forecast (every hour):** The model predicts the next 24 hours for all six metrics.
5. **AI helpers:**
   - The **Alert Agent** warns the public, people with health problems, and outdoor workers when something is dangerous.
   - The **Weather Report Agent** writes a short news-style weather report once a day.
   - The **Drift Agent** watches for changes in the data or in forecast accuracy. If something changes a lot, it alerts the team and starts retraining.
6. **Keep a record:** Every forecast, AI call, and drift event is saved, so you can check what happened later.

## How the sources are combined

**AQI:** Open-Meteo's live `us_aqi` (`current` endpoint) is the primary
source — the same provider/methodology used for the historical backfill
(its `archive` endpoint), so both periods are consistent by construction.
This replaced an earlier design that derived AQI from OpenWeather's PM2.5/
PM10 via our own EPA breakpoint formula: checked against ~4,943 real
backfill hours, that approach disagreed with Open-Meteo's own number on
over 70% of hours (one genuine bug — a breakpoint-table edge case fixed in
`src/ingestion/aqi.py` — plus an undocumented methodology difference we
couldn't reliably reverse-engineer, e.g. Open-Meteo's AQI sometimes being
driven by ozone rather than PM2.5/PM10). Full writeup:
`reports/aqi_validation.md`. The OpenWeather-derived calculation remains
only as a last-resort fallback if Open-Meteo's live call fails.

**This is a design decision, not a validated match.** Using one source for
both periods makes the training data internally consistent, but it has
**not** been shown that Open-Meteo's live value agrees with its own
archive value for the same hour — that 74% disagreement from the old
two-method comparison was worked around, not resolved. Proving same-hour
agreement isn't possible yet because Open-Meteo's archive lags ~1 day
behind real time; re-run `src/eda/aqi_consistency_check.py` in a couple of
days once today's live-collected hours have aged into the archive. See
Phase 3's status note in `plan.md` and the single-provider risk in its
risk table (relying on one provider for `aqi` in both live and training
data means an Open-Meteo outage or methodology change breaks both at once).

AQICN's Islamabad station (the only one in the city) stopped reporting in
February 2026, and the nearest station still active is 150-400+ km away
(varies by call) — too far to represent Islamabad's air quality, so its
raw reading is stored for reference only and never blended into `aqi`.

Temperature, humidity, rain, UV and wind come from OpenWeather only — AQICN
doesn't report them.

**Gap-fill rule:** if a metric is still missing after fusion, use the last
known value if it is less than 3 hours old; otherwise leave it empty and
flag it with a `<metric>_is_imputed` column.

## Historical backfill

Neither OpenWeather nor AQICN offer historical data on a free-tier key
(verified live — see `src/ingestion/openmeteo.py`), so the training history
(`uv run python -m src.ingestion.backfill --start YYYY-MM-DD --end YYYY-MM-DD`)
comes from Open-Meteo's free archive APIs instead. Two real limitations:
- Open-Meteo has no historical `uv_index` or `rain_probability_pct` at
  all — these are empty for every backfilled row, and only start getting
  real values once the hourly live ingestion collects them going forward.
- A per-chunk gap report is written to `reports/backfill_gap_report.md`.

Exploratory data analysis (`uv run python -m src.eda.run`) reads the full
feature history and writes `reports/eda.md` plus per-metric plots in
`reports/figures/`.

## Tools used

- Python, with `uv` to manage packages
- Hopsworks (free tier) to store data and models
- LangGraph to connect the AI helpers
- OpenAI API for writing alerts and reports
- GitHub Actions to run the hourly and daily jobs automatically
- Streamlit to show the dashboard

## Setup

Run all commands from the **project root** (the folder that contains this README).

1. Install `uv` from https://docs.astral.sh/uv/
2. Install the project packages:

   ```bash
   # Run in: project root
   uv sync
   ```

3. Copy the example settings file and add your API keys:

   ```bash
   # Run in: project root
   cp .env.example .env
   ```

   Open `.env` and fill in your keys. Never share or upload this file.

4. Test the data collection:

   ```bash
   # Run in: project root
   uv run python -m src.ingestion.run
   ```

## Progress

- [x] Connect to the data sources
- [ ] Collect data every hour
- [x] Build the history
- [x] Explore the data — **closed, pending AQI validation** (see `plan.md` Phase 3 status note and `reports/aqi_validation.md`; re-check in ~2 days)
- [ ] Train and compare models
- [ ] Save the best model
- [ ] Build the AI helpers
- [ ] Log everything
- [ ] Automate with GitHub Actions
- [ ] Put the dashboard online
- [ ] Write the final report

## City

Islamabad, Pakistan (about 33.68°N, 73.05°E)

## Author

Abdullah Ahmad
