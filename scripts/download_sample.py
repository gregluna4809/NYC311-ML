import json
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path

import requests


ENDPOINT = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
SELECT_COLUMNS = "unique_key,created_date,closed_date,agency,complaint_type,borough,status"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "311_sample.json"
TIMEOUT_SECONDS = 120
DAILY_RECORD_CAP = 50
PAGE_SIZE = 25


def get_request_headers() -> dict[str, str]:
    app_token = os.getenv("NYC_OPENDATA_APP_TOKEN")
    if not app_token:
        return {}

    return {"X-App-Token": app_token}


def subtract_months(value: date, months: int) -> date:
    month_index = value.month - 1 - months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    month_lengths = [
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ]
    day = min(value.day, month_lengths[month - 1])
    return date(year, month, day)


def format_socrata_timestamp(value: date) -> str:
    return datetime.combine(value, time.min).strftime("%Y-%m-%dT%H:%M:%S")


def fetch_day_records(day: date) -> list[dict]:
    day_records: list[dict] = []
    next_day = day + timedelta(days=1)
    headers = get_request_headers()
    offset = 0

    while len(day_records) < DAILY_RECORD_CAP:
        remaining_records = DAILY_RECORD_CAP - len(day_records)
        params = {
            "$select": SELECT_COLUMNS,
            "$where": (
                f"created_date >= '{format_socrata_timestamp(day)}' "
                f"AND created_date < '{format_socrata_timestamp(next_day)}'"
            ),
            "$order": "created_date ASC, unique_key ASC",
            "$limit": min(PAGE_SIZE, remaining_records),
            "$offset": offset,
        }

        try:
            response = requests.get(ENDPOINT, params=params, headers=headers, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            records = response.json()
        except requests.exceptions.RequestException as exc:
            raise SystemExit(f"Download failed for {day.isoformat()}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON response for {day.isoformat()}: {exc}") from exc

        if not isinstance(records, list):
            raise SystemExit(f"Unexpected response format for {day.isoformat()}: expected a list of records.")

        day_records.extend(record for record in records if isinstance(record, dict))

        if len(records) < params["$limit"]:
            break

        offset += params["$limit"]

    return day_records


def main() -> None:
    today = date.today()
    start_day = subtract_months(today, 12)
    records: list[dict] = []
    current_day = start_day

    while current_day <= today:
        day_records = fetch_day_records(current_day)
        records.extend(day_records)
        print(f"Downloaded {len(day_records)} records for {current_day.isoformat()}")
        current_day += timedelta(days=1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(records, output_file, indent=2)

    print(f"Downloaded {len(records)} records from {start_day.isoformat()} through {today.isoformat()} to {OUTPUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import sys
        print(f"[dataloader] FAILED: {e}", file=sys.stderr)
        sys.exit(1)
