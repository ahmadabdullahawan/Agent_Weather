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

- [ ] Connect to the data sources
- [ ] Collect data every hour
- [ ] Build the history
- [ ] Explore the data
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
