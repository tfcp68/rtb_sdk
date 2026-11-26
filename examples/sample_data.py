"""Deterministic synthetic inputs shared by the public examples."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
import json
from pathlib import Path
import random


SAMPLE_DIR = Path(__file__).resolve().parent / "generated_samples"
DEVICES = ["WEB_BROWSER_A", "ANDROID_TV_A", "SMART_TV_PLATFORM_B", "SMART_TV_PLATFORM_A",
           "ANDROID_PHONE_A", "ANDROID_TABLET_A"]


def generate_samples(directory: Path = SAMPLE_DIR, *, count: int = 8000) -> Path:
    """Create demo requests, campaigns, vocabularies and temporal CSV logs."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    requests, rows = [], []
    for i in range(count):
        date = datetime(2025, 7, 1) + timedelta(days=rng.randrange(30), seconds=rng.randrange(86400))
        tags = {
            "location": rng.choice(["region_a", "region_b", "region_c"]),
            "device_type": rng.choices(DEVICES, weights=[80, 8, 3, 3, 4, 2])[0],
            "ad_place_type": rng.choice(["preroll", "midroll", "pauseroll"]),
        }
        user = f"demo_user_{i % 1000:04d}"
        requests.append({"id": f"demo_request_{i:05d}", "date": date.isoformat(),
                         "client_id": user, "user_id": user, "tags": tags})
        for repeat in range(3):
            rows.append({"ts": (date + timedelta(seconds=repeat)).isoformat(sep=" "),
                         "user_id": user, **tags})
    ads = [
        {"id": "demo_broad", "volume": 6000, "cpm": 90, "priority": 1, "targets": {}},
        {"id": "demo_web", "volume": 4000, "cpm": 200, "priority": 2,
         "targets": {"device_type": ["WEB_BROWSER_A"]}},
        {"id": "demo_tv", "volume": 2000, "cpm": 300, "priority": 3,
         "targets": {"device_type": ["ANDROID_TV_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B"]}},
    ]
    for ad in ads:
        ad.update(start_date="2025-07-01T00:00:00", end_date="2025-08-01T00:00:00")
    vocabs = {field: sorted({r["tags"][field] for r in requests})
              for field in ("location", "device_type", "ad_place_type")}
    for name, data in (("filtered_requests.json", requests), ("filtered_ads.json", ads), ("vocab.json", vocabs)):
        (directory / name).write_text(json.dumps(data, indent=2), encoding="utf-8")
    with (directory / "logs.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["ts", "user_id", "location", "device_type", "ad_place_type"])
        writer.writeheader()
        writer.writerows(rows)
    return directory


def ensure_samples() -> Path:
    if not all((SAMPLE_DIR / name).is_file() for name in
               ("filtered_requests.json", "filtered_ads.json", "vocab.json", "logs.csv")):
        generate_samples()
    return SAMPLE_DIR


if __name__ == "__main__":
    print(generate_samples())
