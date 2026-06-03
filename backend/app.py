import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


# Run with:
# uvicorn backend.app:app --reload

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"

app = FastAPI(title="NYC Civic ML API")


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
        raise RuntimeError("DATABASE_URL is not set in .env or the environment.")
    return database_url


try:
    engine = create_engine(get_database_url())
except RuntimeError:
    engine = None


def fetch_count_rows(query: str) -> list[dict]:
    if engine is None:
        raise HTTPException(status_code=500, detail="Database is not configured.")

    try:
        with engine.connect() as connection:
            rows = connection.execute(text(query)).fetchall()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}") from exc

    return [dict(row._mapping) for row in rows]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/analytics/categories")
def analytics_categories() -> list[dict]:
    return fetch_count_rows(
        """
        SELECT resolution_category, COUNT(*) AS count
        FROM complaints_clean
        GROUP BY resolution_category
        ORDER BY count DESC;
        """
    )


@app.get("/analytics/boroughs")
def analytics_boroughs() -> list[dict]:
    return fetch_count_rows(
        """
        SELECT borough, COUNT(*) AS count
        FROM complaints_clean
        GROUP BY borough
        ORDER BY count DESC;
        """
    )


@app.get("/analytics/agencies")
def analytics_agencies() -> list[dict]:
    return fetch_count_rows(
        """
        SELECT agency, COUNT(*) AS count
        FROM complaints_clean
        GROUP BY agency
        ORDER BY count DESC;
        """
    )


@app.get("/analytics/top-complaints")
def analytics_top_complaints() -> list[dict]:
    return fetch_count_rows(
        """
        SELECT complaint_type, COUNT(*) AS count
        FROM complaints_clean
        GROUP BY complaint_type
        ORDER BY count DESC
        LIMIT 10;
        """
    )
