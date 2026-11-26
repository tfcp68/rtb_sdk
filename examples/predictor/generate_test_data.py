"""
Generates test files for full_cycle_core_and_file_loaders.py
"""
import csv
import json
import math
import os
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'test_data')
os.makedirs(DATA_DIR, exist_ok=True)


def generate_daily_series(start: datetime, num_days: int):
    dates = []
    values = []
    for i in range(num_days):
        dt = start + timedelta(days=i)
        dates.append(dt)
        value = 100 + 20 * math.sin(2 * math.pi * i / 30) + 5 * math.sin(2 * math.pi * i / 7)
        values.append(round(value, 2))
    return dates, values


def main():
    start = datetime(2024, 1, 1)
    total_days = 180
    dates, values = generate_daily_series(start, total_days)

    # --- CSV: train data (first 150 days) ---
    train_path = os.path.join(DATA_DIR, 'train_data.csv')
    with open(train_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['date_from', 'date_to', 'value'])
        for i in range(150):
            dt = dates[i]
            dt_to = dt + timedelta(days=1)
            writer.writerow([
                dt.strftime('%Y-%m-%d %H:%M:%S'),
                dt_to.strftime('%Y-%m-%d %H:%M:%S'),
                values[i]
            ])
    print(f"train CSV: {train_path} ({150} rows)")

    # --- CSV: sample data (last 30 days) ---
    sample_path = os.path.join(DATA_DIR, 'sample_data.csv')
    with open(sample_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['date_from', 'date_to', 'value'])
        for i in range(150, total_days):
            dt = dates[i]
            dt_to = dt + timedelta(days=1)
            writer.writerow([
                dt.strftime('%Y-%m-%d %H:%M:%S'),
                dt_to.strftime('%Y-%m-%d %H:%M:%S'),
                values[i]
            ])
    print(f"sample CSV: {sample_path} ({total_days - 150} rows)")

    # --- JSON: prophet options ---
    options_path = os.path.join(DATA_DIR, 'prophet_options.json')
    options = {
        "growth": "linear",
        "changepoint_prior_scale": 0.05,
        "seasonality_mode": "additive",
        "seasonality_prior_scale": 10.0,
        "yearly_seasonality": False,
        "weekly_seasonality": True,
        "n_changepoints": 10,
        "changepoint_range": 0.8,
        "seasonalities": {
            "monthly": {
                "name": "monthly",
                "period": 30.5,
                "fourier_order": 5
            }
        }
    }
    with open(options_path, 'w', encoding='utf-8') as f:
        json.dump(options, f, indent=2, ensure_ascii=False)
    print(f"options JSON: {options_path}")


if __name__ == '__main__':
    main()