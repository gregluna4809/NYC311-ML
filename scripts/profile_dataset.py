import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean, median


INPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "311_sample.json"


def is_missing(value) -> bool:
    return value is None or value == ""


def parse_datetime(value):
    if is_missing(value):
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def print_counter(title: str, counter: Counter, limit: int | None = None) -> None:
    print(f"\n{title}:")
    items = counter.most_common(limit)
    if not items:
        print("- No values found")
        return

    for value, count in items:
        print(f"- {value}: {count}")


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

    columns = sorted({column for record in records if isinstance(record, dict) for column in record})
    missing_counts = Counter()

    for column in columns:
        missing_counts[column] = sum(
            1 for record in records if not isinstance(record, dict) or is_missing(record.get(column))
        )

    resolution_hours = []
    resolution_records = []
    complaint_type_counts = Counter()
    borough_counts = Counter()
    agency_counts = Counter()

    for record in records:
        if not isinstance(record, dict):
            continue

        complaint_type_counts[record.get("complaint_type") or "(missing)"] += 1
        borough_counts[record.get("borough") or "(missing)"] += 1
        agency_counts[record.get("agency") or "(missing)"] += 1

        created_date = parse_datetime(record.get("created_date"))
        closed_date = parse_datetime(record.get("closed_date"))
        if created_date is not None and closed_date is not None:
            hours = (closed_date - created_date).total_seconds() / 3600
            resolution_hours.append(hours)
            resolution_records.append(
                {
                    "unique_key": record.get("unique_key"),
                    "complaint_type": record.get("complaint_type"),
                    "agency": record.get("agency"),
                    "borough": record.get("borough"),
                    "created_date": record.get("created_date"),
                    "closed_date": record.get("closed_date"),
                    "resolution_hours": hours,
                }
            )

    print(f"Number of records: {len(records)}")
    print("\nColumns:")
    for column in columns:
        print(f"- {column}")

    print("\nMissing values per column:")
    for column in columns:
        print(f"- {column}: {missing_counts[column]}")

    print("\nFirst 3 records:")
    print(json.dumps(records[:3], indent=2))

    print("\nResolution time analysis:")
    if resolution_hours:
        print(f"- Minimum resolution_hours: {min(resolution_hours):.2f}")
        print(f"- Maximum resolution_hours: {max(resolution_hours):.2f}")
        print(f"- Average resolution_hours: {mean(resolution_hours):.2f}")
        print(f"- Median resolution_hours: {median(resolution_hours):.2f}")
    else:
        print("- No records found with both created_date and closed_date.")

    print("\nResolution time outliers:")
    print(f"- Records with resolution_hours greater than 24: {sum(1 for hours in resolution_hours if hours > 24)}")
    print(f"- Records with resolution_hours greater than 72: {sum(1 for hours in resolution_hours if hours > 72)}")
    print(f"- Records with resolution_hours greater than 168: {sum(1 for hours in resolution_hours if hours > 168)}")
    print("- Top 10 longest resolution times:")
    longest_resolution_records = sorted(
        resolution_records,
        key=lambda record: record["resolution_hours"],
        reverse=True,
    )[:10]
    if longest_resolution_records:
        for record in longest_resolution_records:
            print(
                f"  - unique_key={record['unique_key']}, "
                f"complaint_type={record['complaint_type']}, "
                f"agency={record['agency']}, "
                f"borough={record['borough']}, "
                f"created_date={record['created_date']}, "
                f"closed_date={record['closed_date']}, "
                f"resolution_hours={record['resolution_hours']:.2f}"
            )
    else:
        print("  - No records found with both created_date and closed_date.")

    print_counter("Top 10 complaint types by count", complaint_type_counts, limit=10)
    print_counter("Borough distribution", borough_counts)
    print_counter("Agency distribution", agency_counts)


if __name__ == "__main__":
    main()
