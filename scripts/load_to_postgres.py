import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
INPUT_PATH = ROOT_DIR / "data" / "processed" / "311_cleaned.json"


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS complaints_clean (
    unique_key BIGINT PRIMARY KEY,
    created_date TIMESTAMP,
    closed_date TIMESTAMP,
    agency VARCHAR(50),
    complaint_type VARCHAR(255),
    borough VARCHAR(50),
    resolution_hours NUMERIC,
    resolution_category VARCHAR(50)
);
"""

UPSERT_SQL = """
INSERT INTO complaints_clean (
    unique_key,
    created_date,
    closed_date,
    agency,
    complaint_type,
    borough,
    resolution_hours,
    resolution_category
)
VALUES %s
ON CONFLICT (unique_key) DO UPDATE SET
    created_date = EXCLUDED.created_date,
    closed_date = EXCLUDED.closed_date,
    agency = EXCLUDED.agency,
    complaint_type = EXCLUDED.complaint_type,
    borough = EXCLUDED.borough,
    resolution_hours = EXCLUDED.resolution_hours,
    resolution_category = EXCLUDED.resolution_category
RETURNING (xmax = 0) AS inserted;
"""


def load_env_file() -> None:
    if not ENV_PATH.exists():
        return

    with ENV_PATH.open("r", encoding="utf-8") as env_file:
        for line in env_file:
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith("#") or "=" not in stripped_line:
                continue

            key, value = stripped_line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def get_database_url() -> str:
    load_env_file()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set in .env or the environment.")
    return database_url


def load_records() -> list[dict]:
    try:
        with INPUT_PATH.open("r", encoding="utf-8") as input_file:
            records = json.load(input_file)
    except FileNotFoundError as exc:
        raise SystemExit(f"Input file not found: {INPUT_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON file: {exc}") from exc

    if not isinstance(records, list):
        raise SystemExit("Unexpected file format: expected a list of records.")

    return [record for record in records if isinstance(record, dict)]


def build_row(record: dict) -> tuple:
    return (
        record.get("unique_key"),
        record.get("created_date"),
        record.get("closed_date"),
        record.get("agency"),
        record.get("complaint_type"),
        record.get("borough"),
        record.get("resolution_hours"),
        record.get("resolution_category"),
    )


def main() -> None:
    database_url = get_database_url()
    records = load_records()
    rows = [build_row(record) for record in records if record.get("unique_key") is not None]

    inserted_rows = 0
    updated_rows = 0

    with psycopg2.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)

            if rows:
                execute_values(cursor, UPSERT_SQL, rows)
                results = cursor.fetchall()
                inserted_rows = sum(1 for (inserted,) in results if inserted)
                updated_rows = len(results) - inserted_rows

            cursor.execute("SELECT COUNT(*) FROM complaints_clean;")
            total_rows = cursor.fetchone()[0]

    print(f"Inserted rows: {inserted_rows}")
    print(f"Updated rows: {updated_rows}")
    print(f"Total rows: {total_rows}")


if __name__ == "__main__":
    main()
