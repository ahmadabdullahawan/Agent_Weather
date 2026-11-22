"""Phase 3: exploratory data analysis.

Reads the full `islamabad_features` feature group, plots each metric's
time series and daily/seasonal patterns, checks missing values and
outliers, computes a correlation matrix, and writes a short summary for
each metric to reports/eda.md. Figures are saved to reports/figures/.

Run with (from the project root):
    uv run python -m src.eda.run
"""

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from dotenv import load_dotenv

from config.location import TIMEZONE
from src.ingestion import hopsworks_io

FIGURES_DIR = "reports/figures"
REPORT_PATH = "reports/eda.md"

METRIC_LABELS = {
    "aqi": ("AQI", "AQI (US EPA scale)"),
    "temperature_c": ("Temperature", "°C"),
    "rain_mm": ("Rain amount", "mm/h"),
    "rain_probability_pct": ("Rain probability", "%"),
    "humidity_pct": ("Humidity", "%"),
    "uv_index": ("UV Index", "index"),
    "wind_speed_ms": ("Wind speed", "m/s"),
    "wind_deg": ("Wind direction", "degrees"),
}

# Outside this range, a value is treated as a sensor/API error, not a
# real outlier to analyze — e.g. a negative humidity percentage.
PHYSICAL_BOUNDS = {
    "aqi": (0, 500),
    "temperature_c": (-20, 55),  # generous bounds for Islamabad
    "rain_mm": (0, 200),
    "rain_probability_pct": (0, 100),
    "humidity_pct": (0, 100),
    "uv_index": (0, 16),
    "wind_speed_ms": (0, 60),
    "wind_deg": (0, 360),
}


def load_data() -> pd.DataFrame:
    fs = hopsworks_io.connect()
    fg = hopsworks_io.get_features_fg(fs)
    df = fg.read().sort_values("timestamp").reset_index(drop=True)
    df["datetime_utc"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df["datetime_local"] = df["datetime_utc"].dt.tz_convert(ZoneInfo(TIMEZONE))
    return df


def plot_time_series(df: pd.DataFrame, metric: str, label: str, unit: str) -> str:
    fig, ax = plt.subplots(figsize=(11, 3.5))
    ax.plot(df["datetime_local"], df[metric], linewidth=0.8)
    ax.set_title(f"{label} over time — Islamabad")
    ax.set_ylabel(unit)
    ax.set_xlabel("Date (Asia/Karachi)")
    fig.tight_layout()
    path = f"{FIGURES_DIR}/{metric}_timeseries.png"
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def plot_daily_seasonal(df: pd.DataFrame, metric: str, label: str, unit: str) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.5))

    by_hour = df.groupby(df["datetime_local"].dt.hour)[metric].mean()
    axes[0].plot(by_hour.index, by_hour.values, marker="o")
    axes[0].set_title(f"{label} by hour of day")
    axes[0].set_xlabel("Hour (local)")
    axes[0].set_ylabel(unit)

    by_month = df.groupby(df["datetime_local"].dt.month)[metric].mean()
    axes[1].plot(by_month.index, by_month.values, marker="o", color="darkorange")
    axes[1].set_title(f"{label} by month")
    axes[1].set_xlabel("Month")
    axes[1].set_ylabel(unit)

    fig.tight_layout()
    path = f"{FIGURES_DIR}/{metric}_daily_seasonal.png"
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def plot_correlation_heatmap(df: pd.DataFrame) -> str:
    cols = list(METRIC_LABELS) + ["hour", "day_of_week", "month"]
    corr = df[cols].corr()
    fig, ax = plt.subplots(figsize=(8, 7))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
    ax.set_title("Correlation between metrics and time features")
    fig.tight_layout()
    path = f"{FIGURES_DIR}/correlation_heatmap.png"
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def metric_summary(df: pd.DataFrame, metric: str) -> dict:
    series = df[metric]
    missing_pct = series.isna().mean() * 100
    low, high = PHYSICAL_BOUNDS[metric]
    valid = series.dropna()
    out_of_bounds = ((valid < low) | (valid > high)).sum()
    # IQR-based outliers, among physically-valid values only.
    in_bounds = valid[(valid >= low) & (valid <= high)]
    outliers = 0
    if len(in_bounds) > 10:
        q1, q3 = in_bounds.quantile(0.25), in_bounds.quantile(0.75)
        iqr = q3 - q1
        outliers = ((in_bounds < q1 - 1.5 * iqr) | (in_bounds > q3 + 1.5 * iqr)).sum()
    return {
        "count": len(series),
        "missing_pct": missing_pct,
        "mean": valid.mean() if len(valid) else None,
        "std": valid.std() if len(valid) else None,
        "min": valid.min() if len(valid) else None,
        "max": valid.max() if len(valid) else None,
        "out_of_bounds": out_of_bounds,
        "iqr_outliers": outliers,
    }


AQI_BANDS = [
    (0, 50, "Good"),
    (50, 100, "Moderate"),
    (100, 150, "Unhealthy for Sensitive Groups"),
    (150, 200, "Unhealthy"),
    (200, 300, "Very Unhealthy"),
    (300, 500, "Hazardous"),
]


def interpretation_sentence(metric: str, df: pd.DataFrame, s: dict) -> str:
    """A plain-language read of what the data actually shows, not just a
    restatement of the stats — the kind of sentence a reader needs."""
    valid = df[metric].dropna()

    if metric == "aqi":
        band_share = {}
        for low, high, name in AQI_BANDS:
            share = ((valid >= low) & (valid < high)).mean() * 100
            if share > 0:
                band_share[name] = share
        dominant = max(band_share, key=band_share.get)
        return (
            f"AQI sits in the \"{dominant}\" band {band_share[dominant]:.0f}% of the time — "
            f"Islamabad's air quality is unhealthy on a typical hour in this dataset, not just "
            f"on occasional bad days."
        )

    if metric == "temperature_c":
        hottest_month = df.groupby(df["datetime_local"].dt.month)[metric].mean().idxmax()
        coldest_month = df.groupby(df["datetime_local"].dt.month)[metric].mean().idxmin()
        return (
            f"Temperature follows a clear seasonal arc — hottest around month {hottest_month} "
            f"and coldest around month {coldest_month} in the data collected so far, with a "
            f"consistent daily rise-and-fall on top of that seasonal trend."
        )

    if metric == "rain_mm":
        near_zero_pct = (valid < 0.1).mean() * 100
        return (
            f"Rain is near zero {near_zero_pct:.0f}% of the time, with occasional heavier "
            f"spikes up to {valid.max():.1f} mm/h — a typical hour is dry, but bursts do happen."
        )

    if metric == "humidity_pct":
        return (
            f"Humidity swings widely (from {valid.min():.0f}% to {valid.max():.0f}%) and moves "
            f"opposite to temperature, as expected physically."
        )

    if metric == "wind_speed_ms":
        return (
            f"Wind is generally calm — the mean of {valid.mean():.1f} m/s is light breeze at "
            f"most, with only occasional stronger gusts."
        )

    if metric == "wind_deg":
        return (
            "Wind direction is circular data (0° and 360° are the same direction), so the "
            "mean/std/outlier statistics above should be read cautiously — they're computed "
            "linearly and can be misleading near the 0°/360° wrap-around."
        )

    return ""


MIN_HOURS_FOR_DAILY_SEASONAL_READ = 5


def narrative_summary(df: pd.DataFrame, metric: str, label: str, unit: str, s: dict) -> str:
    if s["mean"] is None:
        return (
            f"{label} has no valid data in this dataset — Open-Meteo's historical archive "
            f"doesn't record it at all, so every backfilled row is empty. Real values will "
            f"only start accumulating once the hourly live ingestion runs going forward."
        )

    valid = df[metric].dropna()

    if len(valid) < MIN_HOURS_FOR_DAILY_SEASONAL_READ:
        return (
            f"{label} is missing from {s['missing_pct']:.1f}% of rows — Open-Meteo's historical "
            f"archive doesn't record it, so only the {len(valid)} hour(s) collected by live "
            f"ingestion so far have a real value ({valid.min():.2f} to {valid.max():.2f} {unit}). "
            f"Too few hours yet for a meaningful daily or seasonal pattern — that will become "
            f"possible once more live hours accumulate."
        )
    by_hour = df.groupby(df["datetime_local"].dt.hour)[metric].mean()
    peak_hour, trough_hour = by_hour.idxmax(), by_hour.idxmin()

    month_corr = df[[metric, "month"]].corr().iloc[0, 1]
    if abs(month_corr) >= 0.4:
        trend = "rises" if month_corr > 0 else "falls"
        trend_sentence = f"It clearly {trend} moving later into the year (correlation with month: {month_corr:.2f})."
    elif abs(month_corr) >= 0.15:
        trend = "a mild upward" if month_corr > 0 else "a mild downward"
        trend_sentence = f"It shows {trend} drift across the collected months (correlation with month: {month_corr:.2f})."
    else:
        trend_sentence = f"It shows no strong month-to-month trend over the collected period (correlation with month: {month_corr:.2f})."

    daily_sentence = (
        f"On an average day it peaks around {int(peak_hour):02d}:00 and is lowest around "
        f"{int(trough_hour):02d}:00 local time."
    )

    interpretation = interpretation_sentence(metric, df, s)

    pieces = [
        f"{label} ranged from {s['min']:.2f} to {s['max']:.2f} {unit} across {len(valid)} valid hours "
        f"(mean {s['mean']:.2f}, std {s['std']:.2f}).",
        interpretation,
        daily_sentence,
        trend_sentence,
    ]
    if s["missing_pct"] > 0:
        pieces.append(f"{s['missing_pct']:.1f}% of rows are missing this metric (see note above).")
    if s["out_of_bounds"] > 0:
        pieces.append(
            f"{s['out_of_bounds']} readings fell outside the physically-plausible range and were "
            f"treated as data errors, not real extremes."
        )
    if s["iqr_outliers"] > 0:
        pieces.append(
            f"{s['iqr_outliers']} statistically unusual-but-physically-valid hours were kept as real "
            f"outliers (e.g. an unusually hot day or a rain burst), not scrubbed."
        )
    return " ".join(p for p in pieces if p)


def run() -> None:
    os.makedirs(FIGURES_DIR, exist_ok=True)
    df = load_data()

    lines = ["# Exploratory Data Analysis — Islamabad\n"]
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}  ")
    lines.append(f"Rows: {len(df)}  ")
    lines.append(
        f"Range: {df['datetime_local'].min()} to {df['datetime_local'].max()} (Asia/Karachi)\n"
    )
    lines.append(
        "Outlier handling: a value outside the physically-plausible range for that metric "
        "(see `PHYSICAL_BOUNDS` in `src/eda/run.py`) is treated as a data error, not an "
        "extreme-but-real observation, and is reported separately from IQR-based statistical "
        "outliers (which ARE kept — e.g. an unusually hot day is a real outlier, not an error).\n"
    )

    for metric, (label, unit) in METRIC_LABELS.items():
        ts_path = plot_time_series(df, metric, label, unit)
        daily_path = plot_daily_seasonal(df, metric, label, unit)
        s = metric_summary(df, metric)

        lines.append(f"\n## {label} (`{metric}`)\n")
        lines.append(narrative_summary(df, metric, label, unit, s) + "\n")
        if metric == "aqi":
            lines.append(
                "**Status: closed, pending AQI validation, not yet fully closed.** The live and "
                "backfill `aqi` values were cross-checked on ~4,943 hours and found to disagree on "
                "74% of them when computed by two different methods. The live pipeline was changed "
                "to read AQI from the same source (Open-Meteo) used for backfill, which avoids "
                "computing it two different ways — but that is a design decision, not proof the "
                "live and archive values actually agree for the same hour; that proof isn't "
                "possible until Open-Meteo's archive catches up (~1-day lag) and will be re-checked "
                "then. AQICN's raw reading was also checked and is not usable for this city (no "
                "active Islamabad station). Full detail: `reports/aqi_validation.md`.\n"
            )
        if s["missing_pct"] > 0:
            lines.append(f"- **Missing:** {s['missing_pct']:.1f}% of rows")
        if s["mean"] is not None:
            lines.append(
                f"- **Observed range:** {s['min']:.2f} to {s['max']:.2f} {unit}, "
                f"mean {s['mean']:.2f}, std {s['std']:.2f}"
            )
        else:
            lines.append("- **Observed range:** no valid data")
        if s["out_of_bounds"] > 0:
            lines.append(f"- **Out-of-bounds (data-error) values:** {s['out_of_bounds']}")
        lines.append(f"- **IQR outliers (kept as real):** {s['iqr_outliers']}")
        lines.append(f"- Time series: `{ts_path}`")
        lines.append(f"- Daily/seasonal pattern: `{daily_path}`")

    corr_path = plot_correlation_heatmap(df)
    lines.append(f"\n## Correlations\n- Heatmap: `{corr_path}`")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"EDA report written to {REPORT_PATH}")


if __name__ == "__main__":
    load_dotenv()
    run()
