import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


INPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "311_cleaned.json"


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


def print_grouped_counters(title: str, grouped_counts: dict[str, Counter], limit: int | None = None) -> None:
    print(f"\n{title}:")
    if not grouped_counts:
        print("- No values found")
        return

    for group in sorted(grouped_counts):
        print(f"- {group}:")
        for value, count in grouped_counts[group].most_common(limit):
            print(f"  - {value}: {count}")


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

    category_counts = Counter()
    complaint_types_by_category = defaultdict(Counter)
    agencies_by_category = defaultdict(Counter)
    categories_by_borough = defaultdict(Counter)
    categories_by_day_of_week = defaultdict(Counter)

    for record in records:
        if not isinstance(record, dict):
            continue

        created_date = parse_datetime(record.get("created_date"))
        if created_date is None:
            continue

        record["hour_of_day"] = created_date.hour
        record["day_of_week"] = created_date.strftime("%A")
        record["month"] = created_date.month
        record["weekend_flag"] = created_date.weekday() >= 5

        category = record.get("resolution_category") or "(missing)"
        complaint_type = record.get("complaint_type") or "(missing)"
        agency = record.get("agency") or "(missing)"
        borough = record.get("borough") or "(missing)"

        category_counts[category] += 1
        complaint_types_by_category[category][complaint_type] += 1
        agencies_by_category[category][agency] += 1
        categories_by_borough[borough][category] += 1
        categories_by_day_of_week[record["day_of_week"]][category] += 1

    print_counter("Resolution category distribution", category_counts)
    print_grouped_counters("Top complaint types per resolution category", complaint_types_by_category, limit=10)
    print_grouped_counters("Top agencies per resolution category", agencies_by_category, limit=10)
    print_grouped_counters("Resolution category by borough", categories_by_borough)
    print_grouped_counters("Resolution category by day_of_week", categories_by_day_of_week)


if __name__ == "__main__":
    main()
