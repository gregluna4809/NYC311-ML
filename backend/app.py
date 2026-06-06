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
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://nyc311.pulse-forge.com:8080",
    ],
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


def fetch_complaint_type_metadata() -> list[dict]:
    if engine is None:
        raise HTTPException(status_code=500, detail="Database is not configured.")

    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT DISTINCT complaint_type, agency
                    FROM complaints_clean
                    ORDER BY complaint_type, agency;
                    """
                )
            ).fetchall()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}") from exc

    grouped_complaints: dict[str, list[str]] = {}
    for row in rows:
        complaint_type = row._mapping["complaint_type"]
        agency = row._mapping["agency"]
        if complaint_type is None or agency is None:
            continue
        grouped_complaints.setdefault(str(complaint_type), []).append(str(agency))

    return [
        {"complaint_type": complaint_type, "agencies": agencies}
        for complaint_type, agencies in grouped_complaints.items()
    ]


def get_predicted_class_confidence(probabilities, predicted_class) -> float:
    class_probabilities = probabilities[0]
    return float(class_probabilities[int(predicted_class)])


def predict_resolution_category(payload: PredictionRequest) -> dict:
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
                pipeline = prediction_artifact["pipeline"]
                prediction = pipeline.predict(input_frame.astype(str))
                probabilities = pipeline.predict_proba(input_frame.astype(str))
            else:
                model = prediction_artifact["model"]
                encoder = prediction_artifact["encoder"]
                encoded_features = encoder.transform(input_frame.astype(str))
                prediction = model.predict(encoded_features)
                probabilities = model.predict_proba(encoded_features)

            predicted_class = int(prediction[0])
            return {
                "predicted_category": str(label_encoder.inverse_transform([predicted_class])[0]),
                "confidence": get_predicted_class_confidence(probabilities, predicted_class),
            }

        prediction = prediction_artifact.predict([feature_row])
        probabilities = prediction_artifact.predict_proba([feature_row])
        predicted_class = prediction[0]
        classes = list(getattr(prediction_artifact, "classes_", []))
        if predicted_class in classes:
            confidence = float(probabilities[0][classes.index(predicted_class)])
        else:
            confidence = float(max(probabilities[0]))
        return {
            "predicted_category": str(predicted_class),
            "confidence": confidence,
        }
    except KeyError as exc:
        raise HTTPException(status_code=500, detail=f"Model artifact missing key: {exc}") from exc
    except AttributeError as exc:
        raise HTTPException(status_code=500, detail=f"Prediction model does not support confidence scores: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict")
def predict(payload: PredictionRequest) -> dict:
    prediction = predict_resolution_category(payload)
    return {
        "predicted_category": prediction["predicted_category"],
        "confidence": prediction["confidence"],
        "model": "Enhanced XGBoost",
    }


@app.get("/metadata/complaint-types")
def complaint_type_metadata() -> list[dict]:
    return fetch_complaint_type_metadata()


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


@app.get("/analytics/trends/volume")
def analytics_trends_volume() -> list[dict]:
    return fetch_count_rows(
        """
        SELECT
            TO_CHAR(DATE_TRUNC('month', created_date), 'YYYY-MM') AS month,
            COUNT(*) AS count
        FROM complaints_clean
        WHERE created_date IS NOT NULL
        GROUP BY DATE_TRUNC('month', created_date)
        ORDER BY DATE_TRUNC('month', created_date);
        """
    )


@app.get("/analytics/trends/resolution")
def analytics_trends_resolution() -> list[dict]:
    return fetch_count_rows(
        """
        SELECT
            TO_CHAR(DATE_TRUNC('month', created_date), 'YYYY-MM') AS month,
            ROUND(AVG(resolution_hours)::numeric, 2) AS average_resolution_hours
        FROM complaints_clean
        WHERE created_date IS NOT NULL
            AND resolution_hours IS NOT NULL
        GROUP BY DATE_TRUNC('month', created_date)
        ORDER BY DATE_TRUNC('month', created_date);
        """
    )
