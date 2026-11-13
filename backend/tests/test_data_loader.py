import pandas as pd
import pytest

import data_loader


def test_loads_valid_daily_sales_data():
    data_loader.clear_sales_data_cache()
    frame = data_loader.load_sales_data()
    assert set(data_loader.REQUIRED_COLUMNS).issubset(frame.columns)
    assert pd.api.types.is_datetime64_any_dtype(frame["Date"])
    assert frame["Date"].nunique() >= 1000
    assert frame["Date"].min() < frame["Date"].max()
    assert frame["Sub-Category"].nunique() == 17
    frame.loc[frame.index[0], "Revenue"] = -1
    assert data_loader.load_sales_data()["Revenue"].min() >= 0


def test_legacy_sales_data_without_subcategory_remains_supported():
    frame = data_loader.load_sales_data().drop(columns="Sub-Category")
    validated = data_loader.validate_sales_data(frame)
    assert validated["Sub-Category"].eq("Unspecified").all()


def test_missing_dataset_has_actionable_error(tmp_path, monkeypatch):
    data_loader.clear_sales_data_cache()
    monkeypatch.setattr(data_loader, "DATA_PATH", tmp_path / "missing.csv")
    with pytest.raises(FileNotFoundError, match="Sales dataset not found"):
        data_loader.load_sales_data()
    data_loader.clear_sales_data_cache()
