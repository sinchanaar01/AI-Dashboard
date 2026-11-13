import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

PRODUCTS = [
    ("Pro Laptop", "Electronics", 1150, 0.62),
    ("Smart Display", "Electronics", 390, 1.10),
    ("Ergonomic Chair", "Furniture", 285, 0.78),
    ("Standing Desk", "Furniture", 620, 0.52),
    ("Wireless Headset", "Accessories", 125, 1.45),
    ("Docking Station", "Accessories", 195, 0.92),
]
REGIONS = [("North", 1.10), ("South", 0.96), ("East", 1.04), ("West", 0.90)]
WEEKDAY_EFFECT = [0.84, 0.93, 1.00, 1.04, 1.11, 1.18, 0.90]
START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 12, 31)
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "sales_data.csv"


def generate_sales_data() -> int:
    random.seed(29041)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    row_count = 0
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Date", "Product", "Category", "Region", "Units", "Revenue"])
        day = START_DATE
        while day <= END_DATE:
            day_number = (day - START_DATE).days
            seasonal = 1 + 0.20 * math.sin(
                2 * math.pi * (day.timetuple().tm_yday - 35) / 365.25
            )
            holiday = 1.0
            if day.month == 11:
                holiday = 1.42 if day.day >= 20 else 1.18
            elif day.month == 12:
                holiday = 1.48 if day.day <= 20 else 1.12
            elif day.month == 8:
                holiday = 1.14
            trend = 1 + 0.00055 * day_number
            weekday = WEEKDAY_EFFECT[day.weekday()]
            promotion = random.uniform(1.12, 1.38) if random.random() < 0.09 else 1.0
            daily_noise = random.lognormvariate(0, 0.09)

            for product, category, price, base_units in PRODUCTS:
                for region, region_factor in REGIONS:
                    average_units = (
                        base_units
                        * region_factor
                        * seasonal
                        * holiday
                        * trend
                        * weekday
                        * promotion
                        * daily_noise
                    )
                    units = max(
                        0,
                        round(random.gauss(average_units, max(0.7, average_units * 0.22))),
                    )
                    unit_price = price * random.uniform(0.94, 1.06)
                    writer.writerow(
                        [
                            day.isoformat(),
                            product,
                            category,
                            region,
                            units,
                            f"{units * unit_price:.2f}",
                        ]
                    )
                    row_count += 1
            day += timedelta(days=1)
    return row_count


if __name__ == "__main__":
    print(f"Generated {generate_sales_data()} rows in {OUTPUT_PATH}")
