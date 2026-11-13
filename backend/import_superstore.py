from pathlib import Path

import pandas as pd

SOURCE_URL = (
    "https://raw.githubusercontent.com/leonism/sample-superstore/master/data/superstore.csv"
)
SOURCE_PATH = Path(__file__).resolve().parent.parent / "data" / "superstore_source.csv"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "sales_data.csv"
SOURCE_COLUMNS = {
    "Order Date": "Date",
    "Product Name": "Product",
    "Category": "Category",
    "Sub-Category": "Sub-Category",
    "Region": "Region",
    "Quantity": "Units",
    "Sales": "Revenue",
}


def import_superstore() -> int:
    source_path = SOURCE_PATH if SOURCE_PATH.is_file() else SOURCE_URL
    source = pd.read_csv(source_path, encoding="latin-1", parse_dates=["Order Date"])
    missing = set(SOURCE_COLUMNS) - set(source.columns)
    if missing:
        raise ValueError(f"Superstore source is missing columns: {', '.join(sorted(missing))}")

    retail = source[list(SOURCE_COLUMNS)].rename(columns=SOURCE_COLUMNS)
    # The source records positive sales orders; omit any returns/invalid lines if present.
    retail["Units"] = pd.to_numeric(retail["Units"], errors="coerce")
    retail["Revenue"] = pd.to_numeric(retail["Revenue"], errors="coerce")
    retail = retail.dropna(subset=list(SOURCE_COLUMNS.values()))
    retail = retail[(retail["Units"] > 0) & (retail["Revenue"] >= 0)]
    retail["Date"] = pd.to_datetime(retail["Date"]).dt.normalize()
    retail["Units"] = retail["Units"].astype(int)
    retail = retail.sort_values("Date").reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    retail.to_csv(OUTPUT_PATH, index=False, date_format="%Y-%m-%d")
    return len(retail)


if __name__ == "__main__":
    print(f"Imported {import_superstore()} public Superstore records to {OUTPUT_PATH}")
