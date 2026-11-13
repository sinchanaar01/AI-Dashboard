from fastapi.testclient import TestClient

import main
from data_loader import load_sales_data
import ml.forecasting as forecasting
from ml.forecasting import ForecastResult, MODEL_NAMES

client = TestClient(main.app)


def test_forecast_and_metrics_api_shapes():
    forecast = client.get("/api/forecast")
    metrics = client.get("/api/model-metrics")
    assert forecast.status_code == 200
    assert metrics.status_code == 200
    forecast_data = forecast.json()
    metric_data = metrics.json()
    assert len(forecast_data["history"]) == load_sales_data()["Date"].dt.to_period("M").nunique()
    assert len(forecast_data["forecast"]) == 3
    assert forecast_data["model"] == metric_data["selectedModel"]
    assert len(metric_data["metrics"]) == len(MODEL_NAMES)


def test_summary_returns_month_over_month_growth_and_anomalies():
    response = client.get("/api/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["totalRevenue"] > 0
    assert len(summary["topProducts"]) == 5
    assert summary["topSubCategories"][0]["name"] == "Phones"
    assert summary["topSubCategories"][0]["revenue"] == 330007.05
    assert summary["topRegions"]
    assert summary["monthlyRevenue"]
    assert "anomalies" in summary
    expected_growth = (
        (summary["monthlyRevenue"][-1]["revenue"] / summary["monthlyRevenue"][-2]["revenue"]) - 1
    ) * 100
    assert abs(summary["growthPercent"] - expected_growth) < 0.02
    assert summary["momGrowthPercent"] == summary["growthPercent"]
    year_ago = summary["monthlyRevenue"][-13]["revenue"]
    expected_yoy = (summary["monthlyRevenue"][-1]["revenue"] / year_ago - 1) * 100
    assert abs(summary["yoyGrowthPercent"] - expected_yoy) < 0.02
    assert summary["yearAgoMonthRevenue"] == year_ago


def test_insights_fallback_is_computed_without_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.get("/api/insights")
    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["forecast"]
    assert payload["metrics"]["selectedModel"]
    assert payload["narrative"]
    assert payload["recommendation"]


def test_forecast_horizon_is_validated_and_reuses_cached_fit():
    short = client.get("/api/forecast?horizon=1")
    long = client.get("/api/forecast?horizon=6")
    invalid = client.get("/api/forecast?horizon=7")
    assert short.status_code == long.status_code == 200
    assert len(short.json()["forecast"]) == 1
    assert len(long.json()["forecast"]) == 6
    assert short.json()["model"] == long.json()["model"]
    assert invalid.status_code == 422


def test_chat_uses_query_spec_and_rejects_generated_code(monkeypatch):
    monkeypatch.setattr(main, "_gemini_client", lambda: object())
    monkeypatch.setattr(
        main,
        "_json_response",
        lambda *_: {
            "intent": "answerable",
            "query_spec": {
                "group_by": ["Product"],
                "metric": "Revenue",
                "sort_by": "value",
                "sort_order": "desc",
                "limit": 5,
            },
            "chart_type": "bar",
            "title": "Top products",
        },
    )
    monkeypatch.setattr(main, "_text_response", lambda *_: "The chart shows the leading products.")
    response = client.post("/api/chat", json={"message": "Top products by revenue"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["response_type"] == "chart"
    assert payload["chart"]["type"] == "bar"
    assert len(payload["rows"]) == 5

    monkeypatch.setattr(
        main,
        "_json_response",
        lambda *_: {
            "intent": "answerable",
            "query_spec": {"pandas_code": '__import__("os").system("whoami")'},
        },
    )
    rejected = client.post("/api/chat", json={"message": "Run this code"})
    assert rejected.status_code == 422
    assert "safely interpret" in rejected.json()["detail"]


def test_csv_upload_replaces_dataset_and_reset_clears_forecast_cache(monkeypatch):
    forecasting.clear_forecast_cache()
    monkeypatch.setattr(
        forecasting,
        "_build_forecast_series",
        lambda *_: ForecastResult([], [], "test", []),
    )
    default_data = load_sales_data()
    forecasting.get_cached_forecast(default_data, "before-upload-test")
    assert forecasting._cached_forecast.cache_info().currsize == 1

    csv_text = (
        "Date,Product,Category,Region,Units,Revenue\n"
        "2024-01-01,Upload Product,Test,North,2,20.00\n"
        "2024-02-01,Upload Product,Test,North,3,33.00\n"
    )
    response = client.post(
        "/api/upload",
        files={"file": ("uploaded.csv", csv_text.encode(), "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["rows"] == 2
    assert forecasting._cached_forecast.cache_info().currsize == 0
    assert main._sales_data()["Product"].unique().tolist() == ["Upload Product"]

    invalid_csv = csv_text.replace("2,20.00", "-2,20.00")
    invalid = client.post(
        "/api/upload",
        files={"file": ("invalid.csv", invalid_csv.encode(), "text/csv")},
    )
    assert invalid.status_code == 400
    assert main._sales_data()["Product"].unique().tolist() == ["Upload Product"]

    reset = client.post("/api/upload/reset")
    assert reset.status_code == 200
    assert reset.json()["rows"] == len(default_data)
    assert main._sales_data()["Product"].nunique() > 1
    forecasting.clear_forecast_cache()


def test_upload_requires_csv_extension_and_required_columns():
    wrong_extension = client.post(
        "/api/upload",
        files={"file": ("sales.txt", b"Date,Product\n", "text/plain")},
    )
    assert wrong_extension.status_code == 400
    missing_columns = client.post(
        "/api/upload",
        files={"file": ("sales.csv", b"Date,Product\n2024-01-01,A\n", "text/csv")},
    )
    assert missing_columns.status_code == 400
