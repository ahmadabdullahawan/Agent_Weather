"""Phase 4: builds and compares the naive baseline against one model
from each required family -- SARIMAX (statistical), Random Forest
(classical ML), and an LSTM (deep learning) -- for every metric except
AQI, which stays out until Phase 3's AQI validation closes (see
src/training/data.py::METRICS_FOR_TRAINING and plan.md's Phase 3
status note).

`rain_probability_pct` and `uv_index` are skipped entirely for the
three model families (not the baseline) -- Open-Meteo's historical
archive has no data for either (see README), so train has essentially
no real observations to fit on yet; src/training/data.py::
trainable_metrics() enforces this.

Run with (from the project root):
    uv run python -m src.training.run
"""

from datetime import datetime, timezone

from dotenv import load_dotenv

from src.training import lstm_model, random_forest, sarimax_model
from src.training.baseline import naive_predictions
from src.training.data import METRICS_FOR_TRAINING, add_targets, load_features, trainable_metrics
from src.training.features import build_full_matrix
from src.training.metrics import regression_metrics
from src.training.split import split_bounds, time_based_split

REPORT_PATH = "reports/model_comparison.md"

APPROACH_NOTE = (
    "**Model choices (plan.md task 4 -- one model per metric, per family):**\n"
    "- Statistical: SARIMAX, not Prophet -- same seasonal-ARIMA capability without "
    "Prophet's heavier cmdstan/pystan install on Windows.\n"
    "- Classical ML: Random Forest, not Ridge -- the EDA (`reports/eda.md`) shows "
    "clearly non-linear, seasonal relationships that Random Forest captures natively; "
    "it's also what Phase 4 task 6's SHAP step is built around.\n"
    "- Deep learning: an LSTM over a 48h lookback window of the engineered features.\n"
    "- One model per metric in every family, not one shared model across all six -- "
    "each metric's relationship to the shared features differs enough (see "
    "`reports/eda.md`) that a shared model would average that away.\n\n"
    "`wind_deg` is circular data (0 degrees and 360 degrees are the same direction), so "
    "RMSE/MAE/R2 on it -- for every model here, not just the baseline -- should be read "
    "cautiously; the EDA flags the same caveat.\n"
)


def _fmt(value, decimals=2) -> str:
    return f"{value:.{decimals}f}" if value is not None else "n/a"


def run() -> None:
    df = add_targets(load_features())
    train, val, test = time_based_split(df)
    train_end, val_end = split_bounds(len(df))
    usable_metrics = trainable_metrics(train)
    skipped_metrics = [m for m in METRICS_FOR_TRAINING if m not in usable_metrics]

    lines = ["# Model comparison\n"]
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
    lines.append(
        "Split: time-based, never shuffled -- oldest 70% train "
        f"({len(train)} rows), next 15% validation ({len(val)} rows), "
        f"newest 15% test ({len(test)} rows).\n"
    )
    lines.append(
        "**AQI is excluded.** Phase 3's AQI validation hasn't fully closed yet -- see "
        "`plan.md`'s Phase 3 status note and `reports/aqi_validation.md`. It will be "
        "added back once that closes.\n"
    )
    if skipped_metrics:
        lines.append(
            f"**SARIMAX/Random Forest/LSTM skipped for: {', '.join(skipped_metrics)}** "
            "(naive baseline still shown). Open-Meteo's historical archive has no data "
            "for these at all (see README); real values only exist for the handful of "
            "hours live ingestion has collected so far -- not enough to fit anything.\n"
        )
    lines.append(APPROACH_NOTE)

    print("Building shared feature matrix...", flush=True)
    X_full = build_full_matrix(df, train_end)
    X_train, X_val, X_test = X_full[:train_end], X_full[train_end:val_end], X_full[val_end:]

    lines.append("| Metric | Split | Model | n | RMSE | MAE | R2 |")
    lines.append("|---|---|---|---|---|---|---|")

    for metric in METRICS_FOR_TRAINING:
        target_col = f"{metric}_target_24h"
        y_full = df[target_col].to_numpy(dtype=float)
        y_val_arr, y_test_arr = y_full[train_end:val_end], y_full[val_end:]
        y_train_arr = y_full[:train_end]

        preds_by_model = {
            "naive (24h persistence)": {
                "validation": naive_predictions(val, metric).to_numpy(dtype=float),
                "test": naive_predictions(test, metric).to_numpy(dtype=float),
            }
        }

        if metric in usable_metrics:
            print(f"[{metric}] fitting SARIMAX...", flush=True)
            sarimax_fitted = sarimax_model.fit(train[metric])
            sarimax_future = sarimax_model.rolling_forecast_24h(sarimax_fitted, df[metric].iloc[train_end:])
            preds_by_model["SARIMAX"] = {
                "validation": sarimax_future[: len(val)],
                "test": sarimax_future[len(val) :],
            }

            print(f"[{metric}] fitting Random Forest...", flush=True)
            rf_model = random_forest.fit(X_train, y_train_arr)
            preds_by_model["Random Forest"] = {
                "validation": random_forest.predict(rf_model, X_val),
                "test": random_forest.predict(rf_model, X_test),
            }

            print(f"[{metric}] fitting LSTM...", flush=True)
            lstm_bundle = lstm_model.fit(X_train, y_train_arr)
            lstm_full_preds = lstm_model.predict(lstm_bundle, X_full)
            preds_by_model["LSTM"] = {
                "validation": lstm_full_preds[train_end:val_end],
                "test": lstm_full_preds[val_end:],
            }
        else:
            for model_name in ("SARIMAX", "Random Forest", "LSTM"):
                preds_by_model[model_name] = {"validation": None, "test": None}

        for model_name, by_split in preds_by_model.items():
            for split_name, y_true in [("validation", y_val_arr), ("test", y_test_arr)]:
                y_pred = by_split[split_name]
                if y_pred is None:
                    lines.append(f"| {metric} | {split_name} | {model_name} | 0 | n/a | n/a | n/a |")
                    continue
                m = regression_metrics(y_true, y_pred)
                lines.append(
                    f"| {metric} | {split_name} | {model_name} | {m['n']} | "
                    f"{_fmt(m['rmse'])} | {_fmt(m['mae'])} | {_fmt(m['r2'], 3)} |"
                )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Model comparison written to {REPORT_PATH}")


if __name__ == "__main__":
    load_dotenv()
    run()
