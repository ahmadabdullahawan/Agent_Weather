"""RMSE, MAE, R^2 for scoring forecasts against the 24h-ahead target.

Computed with plain numpy rather than adding scikit-learn as a
dependency this early -- these three formulas don't need it. Rows
where either side is NaN (a target in the newest 24h, or a prediction
missing an input) are dropped before scoring.
"""

import numpy as np


def regression_metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    y_true, y_pred = y_true[mask], y_pred[mask]
    if len(y_true) == 0:
        return {"n": 0, "rmse": None, "mae": None, "r2": None}

    errors = y_true - y_pred
    rmse = float(np.sqrt(np.mean(errors**2)))
    mae = float(np.mean(np.abs(errors)))
    ss_res = np.sum(errors**2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else None
    return {"n": len(y_true), "rmse": rmse, "mae": mae, "r2": r2}
