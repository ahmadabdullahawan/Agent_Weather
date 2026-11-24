# Model comparison

Generated: 2026-11-24T18:29:19.587923+00:00

Split: time-based, never shuffled -- oldest 70% train (3461 rows), next 15% validation (741 rows), newest 15% test (743 rows).

**AQI is excluded.** Phase 3's AQI validation hasn't fully closed yet -- see `plan.md`'s Phase 3 status note and `reports/aqi_validation.md`. It will be added back once that closes.

**SARIMAX/Random Forest/LSTM skipped for: rain_probability_pct, uv_index** (naive baseline still shown). Open-Meteo's historical archive has no data for these at all (see README); real values only exist for the handful of hours live ingestion has collected so far -- not enough to fit anything.

**Model choices (plan.md task 4 -- one model per metric, per family):**
- Statistical: SARIMAX, not Prophet -- same seasonal-ARIMA capability without Prophet's heavier cmdstan/pystan install on Windows.
- Classical ML: Random Forest, not Ridge -- the EDA (`reports/eda.md`) shows clearly non-linear, seasonal relationships that Random Forest captures natively; it's also what Phase 4 task 6's SHAP step is built around.
- Deep learning: an LSTM over a 48h lookback window of the engineered features.
- One model per metric in every family, not one shared model across all six -- each metric's relationship to the shared features differs enough (see `reports/eda.md`) that a shared model would average that away.

`wind_deg` is circular data (0 degrees and 360 degrees are the same direction), so RMSE/MAE/R2 on it -- for every model here, not just the baseline -- should be read cautiously; the EDA flags the same caveat.

| Metric | Split | Model | n | RMSE | MAE | R2 |
|---|---|---|---|---|---|---|
| temperature_c | validation | naive (24h persistence) | 741 | 1.79 | 1.21 | 0.793 |
| temperature_c | test | naive (24h persistence) | 718 | 1.15 | 0.84 | 0.906 |
| temperature_c | validation | SARIMAX | 741 | 1.63 | 1.18 | 0.828 |
| temperature_c | test | SARIMAX | 718 | 1.05 | 0.75 | 0.922 |
| temperature_c | validation | Random Forest | 741 | 2.51 | 1.95 | 0.591 |
| temperature_c | test | Random Forest | 718 | 4.79 | 4.06 | -0.615 |
| temperature_c | validation | LSTM | 0 | n/a | n/a | n/a |
| temperature_c | test | LSTM | 0 | n/a | n/a | n/a |
| rain_mm | validation | naive (24h persistence) | 741 | 0.45 | 0.11 | -1.019 |
| rain_mm | test | naive (24h persistence) | 718 | 0.85 | 0.16 | -1.031 |
| rain_mm | validation | SARIMAX | 741 | 0.34 | 0.15 | -0.159 |
| rain_mm | test | SARIMAX | 718 | 0.66 | 0.20 | -0.231 |
| rain_mm | validation | Random Forest | 741 | 0.37 | 0.16 | -0.338 |
| rain_mm | test | Random Forest | 718 | 0.61 | 0.16 | -0.051 |
| rain_mm | validation | LSTM | 0 | n/a | n/a | n/a |
| rain_mm | test | LSTM | 0 | n/a | n/a | n/a |
| rain_probability_pct | validation | naive (24h persistence) | 0 | n/a | n/a | n/a |
| rain_probability_pct | test | naive (24h persistence) | 0 | n/a | n/a | n/a |
| rain_probability_pct | validation | SARIMAX | 0 | n/a | n/a | n/a |
| rain_probability_pct | test | SARIMAX | 0 | n/a | n/a | n/a |
| rain_probability_pct | validation | Random Forest | 0 | n/a | n/a | n/a |
| rain_probability_pct | test | Random Forest | 0 | n/a | n/a | n/a |
| rain_probability_pct | validation | LSTM | 0 | n/a | n/a | n/a |
| rain_probability_pct | test | LSTM | 0 | n/a | n/a | n/a |
| humidity_pct | validation | naive (24h persistence) | 741 | 10.05 | 7.47 | 0.564 |
| humidity_pct | test | naive (24h persistence) | 718 | 9.28 | 7.18 | 0.508 |
| humidity_pct | validation | SARIMAX | 741 | 9.35 | 7.12 | 0.623 |
| humidity_pct | test | SARIMAX | 718 | 8.53 | 6.72 | 0.584 |
| humidity_pct | validation | Random Forest | 741 | 9.51 | 7.31 | 0.610 |
| humidity_pct | test | Random Forest | 718 | 10.13 | 8.25 | 0.413 |
| humidity_pct | validation | LSTM | 0 | n/a | n/a | n/a |
| humidity_pct | test | LSTM | 0 | n/a | n/a | n/a |
| uv_index | validation | naive (24h persistence) | 0 | n/a | n/a | n/a |
| uv_index | test | naive (24h persistence) | 0 | n/a | n/a | n/a |
| uv_index | validation | SARIMAX | 0 | n/a | n/a | n/a |
| uv_index | test | SARIMAX | 0 | n/a | n/a | n/a |
| uv_index | validation | Random Forest | 0 | n/a | n/a | n/a |
| uv_index | test | Random Forest | 0 | n/a | n/a | n/a |
| uv_index | validation | LSTM | 0 | n/a | n/a | n/a |
| uv_index | test | LSTM | 0 | n/a | n/a | n/a |
| wind_speed_ms | validation | naive (24h persistence) | 741 | 1.01 | 0.75 | -0.624 |
| wind_speed_ms | test | naive (24h persistence) | 718 | 1.11 | 0.84 | -0.726 |
| wind_speed_ms | validation | SARIMAX | 741 | 0.81 | 0.61 | -0.033 |
| wind_speed_ms | test | SARIMAX | 718 | 0.88 | 0.69 | -0.080 |
| wind_speed_ms | validation | Random Forest | 741 | 0.81 | 0.61 | -0.047 |
| wind_speed_ms | test | Random Forest | 718 | 0.90 | 0.68 | -0.136 |
| wind_speed_ms | validation | LSTM | 0 | n/a | n/a | n/a |
| wind_speed_ms | test | LSTM | 0 | n/a | n/a | n/a |
| wind_deg | validation | naive (24h persistence) | 741 | 161.35 | 110.52 | -0.678 |
| wind_deg | test | naive (24h persistence) | 718 | 163.66 | 110.11 | -1.046 |
| wind_deg | validation | SARIMAX | 741 | 137.58 | 116.20 | -0.220 |
| wind_deg | test | SARIMAX | 718 | 135.37 | 109.19 | -0.400 |
| wind_deg | validation | Random Forest | 741 | 126.93 | 115.81 | -0.038 |
| wind_deg | test | Random Forest | 718 | 125.53 | 117.85 | -0.204 |
| wind_deg | validation | LSTM | 0 | n/a | n/a | n/a |
| wind_deg | test | LSTM | 0 | n/a | n/a | n/a |
