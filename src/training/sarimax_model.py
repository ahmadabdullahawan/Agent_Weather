"""Statistical family: SARIMAX (chosen over Prophet -- same seasonal-ARIMA
capability, without Prophet's heavier cmdstan/pystan install, which is
awkward on Windows). One model per metric (plan.md task 4): each metric
has a different seasonal shape and variance (see reports/eda.md), so a
single shared model would average that away.

Fits order=(1,1,1), seasonal_order=(0,1,1,24) -- a daily-seasonal
"airline model" -- on the metric's own hourly series, train only.
Validation/test predictions are a genuine rolling-origin 24h-ahead
forecast: each hour's *own* actual value is appended to the fitted
state (no refit -- same parameters, a cheap Kalman update) before
forecasting 24 steps ahead, so the prediction for hour t uses exactly
the information available at t, same as the naive baseline.
"""

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

ORDER = (1, 1, 1)
SEASONAL_ORDER = (0, 1, 1, 24)


def fit(train_series: pd.Series):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = SARIMAX(
            train_series.to_numpy(dtype=float),
            order=ORDER,
            seasonal_order=SEASONAL_ORDER,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        return model.fit(disp=False)


def rolling_forecast_24h(fitted, future_series: pd.Series) -> np.ndarray:
    """`future_series` must be the chronologically continuous series
    immediately following the one `fitted` was trained on (val+test
    concatenated). Returns one 24h-ahead prediction per row."""
    preds = np.empty(len(future_series))
    results = fitted
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i, value in enumerate(future_series.to_numpy(dtype=float)):
            results = results.append([value], refit=False)
            preds[i] = results.get_forecast(steps=24).predicted_mean[-1]
    return preds
