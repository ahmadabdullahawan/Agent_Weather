# AgentWeather: Project Plan

Target city: Islamabad, Pakistan (about 33.68°N, 73.05°E)

This plan lists the work in the order it should be done. Each phase has a goal, the tasks, and a "done when" check. Do not start a phase until the previous one is done.

---

## Phase 0: Setup

**Goal:** A working project folder, accounts, and keys.

Tasks:
1. Create a GitHub repository named `agentweather`.
2. Create the project folder on your computer and clone the repository into it.
3. In the project root, run `uv init` to create the Python project.
4. Add the core packages:
   ```bash
   # Run in: project root
   uv add pandas numpy requests python-dotenv
   ```
5. Create accounts (all free tier):
   - OpenWeather (API key)
   - AQICN (API token, from https://aqicn.org/data-platform/token/)
   - Hopsworks (API key)
   - OpenAI (API key, for the AI helper agents)
6. Create `.env.example` with empty placeholders for `OPENWEATHER_API_KEY`, `AQICN_TOKEN`, `HOPSWORKS_API_KEY`, `OPENAI_API_KEY`.
7. Create `.env` with your real keys. Add `.env` to `.gitignore`.
8. Create the folder structure (see the bottom of this plan).

**Done when:** `uv sync` runs without errors, and each API key returns a successful test response.

---

## Phase 1: Data sources and ingestion

**Goal:** One script that fetches, cleans, and stores one hour of Islamabad data.

Tasks:
1. Write a fetch function for OpenWeather (temperature, humidity, rain, wind, UV) for Islamabad.
2. Write a fetch function for AQICN (AQI and pollutants) for Islamabad.
3. Combine both sources into one row per hour. Use one fixed rule and write it in the README (for example: average the two when both exist, otherwise use whichever one exists).
4. Fill gaps with one documented rule (for example: use the last known value if it is less than 3 hours old, otherwise leave it empty and flag it).
5. Compute features:
   - Time features: hour, day, month
   - Change features: difference from the previous hour
   - Rolling features: 3-hour and 24-hour averages
6. Save each row to the Hopsworks Feature Store. Store raw observations and features separately.
7. Run it once by hand and check the new rows in Hopsworks.

Entry point: `src/ingestion/run.py`, run with:
```bash
# Run in: project root
uv run python -m src.ingestion.run
```

**Done when:** Running the script twice for the same hour updates one row and creates no duplicate.

---

## Phase 2: Historical backfill

**Goal:** Enough history to train models (aim for at least 6 months).

Tasks:
1. Check which historical endpoints your OpenWeather and AQICN plans allow. If history is not available on the free tier, use the Open-Meteo historical weather and air-quality archives as the backup source, and note this in the README.
2. Add a date-range option to the ingestion script so it can run for past dates.
3. Run the backfill in small chunks (for example, one month at a time) and check each chunk for gaps.
4. Create the targets: for each hour, the target is the observed value 24 hours later.
5. Leave the newest 24 hours without targets. They are used for forecasting only.

**Done when:** Hopsworks holds at least 6 months of hourly rows for all six metrics, with a gap report saved.

---

## Phase 3: Exploratory data analysis (EDA)

**Goal:** Understand each metric before modelling.

Tasks:
1. For each of the six metrics, plot the values over time.
2. Plot daily and seasonal patterns (by hour of day and by month).
3. Check missing values and outliers, and record how you handled them.
4. Check correlations between metrics and with the time features.
5. Write a short summary for each metric in `reports/eda.md`.

**Done when:** Every metric has a plot and a written summary.

---

## Phase 4: Model training and comparison

**Goal:** A best model for each metric, chosen on validation data.

Tasks:
1. Split the data by time, never randomly:
   - Train: oldest 70%
   - Validation: next 15%
   - Test: newest 15%
   Use the test set only once, for the final score. Choose models on validation.
2. Build the naive baseline: the value from 24 hours ago.
3. Train at least three model families:
   - Statistical: SARIMAX or Prophet
   - Classical ML: Ridge or Random Forest
   - Deep learning: LSTM
4. Use one model per metric, or one model for all six. Choose one approach and write down why.
5. Score every model and the baseline on every metric with RMSE, MAE, and R².
6. Explain the best model with SHAP or LIME. Save the plots.
7. Save the best model to the Hopsworks Model Registry.
8. Add the rule: a new model replaces the current one only if it beats the current model on validation.

Entry point: `src/training/run.py`, run with:
```bash
# Run in: project root
uv run python -m src.training.run
```

**Done when:** A comparison table exists for all models, the baseline, and all six metrics, and the best model is in the registry.

---

## Phase 5: Forecasting

**Goal:** A 24-hour forecast for all six metrics, made every hour.

Tasks:
1. Load the latest feature row from Hopsworks.
2. Load the current best model from the registry.
3. Produce the 24-hour forecast for each metric.
4. Save the forecast to the Forecast Ledger (time made, target time, metric, value).

**Done when:** The Forecast Ledger gets one new 24-row block each hour.

---

## Phase 6: AI helper agents (LangGraph)

**Goal:** Four agents in one LangGraph graph, sharing one state.

Shared state holds: latest forecast, alerts, report, and drift status. It is saved between runs in the Forecast Ledger.

### 6a. Alert Agent
1. Write fixed hazard rules for all six metrics (for example, AQI above a set level, rain above a set amount, UV above a set index). Save them in one config file.
2. Check the forecast against the rules.
3. If a rule triggers, ask the OpenAI model to write the alert for three audiences: the general public, sensitive groups, and outdoor workers. Put the model name in the config file so it can be changed without editing code.
4. If the OpenAI call fails, use a fixed template message instead.

### 6b. Weather Report Agent
1. Use the forecast and any alerts to write one short news-style report.
2. Run it once a day, and also after each new alert.
3. Use the same LLM fallback as the Alert Agent.

### 6c. Drift Agent
1. Data drift: compare the live features with the training features (for example, with a statistical test such as PSI or Kolmogorov-Smirnov). Choose one and write it down.
2. Model drift: compare the recent forecast error with the error recorded on validation data.
3. Set a threshold for each check and write it in the config file.
4. If a threshold is crossed, alert the team and start a training run.
5. Write every drift check to the drift log.

### 6d. Forecast Agent
Runs the Phase 5 steps as a node in the graph.

**Graph order:** Forecast Agent → Alert Agent → Drift Agent. Weather Report Agent runs on its own daily schedule and after new alerts.

Entry point: `src/agents/graph.py`, run with:
```bash
# Run in: project root
uv run python -m src.agents.graph
```

**Done when:** One graph run produces a forecast, checks alerts and drift, and logs each step.

---

## Phase 7: Logging

**Goal:** Every decision is recorded in the Feature Store.

Three logs:
1. **Forecast Ledger:** time made, target time, metric, forecast value.
2. **Agent call log:** agent name, prompt, response, latency, status (success or failed).
3. **Drift log:** time, metric, drift type (data or model), score, threshold, action taken.

Failed LLM calls also go to a separate failure log.

**Done when:** A test run writes to all three logs and to the failure log when a call is forced to fail.

---

## Phase 8: Automation (GitHub Actions)

**Goal:** The system runs by itself.

Tasks:
1. Create `.github/workflows/ingest.yml`: runs the ingestion script every hour.
2. Create `.github/workflows/train.yml`: runs the training script every day. Add the `workflow_dispatch` trigger so the Drift Agent can start it on demand through the GitHub API.
3. Create `.github/workflows/report.yml` or add the report step to the daily run.
4. Store all API keys as GitHub repository secrets, not in the code.
5. Trigger each workflow by hand once, and check the logs.

**Done when:** Each workflow passes a manual run, and the scheduled runs appear in the Actions tab.

---

## Phase 9: Explainability and quality checks

**Goal:** Make sure the results can be trusted and explained.

Tasks:
1. Confirm SHAP or LIME plots exist for the best model.
2. Check that every alert rule has been tested with a sample forecast that should trigger it.
3. Review the agent call log: the success rate, failure rate, and average latency.
4. Review the drift log: check that the drift events match what you expected.

**Done when:** Each check above has a short written result.

---

## Phase 10: Dashboard

**Goal:** A public dashboard that presents the whole system.

Tasks:
1. Build the Streamlit app with these sections:
   - 24-hour forecasts for all six metrics (charts)
   - Latest weather report
   - Agent Activity panel: alerts
   - EDA and SHAP/LIME plots
   - Drift events and metrics
   - Failed agent calls
2. Deploy to Streamlit Community Cloud (or Hugging Face Spaces or Render).
3. Add the link to the README.

**Done when:** The dashboard opens from the public link and shows live data.

---

## Phase 11: Final report

**Goal:** A written report that covers the whole project.

The report must cover:
1. Data sources and how they were combined.
2. How missing values were filled.
3. Model choices and the comparison results.
4. Problems met and how they were fixed.
5. Agent performance:
   - Alert quality (how many alerts were correct)
   - Drift detection (how many drift events were correct)
   - LLM call failure rate

**Done when:** The report is complete and checked against this plan.

---

## Checkpoints

| Checkpoint | After phase | What to show |
|---|---|---|
| 1 | Phase 1 | One hour of data in Hopsworks |
| 2 | Phase 2 | Six months of history with a gap report |
| 3 | Phase 4 | Model comparison table |
| 4 | Phase 6 | One full graph run with logs |
| 5 | Phase 10 | Live dashboard link |

---

## Main risks

| Risk | What to do |
|---|---|
| Free API history is limited | Use Open-Meteo archives as backup (Phase 2) |
| Free Hopsworks limits are reached | Keep only the features needed; delete test rows |
| OpenAI service is down or the key runs out of credit | Use the fixed template fallback (Phase 6); check the usage limit on your OpenAI account |
| Model is worse than the naive baseline | Keep the baseline as the model until a better one is found |
| GitHub Actions schedule runs late | Accept small delays; the forecast still uses the latest saved data |

---

## Folder structure

```
agentweather/
├── .github/workflows/     # hourly ingest, daily train, report
├── src/
│   ├── ingestion/         # run.py, fetch and clean code
│   ├── features/          # feature building
│   ├── training/          # run.py, model code
│   ├── agents/            # graph.py, alert, report, drift agents
│   └── dashboard/         # Streamlit app
├── config/                # alert rules, drift thresholds
├── reports/               # EDA and model comparison outputs
├── notebooks/             # exploration
├── tests/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── plan.md
```

---

## Review

Checked once for: phase order, dependencies between phases, commands matching the folder structure, and every requirement from the project brief (six metrics, 24-hour horizon, RMSE/MAE/R², at least three model families, naive baseline, time-based split, validation-based replacement, four agents, three logs, GitHub Actions schedule, dashboard contents, final report contents).
