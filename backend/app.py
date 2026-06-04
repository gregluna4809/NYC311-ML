import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import joblib
import pandas as pd
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


# Run with:
# uvicorn backend.app:app --reload

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
MODEL_PATH = ROOT_DIR / "models" / "enhanced_xgboost_pipeline.joblib"
ENHANCED_FEATURE_COLUMNS = [
    "agency",
    "complaint_type",
    "borough",
    "hour_of_day",
    "day_of_week",
    "month",
    "weekend_flag",
]

prediction_artifact = None
prediction_artifact_error: str | None = None

app = FastAPI(title="NYC Civic ML API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictionRequest(BaseModel):
    agency: str
    complaint_type: str
    borough: str
    day_of_week: str
    month: int
    hour_of_day: int
    weekend_flag: bool


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


@app.on_event("startup")
def load_prediction_artifact() -> None:
    global prediction_artifact, prediction_artifact_error

    if not MODEL_PATH.exists():
        prediction_artifact = None
        prediction_artifact_error = f"Model file not found: {MODEL_PATH}"
        return

    try:
        prediction_artifact = joblib.load(MODEL_PATH)
        prediction_artifact_error = None
    except Exception as exc:
        prediction_artifact = None
        prediction_artifact_error = f"Failed to load model: {exc}"


def fetch_count_rows(query: str) -> list[dict]:
    if engine is None:
        raise HTTPException(status_code=500, detail="Database is not configured.")

    try:
        with engine.connect() as connection:
            rows = connection.execute(text(query)).fetchall()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}") from exc

    return [dict(row._mapping) for row in rows]


def predict_resolution_category(payload: PredictionRequest) -> str:
    if prediction_artifact is None:
        detail = prediction_artifact_error or "Prediction model is not loaded."
        raise HTTPException(status_code=500, detail=detail)

    feature_row = {
        "agency": payload.agency,
        "complaint_type": payload.complaint_type,
        "borough": payload.borough,
        "hour_of_day": payload.hour_of_day,
        "day_of_week": payload.day_of_week,
        "month": payload.month,
        "weekend_flag": payload.weekend_flag,
    }

    try:
        if isinstance(prediction_artifact, dict):
            feature_columns = prediction_artifact.get("feature_columns", ENHANCED_FEATURE_COLUMNS)
            input_frame = pd.DataFrame([{column: feature_row[column] for column in feature_columns}])
            label_encoder = prediction_artifact["label_encoder"]

            if "pipeline" in prediction_artifact:
                prediction = prediction_artifact["pipeline"].predict(input_frame.astype(str))
            else:
                model = prediction_artifact["model"]
                encoder = prediction_artifact["encoder"]
                encoded_features = encoder.transform(input_frame.astype(str))
                prediction = model.predict(encoded_features)

            return str(label_encoder.inverse_transform([int(prediction[0])])[0])

        prediction = prediction_artifact.predict([feature_row])
        return str(prediction[0])
    except KeyError as exc:
        raise HTTPException(status_code=500, detail=f"Model artifact missing key: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict")
def predict(payload: PredictionRequest) -> dict:
    return {
        "predicted_category": predict_resolution_category(payload),
        "model": "Enhanced XGBoost",
    }


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
