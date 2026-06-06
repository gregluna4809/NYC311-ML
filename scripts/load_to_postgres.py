import json
import os
from pathlib import Path

from sqlalchemy import BigInteger, Column, Float, MetaData, String, Table, TIMESTAMP, create_engine, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
INPUT_PATH = ROOT_DIR / "data" / "processed" / "311_cleaned.json"

metadata = MetaData()

complaints_clean = Table(
    "complaints_clean",
    metadata,
    Column("unique_key", BigInteger, primary_key=True),
    Column("created_date", TIMESTAMP),
    Column("closed_date", TIMESTAMP),
    Column("agency", String(50)),
    Column("complaint_type", String(255)),
    Column("borough", String(50)),
    Column("resolution_hours", Float),
    Column("resolution_category", String(50)),
)


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


def build_row(record: dict) -> dict:
    return {
        "unique_key": record.get("unique_key"),
        "created_date": record.get("created_date"),
        "closed_date": record.get("closed_date"),
        "agency": record.get("agency"),
        "complaint_type": record.get("complaint_type"),
        "borough": record.get("borough"),
        "resolution_hours": record.get("resolution_hours"),
        "resolution_category": record.get("resolution_category"),
    }


def upsert_records(engine, rows: list[dict]) -> tuple[int, int]:
    if not rows:
        return 0, 0

    insert_statement = insert(complaints_clean).values(rows)
    update_columns = {
        column.name: insert_statement.excluded[column.name]
        for column in complaints_clean.columns
        if column.name != "unique_key"
    }
    upsert_statement = (
        insert_statement.on_conflict_do_update(
            index_elements=["unique_key"],
            set_=update_columns,
        )
        .returning(text("(xmax = 0) AS inserted"))
    )

    with engine.begin() as connection:
        results = connection.execute(upsert_statement).fetchall()

    inserted_rows = sum(1 for row in results if row.inserted)
    updated_rows = len(results) - inserted_rows
    return inserted_rows, updated_rows


def truncate_complaints_clean(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE complaints_clean;"))

    print("Wiped complaints_clean before loading new records.")


def main() -> None:
    database_url = get_database_url()
    records = load_records()
    rows = [build_row(record) for record in records if record.get("unique_key") is not None]

    try:
        engine = create_engine(database_url)
        metadata.create_all(engine, tables=[complaints_clean])
        truncate_complaints_clean(engine)
        inserted_rows, updated_rows = upsert_records(engine, rows)
    except SQLAlchemyError as exc:
        raise SystemExit(f"Database operation failed: {exc}") from exc

    print(f"Total records processed: {len(rows)}")
    print(f"Rows inserted: {inserted_rows}")
    print(f"Rows updated: {updated_rows}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import sys
        print(f"[dataloader] FAILED: {e}", file=sys.stderr)
        sys.exit(1)
