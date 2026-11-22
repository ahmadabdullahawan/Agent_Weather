# Exploratory Data Analysis — Islamabad

Generated: 2026-11-22T22:53:23.341930+00:00  
Rows: 4944  
Range: 2026-05-01 05:00:00+05:00 to 2026-11-23 04:00:00+05:00 (Asia/Karachi)

Outlier handling: a value outside the physically-plausible range for that metric (see `PHYSICAL_BOUNDS` in `src/eda/run.py`) is treated as a data error, not an extreme-but-real observation, and is reported separately from IQR-based statistical outliers (which ARE kept — e.g. an unusually hot day is a real outlier, not an error).


## AQI (`aqi`)

AQI ranged from 58.00 to 210.00 AQI (US EPA scale) across 4944 valid hours (mean 115.70, std 29.98). AQI sits in the "Unhealthy for Sensitive Groups" band 46% of the time — Islamabad's air quality is unhealthy on a typical hour in this dataset, not just on occasional bad days. On an average day it peaks around 18:00 and is lowest around 07:00 local time. It shows no strong month-to-month trend over the collected period (correlation with month: 0.06). 5 statistically unusual-but-physically-valid hours were kept as real outliers (e.g. an unusually hot day or a rain burst), not scrubbed.

**Status: closed, pending AQI validation, not yet fully closed.** The live and backfill `aqi` values were cross-checked on ~4,943 hours and found to disagree on 74% of them when computed by two different methods. The live pipeline was changed to read AQI from the same source (Open-Meteo) used for backfill, which avoids computing it two different ways — but that is a design decision, not proof the live and archive values actually agree for the same hour; that proof isn't possible until Open-Meteo's archive catches up (~1-day lag) and will be re-checked then. AQICN's raw reading was also checked and is not usable for this city (no active Islamabad station). Full detail: `reports/aqi_validation.md`.

- **Observed range:** 58.00 to 210.00 AQI (US EPA scale), mean 115.70, std 29.98
- **IQR outliers (kept as real):** 5
- Time series: `reports/figures/aqi_timeseries.png`
- Daily/seasonal pattern: `reports/figures/aqi_daily_seasonal.png`

## Temperature (`temperature_c`)

Temperature ranged from 10.80 to 41.70 °C across 4944 valid hours (mean 26.56, std 5.47). Temperature follows a clear seasonal arc — hottest around month 6 and coldest around month 11 in the data collected so far, with a consistent daily rise-and-fall on top of that seasonal trend. On an average day it peaks around 14:00 and is lowest around 04:00 local time. It clearly falls moving later into the year (correlation with month: -0.61). 26 statistically unusual-but-physically-valid hours were kept as real outliers (e.g. an unusually hot day or a rain burst), not scrubbed.

- **Observed range:** 10.80 to 41.70 °C, mean 26.56, std 5.47
- **IQR outliers (kept as real):** 26
- Time series: `reports/figures/temperature_c_timeseries.png`
- Daily/seasonal pattern: `reports/figures/temperature_c_daily_seasonal.png`

## Rain amount (`rain_mm`)

Rain amount ranged from 0.00 to 10.70 mm/h across 4944 valid hours (mean 0.12, std 0.55). Rain is near zero 85% of the time, with occasional heavier spikes up to 10.7 mm/h — a typical hour is dry, but bursts do happen. On an average day it peaks around 02:00 and is lowest around 21:00 local time. It shows no strong month-to-month trend over the collected period (correlation with month: 0.01). 746 statistically unusual-but-physically-valid hours were kept as real outliers (e.g. an unusually hot day or a rain burst), not scrubbed.

- **Observed range:** 0.00 to 10.70 mm/h, mean 0.12, std 0.55
- **IQR outliers (kept as real):** 746
- Time series: `reports/figures/rain_mm_timeseries.png`
- Daily/seasonal pattern: `reports/figures/rain_mm_daily_seasonal.png`

## Rain probability (`rain_probability_pct`)

Rain probability is missing from 100.0% of rows — Open-Meteo's historical archive doesn't record it, so only the 1 hour(s) collected by live ingestion so far have a real value (0.00 to 0.00 %). Too few hours yet for a meaningful daily or seasonal pattern — that will become possible once more live hours accumulate.

- **Missing:** 100.0% of rows
- **Observed range:** 0.00 to 0.00 %, mean 0.00, std nan
- **IQR outliers (kept as real):** 0
- Time series: `reports/figures/rain_probability_pct_timeseries.png`
- Daily/seasonal pattern: `reports/figures/rain_probability_pct_daily_seasonal.png`

## Humidity (`humidity_pct`)

Humidity ranged from 9.00 to 100.00 % across 4944 valid hours (mean 61.66, std 20.33). Humidity swings widely (from 9% to 100%) and moves opposite to temperature, as expected physically. On an average day it peaks around 06:00 and is lowest around 14:00 local time. It shows a mild upward drift across the collected months (correlation with month: 0.37).

- **Observed range:** 9.00 to 100.00 %, mean 61.66, std 20.33
- **IQR outliers (kept as real):** 0
- Time series: `reports/figures/humidity_pct_timeseries.png`
- Daily/seasonal pattern: `reports/figures/humidity_pct_daily_seasonal.png`

## UV Index (`uv_index`)

UV Index is missing from 100.0% of rows — Open-Meteo's historical archive doesn't record it, so only the 1 hour(s) collected by live ingestion so far have a real value (2.98 to 2.98 index). Too few hours yet for a meaningful daily or seasonal pattern — that will become possible once more live hours accumulate.

- **Missing:** 100.0% of rows
- **Observed range:** 2.98 to 2.98 index, mean 2.98, std nan
- **IQR outliers (kept as real):** 0
- Time series: `reports/figures/uv_index_timeseries.png`
- Daily/seasonal pattern: `reports/figures/uv_index_daily_seasonal.png`

## Wind speed (`wind_speed_ms`)

Wind speed ranged from 0.06 to 6.56 m/s across 4944 valid hours (mean 1.66, std 0.93). Wind is generally calm — the mean of 1.7 m/s is light breeze at most, with only occasional stronger gusts. On an average day it peaks around 17:00 and is lowest around 08:00 local time. It shows a mild downward drift across the collected months (correlation with month: -0.23). 109 statistically unusual-but-physically-valid hours were kept as real outliers (e.g. an unusually hot day or a rain burst), not scrubbed.

- **Observed range:** 0.06 to 6.56 m/s, mean 1.66, std 0.93
- **IQR outliers (kept as real):** 109
- Time series: `reports/figures/wind_speed_ms_timeseries.png`
- Daily/seasonal pattern: `reports/figures/wind_speed_ms_daily_seasonal.png`

## Wind direction (`wind_deg`)

Wind direction ranged from 1.00 to 360.00 degrees across 4944 valid hours (mean 169.92, std 114.41). Wind direction is circular data (0° and 360° are the same direction), so the mean/std/outlier statistics above should be read cautiously — they're computed linearly and can be misleading near the 0°/360° wrap-around. On an average day it peaks around 15:00 and is lowest around 00:00 local time. It shows a mild upward drift across the collected months (correlation with month: 0.21).

- **Observed range:** 1.00 to 360.00 degrees, mean 169.92, std 114.41
- **IQR outliers (kept as real):** 0
- Time series: `reports/figures/wind_deg_timeseries.png`
- Daily/seasonal pattern: `reports/figures/wind_deg_daily_seasonal.png`

## Correlations
- Heatmap: `reports/figures/correlation_heatmap.png`
