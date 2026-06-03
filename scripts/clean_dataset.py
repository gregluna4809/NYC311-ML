import json
from collections import Counter
from datetime import datetime
from pathlib import Path


INPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "311_sample.json"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "311_cleaned.json"


def is_missing(value) -> bool:
    return value is None or value == ""


def parse_datetime(value):
    if is_missing(value):
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_resolution_category(resolution_hours: float) -> str:
    if resolution_hours < 24:
        return "Same Day"
    if resolution_hours < 72:
        return "1-3 Days"
    if resolution_hours < 168:
        return "3-7 Days"
    return "Over 7 Days"


def main() -> None:
    try:
        with INPUT_PATH.open("r", encoding="utf-8") as input_file:
            records = json.load(input_file)
    except FileNotFoundError as exc:
        raise SystemExit(f"Input file not found: {INPUT_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON file: {exc}") from exc

    if not isinstance(records, list):
        raise SystemExit("Unexpected file format: expected a list of records.")

    cleaned_records = []
    category_counts = Counter()

    for record in records:
        if not isinstance(record, dict):
            continue

        created_date = parse_datetime(record.get("created_date"))
        closed_date = parse_datetime(record.get("closed_date"))

        if created_date is None or closed_date is None:
            continue

        resolution_hours = (closed_date - created_date).total_seconds() / 3600
        if resolution_hours < 0:
            continue

        cleaned_record = dict(record)
        cleaned_record["resolution_hours"] = resolution_hours
        cleaned_record["resolution_category"] = get_resolution_category(resolution_hours)

        cleaned_records.append(cleaned_record)
        category_counts[cleaned_record["resolution_category"]] += 1

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(cleaned_records, output_file, indent=2)

    print(f"Original record count: {len(records)}")
    print(f"Records removed: {len(records) - len(cleaned_records)}")
    print(f"Cleaned record count: {len(cleaned_records)}")
    print("Category distribution:")
    for category, count in category_counts.items():
        print(f"- {category}: {count}")


if __name__ == "__main__":
    main()
