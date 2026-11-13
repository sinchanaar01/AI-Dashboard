import numpy as np
import pandas as pd

from ml.forecasting import build_forecast, monthly_revenue


def build_summary(df: pd.DataFrame) -> dict:
    monthly = monthly_revenue(df)
    total_revenue = float(df["Revenue"].sum())
    previous_month = float(monthly.iloc[-2]) if len(monthly) > 1 else 0.0
    latest_month = float(monthly.iloc[-1])
    mom_growth_percent = (
        (latest_month - previous_month) / previous_month * 100
        if previous_month
        else 0.0
    )
    year_ago_revenue = float(monthly.iloc[-13]) if len(monthly) >= 13 else None
    yoy_growth_percent = (
        (latest_month - year_ago_revenue) / year_ago_revenue * 100
        if year_ago_revenue
        else None
    )

    def top_items(column: str, limit: int = 5) -> list[dict]:
        totals = df.groupby(column)["Revenue"].sum().nlargest(limit)
        return [
            {"name": str(name), "revenue": round(float(value), 2)}
            for name, value in totals.items()
        ]

    monthly_values = monthly.to_numpy(dtype=float)
    q1, q3 = np.percentile(monthly_values, [25, 75])
    iqr = q3 - q1
    lower_bound, upper_bound = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    anomalies = [
        {
            "date": timestamp.strftime("%Y-%m"),
            "revenue": round(float(value), 2),
            "kind": "high" if value > upper_bound else "low",
        }
        for timestamp, value in monthly.items()
        if value > upper_bound or value < lower_bound
    ]
    return {
        "totalRevenue": round(total_revenue, 2),
        "growthPercent": round(mom_growth_percent, 2),
        "momGrowthPercent": round(mom_growth_percent, 2),
        "yoyGrowthPercent": round(yoy_growth_percent, 2) if yoy_growth_percent is not None else None,
        "topProducts": top_items("Product"),
        "topSubCategories": top_items("Sub-Category"),
        "topRegions": top_items("Region"),
        "monthlyRevenue": [
            {"date": timestamp.strftime("%Y-%m"), "revenue": round(float(value), 2)}
            for timestamp, value in monthly.items()
        ],
        "revenueByCategory": [
            {"category": str(category), "revenue": round(float(value), 2)}
            for category, value in (
                df.groupby("Category")["Revenue"].sum().sort_values(ascending=False).items()
            )
        ],
        "anomalies": anomalies,
        "latestMonthRevenue": round(latest_month, 2),
        "previousMonthRevenue": round(previous_month, 2),
        "yearAgoMonthRevenue": round(year_ago_revenue, 2) if year_ago_revenue is not None else None,
    }


def build_insight_context(df: pd.DataFrame, forecast=None) -> dict:
    summary = build_summary(df)
    forecast = forecast or build_forecast(df)
    return {
        "growthPercent": summary["growthPercent"],
        "momGrowthPercent": summary["momGrowthPercent"],
        "yoyGrowthPercent": summary["yoyGrowthPercent"],
        "latestMonthRevenue": summary["latestMonthRevenue"],
        "previousMonthRevenue": summary["previousMonthRevenue"],
        "selectedModel": forecast.model,
        "forecast": forecast.forecast,
        "topProduct": summary["topProducts"][0] if summary["topProducts"] else None,
        "topRegion": summary["topRegions"][0] if summary["topRegions"] else None,
        "anomalyCount": len(summary["anomalies"]),
    }
