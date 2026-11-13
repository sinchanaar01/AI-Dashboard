import numpy as np

import ml.forecasting as forecasting
from data_loader import load_sales_data
from ml.evaluation import calculate_metrics
from ml.forecasting import (
    ForecastResult,
    MODEL_NAMES,
    build_forecast,
    evaluate_weekly_models,
)


def test_calculate_metrics():
    result = calculate_metrics([10, 20, 30], [12, 18, 30])
    assert result["mae"] == 4 / 3
    assert round(result["rmse"], 4) == round(np.sqrt(8 / 3), 4)
    assert result["mape"] > 0


def test_forecast_shape_and_model_comparison():
    data = load_sales_data()
    result = build_forecast(data)
    assert len(result.history) == data["Date"].dt.to_period("M").nunique()
    assert len(result.forecast) == 3
    assert result.model in MODEL_NAMES
    assert len(result.metrics) == len(MODEL_NAMES) == 6
    assert {row["model"] for row in result.metrics} == set(MODEL_NAMES)
    assert sum(row["selected"] for row in result.metrics) == 1
    assert {row["backtestPoints"] for row in result.metrics} == {
        len(result.history) - 18
    }
    assert all(row["mae"] >= 0 and row["rmse"] >= 0 and row["mape"] >= 0 for row in result.metrics)
    assert all(
        {"date", "forecast", "ciLower", "ciUpper"} <= point.keys()
        and point["ciLower"] <= point["forecast"] <= point["ciUpper"]
        for point in result.forecast
    )


def test_ensemble_is_mean_of_seasonal_naive_and_holt_winters(monkeypatch):
    monkeypatch.setattr(forecasting, "_seasonal_naive", lambda _: 10.0)
    monkeypatch.setattr(forecasting, "_holt_winters", lambda _: 14.0)
    assert forecasting._ensemble(np.arange(24, dtype=float)) == 12.0


def test_weekly_models_use_rolling_origin_backtest():
    data = load_sales_data()
    results = evaluate_weekly_models(data)
    expected_points = len(forecasting.weekly_revenue(data)) - forecasting.WEEKLY_MINIMUM_TRAIN_SIZE

    assert {row["model"] for row in results} == {
        "Weekly Seasonal Naive (52)",
        "Weekly Holt-Winters (52)",
    }
    assert {row["backtestPoints"] for row in results} == {expected_points}
    assert all(row["mae"] >= 0 and row["rmse"] >= 0 and row["mape"] >= 0 for row in results)


def test_cached_forecast_is_reused_for_all_horizons_per_dataset(monkeypatch):
    calls = []

    def fake_build(series, horizon):
        calls.append((len(series), horizon))
        return ForecastResult([], [], "test", [])

    forecasting.clear_forecast_cache()
    monkeypatch.setattr(forecasting, "_build_forecast_series", fake_build)
    data = load_sales_data()
    first = forecasting.get_cached_forecast(data, "cache-test-v1")
    same = forecasting.get_cached_forecast(data, "cache-test-v1")
    other_version = forecasting.get_cached_forecast(data, "cache-test-v2")
    assert first is same
    assert len(calls) == 2
    assert calls[0][1] == calls[1][1] == forecasting.MAX_FORECAST_HORIZON
    assert other_version is not first
    forecasting.clear_forecast_cache()
