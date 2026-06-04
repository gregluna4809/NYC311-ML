from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from xgboost import XGBClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "311_cleaned.json"
OUTPUT_PATH = PROJECT_ROOT / "models" / "enhanced_xgboost_pipeline.joblib"

BASE_FEATURE_COLUMNS = ["agency", "complaint_type", "borough"]
TIME_FEATURE_COLUMNS = ["hour_of_day", "day_of_week", "month", "weekend_flag"]
FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + TIME_FEATURE_COLUMNS
TARGET_COLUMN = "resolution_category"


def make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def make_xgboost_classifier(class_count: int) -> XGBClassifier:
    return XGBClassifier(
        objective="multi:softmax",
        num_class=class_count,
        eval_metric="mlogloss",
        random_state=42,
    )


def add_time_features(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    created_dates = pd.to_datetime(data["created_date"], errors="coerce")
    data["hour_of_day"] = created_dates.dt.hour
    data["day_of_week"] = created_dates.dt.day_name()
    data["month"] = created_dates.dt.month
    data["weekend_flag"] = created_dates.dt.weekday >= 5
    return data


def load_training_data() -> pd.DataFrame:
    try:
        data = pd.read_json(INPUT_PATH)
    except FileNotFoundError as exc:
        raise SystemExit(f"Input file not found: {INPUT_PATH}") from exc
    except ValueError as exc:
        raise SystemExit(f"Invalid JSON file: {exc}") from exc

    required_columns = BASE_FEATURE_COLUMNS + ["created_date", TARGET_COLUMN]
    missing_columns = [column for column in required_columns if column not in data.columns]
    if missing_columns:
        raise SystemExit(f"Missing required columns: {', '.join(missing_columns)}")

    model_data = add_time_features(data)
    model_data = model_data[FEATURE_COLUMNS + [TARGET_COLUMN]].dropna()
    if model_data.empty:
        raise SystemExit("No complete records available for training.")

    return model_data


def main() -> None:
    model_data = load_training_data()
    X = model_data[FEATURE_COLUMNS].astype(str)
    y = model_data[TARGET_COLUMN].astype(str)

    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    pipeline = Pipeline(
        steps=[
            ("encoder", make_one_hot_encoder()),
            ("classifier", make_xgboost_classifier(len(label_encoder.classes_))),
        ]
    )
    pipeline.fit(X, y_encoded)

    saved_model = {
        "pipeline": pipeline,
        "label_encoder": label_encoder,
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(saved_model, OUTPUT_PATH)
    print(f"Enhanced XGBoost model pipeline saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
