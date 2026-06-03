import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"


QUERIES = [
    (
        "Top 10 complaint types",
        """
        SELECT complaint_type, COUNT(*) AS complaint_count
        FROM complaints_clean
        GROUP BY complaint_type
        ORDER BY complaint_count DESC
        LIMIT 10;
        """,
    ),
    (
        "Resolution category distribution",
        """
        SELECT resolution_category, COUNT(*) AS complaint_count
        FROM complaints_clean
        GROUP BY resolution_category
        ORDER BY complaint_count DESC;
        """,
    ),
    (
        "Complaints by borough",
        """
        SELECT borough, COUNT(*) AS complaint_count
        FROM complaints_clean
        GROUP BY borough
        ORDER BY complaint_count DESC;
        """,
    ),
    (
        "Average resolution_hours by agency",
        """
        SELECT agency, AVG(resolution_hours) AS average_resolution_hours
        FROM complaints_clean
        GROUP BY agency
        ORDER BY average_resolution_hours DESC;
        """,
    ),
    (
        "Average resolution_hours by complaint_type (top 20 complaint types only)",
        """
        WITH top_complaint_types AS (
            SELECT complaint_type
            FROM complaints_clean
            GROUP BY complaint_type
            ORDER BY COUNT(*) DESC
            LIMIT 20
        )
        SELECT
            complaints_clean.complaint_type,
            AVG(complaints_clean.resolution_hours) AS average_resolution_hours
        FROM complaints_clean
        JOIN top_complaint_types
            ON complaints_clean.complaint_type = top_complaint_types.complaint_type
        GROUP BY complaints_clean.complaint_type
        ORDER BY average_resolution_hours DESC;
        """,
    ),
]


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


def print_results(title: str, rows) -> None:
    print(f"\n{title}:")
    if not rows:
        print("- No rows found")
        return

    for row in rows:
        values = row._mapping
        print("- " + ", ".join(f"{key}: {value}" for key, value in values.items()))


def main() -> None:
    database_url = get_database_url()

    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            for title, query in QUERIES:
                rows = connection.execute(text(query)).fetchall()
                print_results(title, rows)
    except SQLAlchemyError as exc:
        raise SystemExit(f"Database query failed: {exc}") from exc


if __name__ == "__main__":
    main()
