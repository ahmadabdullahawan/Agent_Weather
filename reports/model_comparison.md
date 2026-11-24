# Model comparison

Generated: 2026-11-24T17:47:45.353948+00:00

Split: time-based, never shuffled -- oldest 70% train (3461 rows), next 15% validation (741 rows), newest 15% test (743 rows).

**AQI is excluded from this comparison.** Phase 3's AQI validation hasn't fully closed yet -- see `plan.md`'s Phase 3 status note and `reports/aqi_validation.md`. It will be added back once that closes.

**Baseline only so far.** This is Phase 4 scaffolding (the time-based split and the naive baseline) -- SARIMAX/Prophet, Ridge/Random Forest, and LSTM rows are added in later work.

| Metric | Split | Model | n | RMSE | MAE | R2 |
|---|---|---|---|---|---|---|
| temperature_c | validation | naive (24h persistence) | 741 | 1.79 | 1.21 | 0.793 |
| temperature_c | test | naive (24h persistence) | 718 | 1.15 | 0.84 | 0.906 |
| rain_mm | validation | naive (24h persistence) | 741 | 0.45 | 0.11 | -1.019 |
| rain_mm | test | naive (24h persistence) | 718 | 0.85 | 0.16 | -1.031 |
| rain_probability_pct | validation | naive (24h persistence) | 0 | n/a | n/a | n/a |
| rain_probability_pct | test | naive (24h persistence) | 0 | n/a | n/a | n/a |
| humidity_pct | validation | naive (24h persistence) | 741 | 10.05 | 7.47 | 0.564 |
| humidity_pct | test | naive (24h persistence) | 718 | 9.28 | 7.18 | 0.508 |
| uv_index | validation | naive (24h persistence) | 0 | n/a | n/a | n/a |
| uv_index | test | naive (24h persistence) | 0 | n/a | n/a | n/a |
| wind_speed_ms | validation | naive (24h persistence) | 741 | 1.01 | 0.75 | -0.624 |
| wind_speed_ms | test | naive (24h persistence) | 718 | 1.11 | 0.84 | -0.726 |
| wind_deg | validation | naive (24h persistence) | 741 | 161.35 | 110.52 | -0.678 |
| wind_deg | test | naive (24h persistence) | 718 | 163.66 | 110.11 | -1.046 |
