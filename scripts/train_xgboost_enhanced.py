from pathlib import Path

import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from xgboost import XGBClassifier


INPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "311_cleaned.json"
BASE_FEATURE_COLUMNS = ["agency", "complaint_type", "borough"]
TIME_FEATURE_COLUMNS = ["hour_of_day", "day_of_week", "month", "weekend_flag"]
ENHANCED_FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + TIME_FEATURE_COLUMNS
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


def train_xgboost_with_encoded_features(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train,
    class_count: int,
):
    encoder = make_one_hot_encoder()
    X_train_encoded = encoder.fit_transform(X_train)
    X_test_encoded = encoder.transform(X_test)

    model = make_xgboost_classifier(class_count)
    model.fit(X_train_encoded, y_train)
    predictions = model.predict(X_test_encoded)
    return model, encoder, predictions


def main() -> None:
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
    model_data = model_data[ENHANCED_FEATURE_COLUMNS + [TARGET_COLUMN]].dropna()
    if model_data.empty:
        raise SystemExit("No complete records available for training.")

    X = model_data[ENHANCED_FEATURE_COLUMNS].astype(str)
    y = model_data[TARGET_COLUMN].astype(str)

    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    stratify = y_encoded if pd.Series(y_encoded).value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y_encoded,
        test_size=0.2,
        random_state=42,
        stratify=stratify,
    )

    enhanced_model, enhanced_encoder, enhanced_predictions = train_xgboost_with_encoded_features(
        X_train,
        X_test,
        y_train,
        len(label_encoder.classes_),
    )

    majority_model = DummyClassifier(strategy="most_frequent")
    majority_model.fit(X_train, y_train)
    majority_predictions = majority_model.predict(X_test)

    logistic_model = Pipeline(
        steps=[
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ("classifier", LogisticRegression(max_iter=1000)),
        ]
    )
    logistic_model.fit(X_train[BASE_FEATURE_COLUMNS], y_train)
    logistic_predictions = logistic_model.predict(X_test[BASE_FEATURE_COLUMNS])

    _, _, original_xgboost_predictions = train_xgboost_with_encoded_features(
        X_train[BASE_FEATURE_COLUMNS],
        X_test[BASE_FEATURE_COLUMNS],
        y_train,
        len(label_encoder.classes_),
    )

    print(f"Accuracy: {accuracy_score(y_test, enhanced_predictions):.4f}")
    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            enhanced_predictions,
            labels=range(len(label_encoder.classes_)),
            target_names=label_encoder.classes_,
            zero_division=0,
        )
    )
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, enhanced_predictions, labels=range(len(label_encoder.classes_))))

    print("\nTop feature importances:")
    feature_names = enhanced_encoder.get_feature_names_out(ENHANCED_FEATURE_COLUMNS)
    feature_importances = sorted(
        zip(feature_names, enhanced_model.feature_importances_),
        key=lambda item: item[1],
        reverse=True,
    )
    for rank, (feature_name, importance) in enumerate(feature_importances[:20], start=1):
        print(f"{rank}. {feature_name}: {importance:.6f}")

    print("\nAccuracy comparison:")
    print(f"- Majority Class Baseline: {accuracy_score(y_test, majority_predictions):.4f}")
    print(f"- Logistic Regression: {accuracy_score(y_test, logistic_predictions):.4f}")
    print(f"- Original XGBoost: {accuracy_score(y_test, original_xgboost_predictions):.4f}")
    print(f"- Enhanced XGBoost: {accuracy_score(y_test, enhanced_predictions):.4f}")


if __name__ == "__main__":
    main()
