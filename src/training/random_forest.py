"""Classical-ML family: Random Forest (chosen over Ridge). The EDA
(reports/eda.md) shows clearly non-linear, seasonal relationships
between each metric and the time/lag/rolling features -- Random Forest
captures that natively, where Ridge would need manual interaction and
seasonality terms to compete. It's also the model Phase 4 task 6's
SHAP explainability step is built around (SHAP's TreeExplainer is
exact and fast for tree ensembles).

One model per metric, same reasoning as sarimax_model.py.
"""

import numpy as np
from sklearn.ensemble import RandomForestRegressor

N_ESTIMATORS = 200
RANDOM_STATE = 0


def fit(X_train: np.ndarray, y_train: np.ndarray):
    mask = ~np.isnan(y_train)
    if mask.sum() == 0:
        return None
    model = RandomForestRegressor(n_estimators=N_ESTIMATORS, random_state=RANDOM_STATE, n_jobs=-1)
    model.fit(X_train[mask], y_train[mask])
    return model


def predict(model, X: np.ndarray) -> np.ndarray:
    if model is None:
        return np.full(len(X), np.nan)
    return model.predict(X)
