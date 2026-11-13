import numpy as np


def calculate_metrics(actual, predicted):
    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)
    if actual_values.shape != predicted_values.shape or actual_values.size == 0:
        raise ValueError("Actual and predicted values must have the same non-empty shape.")

    errors = actual_values - predicted_values
    nonzero = actual_values != 0
    mape = (
        float(np.mean(np.abs(errors[nonzero] / actual_values[nonzero])) * 100)
        if nonzero.any()
        else 0.0
    )
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(np.square(errors)))),
        "mape": mape,
    }


def rolling_origin_evaluate(series, forecasters, minimum_train_size=18):
    values = np.asarray(series, dtype=float)
    if values.ndim != 1 or values.size <= minimum_train_size:
        raise ValueError(
            f"At least {minimum_train_size + 1} observations are required "
            "for rolling-origin evaluation."
        )
    if not np.isfinite(values).all():
        raise ValueError("Time series must contain only finite values.")

    origins = range(minimum_train_size, values.size)

    results = {}
    for name, predict_next in forecasters.items():
        actuals = []
        predictions = []
        for origin in origins:
            history = values[:origin]
            actuals.append(values[origin])
            predictions.append(float(predict_next(history)))
        metrics = calculate_metrics(actuals, predictions)
        metrics["backtestPoints"] = len(actuals)
        metrics["residuals"] = (np.asarray(actuals) - np.asarray(predictions)).tolist()
        results[name] = metrics
    return results
