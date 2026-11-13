from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import RLock
from uuid import uuid4

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("Date", "Product", "Category", "Region", "Units", "Revenue")
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sales_data.csv"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

_dataset_lock = RLock()
_active_dataset: pd.DataFrame | None = None
_active_dataset_version: str | None = None


def validate_sales_data(frame: pd.DataFrame) -> pd.DataFrame:
    missing = set(REQUIRED_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Sales dataset is missing required columns: {', '.join(sorted(missing))}")
    if frame.empty:
        raise ValueError("Sales dataset contains no rows.")

    df = frame.loc[:, REQUIRED_COLUMNS].copy()
    if "Sub-Category" in frame.columns:
        df["Sub-Category"] = frame["Sub-Category"].astype("string").str.strip()
    else:
        df["Sub-Category"] = "Unspecified"
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for column in ("Product", "Category", "Region"):
        df[column] = df[column].astype("string").str.strip()
    df["Sub-Category"] = df["Sub-Category"].astype("string").str.strip()
    df["Units"] = pd.to_numeric(df["Units"], errors="coerce")
    df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce")

    invalid_rows = df[list(REQUIRED_COLUMNS)].isna().any(axis=1)
    for column in ("Product", "Category", "Region", "Sub-Category"):
        invalid_rows |= df[column].eq("")
    if invalid_rows.any():
        raise ValueError(
            f"Sales dataset contains {int(invalid_rows.sum())} invalid date, text, or numeric rows."
        )
    if not np.isfinite(df[["Units", "Revenue"]].to_numpy(dtype=float)).all():
        raise ValueError("Sales dataset contains non-finite unit or revenue values.")
    if (df[["Units", "Revenue"]] < 0).any().any():
        raise ValueError("Sales dataset cannot contain negative units or revenue.")
    return df.reset_index(drop=True)


@lru_cache(maxsize=4)
def _read_sales_data(modified_ns: int, file_size: int) -> pd.DataFrame:
    del modified_ns, file_size
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Sales dataset not found at {DATA_PATH}. "
            "Add data/sales_data.csv or run backend/import_superstore.py."
        )
    try:
        raw = pd.read_csv(DATA_PATH, parse_dates=["Date"])
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise ValueError(f"Unable to read sales dataset at {DATA_PATH}: {exc}") from exc
    return validate_sales_data(raw)


def get_sales_data_snapshot() -> tuple[pd.DataFrame, str]:
    with _dataset_lock:
        if _active_dataset is not None and _active_dataset_version is not None:
            return _active_dataset.copy(), _active_dataset_version

    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Sales dataset not found at {DATA_PATH}. "
            "Add data/sales_data.csv or run backend/import_superstore.py."
        )
    stat = DATA_PATH.stat()
    version = f"default:{stat.st_mtime_ns}:{stat.st_size}"
    return _read_sales_data(stat.st_mtime_ns, stat.st_size).copy(), version


def load_sales_data() -> pd.DataFrame:
    """Return a validated copy of the active dataset or bundled default."""
    return get_sales_data_snapshot()[0]


def validate_uploaded_csv(contents: bytes) -> pd.DataFrame:
    if not contents:
        raise ValueError("Uploaded CSV is empty.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise ValueError(f"CSV exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.")
    try:
        frame = pd.read_csv(BytesIO(contents))
    except (UnicodeDecodeError, ValueError, pd.errors.ParserError) as exc:
        raise ValueError(f"Unable to parse uploaded CSV: {exc}") from exc
    return validate_sales_data(frame)


def install_uploaded_dataset(frame: pd.DataFrame) -> str:
    global _active_dataset, _active_dataset_version
    validated = validate_sales_data(frame)
    version = f"upload:{uuid4().hex}"
    with _dataset_lock:
        _active_dataset = validated
        _active_dataset_version = version
    return version


def reset_to_default_dataset() -> None:
    global _active_dataset, _active_dataset_version
    with _dataset_lock:
        _active_dataset = None
        _active_dataset_version = None
    _read_sales_data.cache_clear()


def clear_sales_data_cache() -> None:
    _read_sales_data.cache_clear()
