from data_loader import load_sales_data
from ml.forecasting import build_forecast, evaluate_weekly_models


def main() -> None:
    data = load_sales_data()
    monthly = build_forecast(data)
    results = [
        (
            "Monthly",
            row["model"],
            row["backtestPoints"],
            row["mae"],
            row["rmse"],
            row["mape"],
        )
        for row in monthly.metrics
    ]
    results.extend(
        (
            "Weekly",
            row["model"],
            row["backtestPoints"],
            row["mae"],
            row["rmse"],
            row["mape"],
        )
        for row in evaluate_weekly_models(data)
    )

    print("| Frequency | Model | Rolling-origin points | MAE | RMSE | MAPE (%) |")
    print("|---|---|---:|---:|---:|---:|")
    for frequency, name, points, mae, rmse, mape in results:
        print(f"| {frequency} | {name} | {points} | {mae:.2f} | {rmse:.2f} | {mape:.2f} |")
    print(f"\nSelected monthly model (lowest MAE): **{monthly.model}**")


if __name__ == "__main__":
    main()
