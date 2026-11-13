import pytest

from chat_data import execute_query_spec
from data_loader import load_sales_data


def test_grouped_query_aggregates_monthly_revenue_by_region():
    result = execute_query_spec(
        load_sales_data(),
        {"group_by": ["month", "Region"], "metric": "Revenue", "limit": 50},
    )
    assert result["x_key"] == "date"
    assert len(result["y_keys"]) == 4
    assert len(result["data"]) == load_sales_data()["Date"].dt.to_period("M").nunique()
    assert {"date", *result["y_keys"]}.issubset(result["data"][0])


def test_query_filters_and_limits_are_applied():
    result = execute_query_spec(
        load_sales_data(),
        {
            "group_by": ["Product"],
            "metric": "Units",
            "filters": {"Region": "West"},
            "sort_by": "value",
            "sort_order": "desc",
            "limit": 2,
        },
    )
    assert len(result["data"]) == 2
    assert result["data"][0]["value"] >= result["data"][1]["value"]


def test_generated_code_is_rejected():
    with pytest.raises(ValueError, match="Generated code is not accepted"):
        execute_query_spec(
            load_sales_data(),
            {"pandas_code": '__import__("os").system("whoami")'},
        )


def test_unknown_query_fields_are_rejected():
    with pytest.raises(ValueError, match="unsupported fields"):
        execute_query_spec(load_sales_data(), {"query": "select *"})
