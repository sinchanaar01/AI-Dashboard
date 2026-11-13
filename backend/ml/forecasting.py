from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

from data_loader import get_sales_data_snapshot
from ml.evaluation import rolling_origin_evaluate

MODEL_NAMES = (
    "Seasonal Naive",
    "Holt-Winters",
    "Ensemble",
    "Log Holt-Winters",
    "SARIMA",
    "Gradient Boosting",
)
FORECAST_HORIZON = 3
MAX_FORECAST_HORIZON = 6
WEEKLY_MINIMUM_TRAIN_SIZE = 104


def monthly_revenue(df: pd.DataFrame) -> pd.Series:
    if not {"Date", "Revenue"}.issubset(df.columns):
        raise ValueError("Sales data must include Date and Revenue columns.")
    monthly = (
        df.assign(Date=pd.to_datetime(df["Date"]), Revenue=pd.to_numeric(df["Revenue"]))
        .set_index("Date")["Revenue"]
        .resample("MS")
        .sum()
    )
    if monthly.empty or not np.isfinite(monthly.to_numpy(dtype=float)).all():
        raise ValueError("Monthly revenue series is empty or contains invalid values.")
    return monthly.astype(float)


def weekly_revenue(df: pd.DataFrame) -> pd.Series:
    if not {"Date", "Revenue"}.issubset(df.columns):
        raise ValueError("Sales data must include Date and Revenue columns.")
    weekly = (
        df.assign(Date=pd.to_datetime(df["Date"]), Revenue=pd.to_numeric(df["Revenue"]))
        .set_index("Date")["Revenue"]
        .resample("W-SUN")
        .sum()
    )
    if weekly.empty or not np.isfinite(weekly.to_numpy(dtype=float)).all():
        raise ValueError("Weekly revenue series is empty or contains invalid values.")
    return weekly.astype(float)


def _seasonal_naive(history: np.ndarray) -> float:
    return float(history[-12] if len(history) >= 12 else history[-1])


def _holt_winters(history: np.ndarray) -> float:
    seasonal = "add" if len(history) >= 24 else None
    model = ExponentialSmoothing(
        history,
        trend="add",
        seasonal=seasonal,
        seasonal_periods=12 if seasonal else None,
        initialization_method="estimated",
    )
    fitted = model.fit(optimized=True)
    return float(fitted.forecast(1)[0])


def _ensemble(history: np.ndarray) -> float:
    return (_seasonal_naive(history) + _holt_winters(history)) / 2


def _log_holt_winters(history: np.ndarray) -> float:
    log_history = np.log1p(history)
    seasonal = "add" if len(history) >= 24 else None
    model = ExponentialSmoothing(
        log_history,
        trend="add",
        seasonal=seasonal,
        seasonal_periods=12 if seasonal else None,
        initialization_method="estimated",
    )
    fitted = model.fit(optimized=True)
    return float(np.expm1(fitted.forecast(1)[0]))


def _weekly_seasonal_naive(history: np.ndarray) -> float:
    return float(history[-52] if len(history) >= 52 else history[-1])


def _weekly_holt_winters(history: np.ndarray) -> float:
    fitted = ExponentialSmoothing(
        history,
        trend="add",
        seasonal="add",
        seasonal_periods=52,
        initialization_method="estimated",
    ).fit(optimized=True)
    return float(fitted.forecast(1)[0])


def _sarima(history: np.ndarray) -> float:
    seasonal_order = (1, 0, 0, 12) if len(history) >= 24 else (0, 0, 0, 0)
    fitted = SARIMAX(
        history,
        order=(1, 1, 1),
        seasonal_order=seasonal_order,
        trend="n",
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False, maxiter=50)
    return float(fitted.forecast(1)[0])


def _feature(values: np.ndarray, index: int) -> list[float]:
    month = index % 12 + 1
    return [
        float(index),
        float(values[-1]),
        float(values[-2]) if len(values) >= 2 else float(values[-1]),
        float(values[-3]) if len(values) >= 3 else float(values[-1]),
        float(values[-6]) if len(values) >= 6 else float(values[-1]),
        float(values[-12]) if len(values) >= 12 else float(values[-1]),
        float(np.mean(values[-3:])),
        float(np.mean(values[-12:])),
        float(np.sin(2 * np.pi * month / 12)),
        float(np.cos(2 * np.pi * month / 12)),
    ]


def _gradient_boosting(history: np.ndarray) -> float:
    if len(history) < 14:
        return _seasonal_naive(history)
    features = np.asarray([_feature(history[:i], i) for i in range(12, len(history))])
    target = history[12:]
    model = GradientBoostingRegressor(
        n_estimators=120,
        learning_rate=0.04,
        max_depth=2,
        loss="huber",
        random_state=42,
    )
    model.fit(features, target)
    return float(model.predict([_feature(history, len(history))])[0])


FORECASTERS = {
    MODEL_NAMES[0]: _seasonal_naive,
    MODEL_NAMES[1]: _holt_winters,
    MODEL_NAMES[2]: _ensemble,
    MODEL_NAMES[3]: _log_holt_winters,
    MODEL_NAMES[4]: _sarima,
    MODEL_NAMES[5]: _gradient_boosting,
}


@dataclass
class ForecastResult:
    history: list[dict]
    forecast: list[dict]
    model: str
    metrics: list[dict]


def evaluate_weekly_models(df: pd.DataFrame) -> list[dict]:
    weekly_values = weekly_revenue(df).to_numpy(dtype=float)
    evaluation = rolling_origin_evaluate(
        weekly_values,
        {
            "Weekly Seasonal Naive (52)": _weekly_seasonal_naive,
            "Weekly Holt-Winters (52)": _weekly_holt_winters,
        },
        minimum_train_size=WEEKLY_MINIMUM_TRAIN_SIZE,
    )
    return [
        {
            "model": name,
            "mae": round(result["mae"], 2),
            "rmse": round(result["rmse"], 2),
            "mape": round(result["mape"], 2),
            "backtestPoints": result["backtestPoints"],
        }
        for name, result in sorted(evaluation.items(), key=lambda item: item[1]["mae"])
    ]


def _build_forecast_series(series: pd.Series, horizon: int) -> ForecastResult:
    if not 1 <= horizon <= 6:
        raise ValueError("Forecast horizon must be between 1 and 6 months.")
    if len(series) < 3:
        raise ValueError("At least three months of sales are required to forecast.")
    values = series.to_numpy(dtype=float)

    evaluation = rolling_origin_evaluate(values, FORECASTERS)
    best_model = min(evaluation, key=lambda name: evaluation[name]["mae"])
    residuals = np.asarray(evaluation[best_model]["residuals"], dtype=float)
    residual_std = max(float(np.std(residuals, ddof=1)) if residuals.size > 1 else 0.0, 1.0)

    history = [
        {"date": timestamp.strftime("%Y-%m"), "actual": round(float(value), 2)}
        for timestamp, value in series.items()
    ]
    future_values = values.copy()
    forecast = []
    future_dates = pd.date_range(series.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")
    for step, timestamp in enumerate(future_dates, start=1):
        predicted = max(0.0, float(FORECASTERS[best_model](future_values)))
        margin = 1.96 * residual_std * np.sqrt(step)
        forecast.append(
            {
                "date": timestamp.strftime("%Y-%m"),
                "forecast": round(predicted, 2),
                "ciUpper": round(predicted + margin, 2),
                "ciLower": round(max(0.0, predicted - margin), 2),
            }
        )
        future_values = np.append(future_values, predicted)

    metrics = [
        {
            "model": name,
            "mae": round(result["mae"], 2),
            "rmse": round(result["rmse"], 2),
            "mape": round(result["mape"], 2),
            "backtestPoints": result["backtestPoints"],
            "selected": name == best_model,
        }
        for name, result in sorted(evaluation.items(), key=lambda item: item[1]["mae"])
    ]
    return ForecastResult(history, forecast, best_model, metrics)


def build_forecast(df: pd.DataFrame, horizon: int = FORECAST_HORIZON) -> ForecastResult:
    return _build_forecast_series(monthly_revenue(df), horizon)


@lru_cache(maxsize=12)
def _cached_forecast(
    dataset_version: str,
    dates: tuple[str, ...],
    values: tuple[float, ...],
) -> ForecastResult:
    del dataset_version
    series = pd.Series(values, index=pd.to_datetime(dates), dtype=float)
    return _build_forecast_series(series, MAX_FORECAST_HORIZON)


def get_cached_forecast(
    df: pd.DataFrame,
    dataset_version: str,
) -> ForecastResult:
    series = monthly_revenue(df)
    dates = tuple(timestamp.isoformat() for timestamp in series.index)
    values = tuple(float(value) for value in series.to_numpy(dtype=float))
    return _cached_forecast(dataset_version, dates, values)


def get_active_forecast() -> ForecastResult:
    frame, version = get_sales_data_snapshot()
    return get_cached_forecast(frame, version)


def clear_forecast_cache() -> None:
    _cached_forecast.cache_clear()
