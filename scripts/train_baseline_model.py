from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder


INPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "311_cleaned.json"
FEATURE_COLUMNS = ["agency", "complaint_type", "borough"]
TARGET_COLUMN = "resolution_category"


def main() -> None:
    try:
        data = pd.read_json(INPUT_PATH)
    except FileNotFoundError as exc:
        raise SystemExit(f"Input file not found: {INPUT_PATH}") from exc
    except ValueError as exc:
        raise SystemExit(f"Invalid JSON file: {exc}") from exc

    required_columns = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing_columns = [column for column in required_columns if column not in data.columns]
    if missing_columns:
        raise SystemExit(f"Missing required columns: {', '.join(missing_columns)}")

    model_data = data[required_columns].dropna()
    if model_data.empty:
        raise SystemExit("No complete records available for training.")

    X = model_data[FEATURE_COLUMNS].astype(str)
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

    model = Pipeline(
        steps=[
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ("classifier", LogisticRegression(max_iter=1000)),
        ]
    )

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    print("Top 20 most common feature values:")
    feature_value_counts = pd.concat(
        [model_data[column].astype(str).map(lambda value: f"{column}={value}") for column in FEATURE_COLUMNS]
    ).value_counts()
    for feature_value, count in feature_value_counts.head(20).items():
        print(f"- {feature_value}: {count}")

    print(f"\nAccuracy: {accuracy_score(y_test, predictions):.4f}")
    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=range(len(label_encoder.classes_)),
            target_names=label_encoder.classes_,
            zero_division=0,
        )
    )
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, predictions, labels=range(len(label_encoder.classes_))))


if __name__ == "__main__":
    main()
