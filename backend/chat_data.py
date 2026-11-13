from datetime import datetime

import pandas as pd

GROUP_FIELDS = {"day", "month", "year", "Product", "Category", "Region"}
CATEGORY_FIELDS = {"Product", "Category", "Region"}
METRICS = {"Revenue", "Units"}


def execute_query_spec(df: pd.DataFrame, spec: dict) -> dict:
    if not isinstance(spec, dict):
        raise ValueError("The AI query must be a JSON object.")
    if "pandas_code" in spec or "code" in spec:
        raise ValueError("Generated code is not accepted; provide a constrained query_spec.")
    allowed_keys = {"group_by", "metric", "filters", "sort_by", "sort_order", "limit"}
    if set(spec) - allowed_keys:
        raise ValueError("The query contains unsupported fields.")

    metric = spec.get("metric", "Revenue")
    if metric not in METRICS:
        raise ValueError(f"Unsupported metric: {metric}.")
    group_by = spec.get("group_by", [])
    if not isinstance(group_by, list) or len(group_by) > 2:
        raise ValueError("group_by must contain at most two supported dimensions.")
    if any(field not in GROUP_FIELDS for field in group_by) or len(set(group_by)) != len(group_by):
        raise ValueError("The query contains an unsupported or repeated group_by field.")

    limit = spec.get("limit", 20)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        raise ValueError("limit must be an integer between 1 and 50.")
    sort_order = spec.get("sort_order", "desc")
    if sort_order not in {"asc", "desc"}:
        raise ValueError("sort_order must be 'asc' or 'desc'.")

    frame = df.copy()
    filters = spec.get("filters", {})
    if not isinstance(filters, dict):
        raise ValueError("filters must be a JSON object.")
    for field, selected in filters.items():
        if field in CATEGORY_FIELDS:
            values = selected if isinstance(selected, list) else [selected]
            if not values or len(values) > 20 or not all(isinstance(value, str) for value in values):
                raise ValueError(f"Filter for {field} must contain one to 20 text values.")
            frame = frame[frame[field].isin(values)]
        elif field in {"date_from", "date_to"}:
            if not isinstance(selected, str):
                raise ValueError(f"{field} must be an ISO date string.")
            try:
                date_value = datetime.fromisoformat(selected)
            except ValueError as exc:
                raise ValueError(f"{field} must be an ISO date string.") from exc
            if field == "date_from":
                frame = frame[frame["Date"] >= date_value]
            else:
                frame = frame[frame["Date"] <= date_value]
        else:
            raise ValueError(f"Unsupported filter field: {field}.")

    if frame.empty:
        return {"data": [], "x_key": "date", "y_keys": [], "metric": metric}

    grouping_fields = []
    for field in group_by:
        if field == "day":
            key = "date"
            frame[key] = frame["Date"].dt.strftime("%Y-%m-%d")
        elif field == "month":
            key = "date"
            frame[key] = frame["Date"].dt.to_period("M").astype(str)
        elif field == "year":
            key = "year"
            frame[key] = frame["Date"].dt.year.astype(str)
        else:
            key = field
        grouping_fields.append(key)

    if not grouping_fields:
        return {
            "data": [{"metric": metric, "value": round(float(frame[metric].sum()), 2)}],
            "x_key": "metric",
            "y_keys": ["value"],
            "metric": metric,
        }

    grouped = frame.groupby(grouping_fields, observed=True)[metric].sum().reset_index(name="value")
    if len(grouping_fields) == 2:
        pivot = grouped.pivot(index="date", columns=grouping_fields[1], values="value").fillna(0)
        pivot = pivot.sort_index()
        if len(pivot.columns) > 8:
            raise ValueError("This chart would contain too many series; filter to eight or fewer.")
        pivot = pivot.head(limit)
        data = [
            {
                "date": str(index),
                **{str(column): round(float(value), 2) for column, value in row.items()},
            }
            for index, row in pivot.iterrows()
        ]
        y_keys = [str(column) for column in pivot.columns]
        x_key = "date"
    else:
        sort_by = spec.get("sort_by", "value")
        if sort_by not in {*grouping_fields, "value"}:
            raise ValueError("sort_by must be one of the grouping fields or value.")
        grouped = grouped.sort_values(
            sort_by,
            ascending=sort_order == "asc",
            kind="stable",
        ).head(limit)
        data = grouped.to_dict(orient="records")
        x_key = grouping_fields[0]
        y_keys = ["value"]

    return {"data": data, "x_key": x_key, "y_keys": y_keys, "metric": metric}
