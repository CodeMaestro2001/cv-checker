import argparse
import csv
import json
from pathlib import Path
from typing import Any

from app.services.features import FEATURE_COLUMNS, build_match_features, features_as_row


LABEL_MAP = {
    "poor": 0,
    "bad": 0,
    "low": 0,
    "no": 0,
    "not_match": 0,
    "average": 1,
    "medium": 1,
    "partial": 1,
    "maybe": 1,
    "good": 2,
    "strong": 2,
    "match": 2,
    "yes": 2,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train candidate-job match classifier from labeled CSV data.")
    parser.add_argument("--data", default="data/training_samples.csv", help="CSV with resume_text, job_text, label columns.")
    parser.add_argument("--output-dir", default="models", help="Directory for trained model artifacts.")
    args = parser.parse_args()

    dataset_path = Path(args.data)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = load_training_rows(dataset_path)
    if len(rows) < 6:
        raise SystemExit("Need at least 6 labeled rows for a meaningful train/test split.")

    sklearn = import_sklearn()
    train_test_split = sklearn["train_test_split"]
    accuracy_score = sklearn["accuracy_score"]
    classification_report = sklearn["classification_report"]
    confusion_matrix = sklearn["confusion_matrix"]
    joblib = sklearn["joblib"]

    x = []
    y = []
    for row in rows:
        features = build_match_features(row["resume_text"], row["job_text"])
        x.append([features_as_row(features)[column] for column in FEATURE_COLUMNS])
        y.append(parse_label(row["label"]))

    stratify = y if len(set(y)) > 1 and min(y.count(label) for label in set(y)) >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=42, stratify=stratify)

    models = build_models(sklearn)
    results: list[dict[str, Any]] = []
    best_name = ""
    best_model = None
    best_accuracy = -1.0

    for name, model in models.items():
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)
        accuracy = accuracy_score(y_test, predictions)
        results.append({"model": name, "accuracy": round(float(accuracy), 4)})
        if accuracy > best_accuracy:
            best_name = name
            best_model = model
            best_accuracy = accuracy

    assert best_model is not None
    artifact = {
        "model": best_model,
        "feature_columns": FEATURE_COLUMNS,
        "label_names": {0: "poor", 1: "average", 2: "good"},
    }
    joblib.dump(artifact, output_dir / "match_model.joblib")

    best_predictions = best_model.predict(x_test)
    metrics = {
        "best_model": best_name,
        "best_accuracy": round(float(best_accuracy), 4),
        "all_results": results,
        "feature_columns": FEATURE_COLUMNS,
        "classification_report": classification_report(y_test, best_predictions, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, best_predictions).tolist(),
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"Best model: {best_name}")
    print(f"Accuracy: {best_accuracy:.4f}")
    print(f"Saved: {output_dir / 'match_model.joblib'}")
    print(f"Metrics: {output_dir / 'metrics.json'}")


def load_training_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        required = {"resume_text", "job_text", "label"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"Training CSV missing columns: {', '.join(sorted(missing))}")
        return [row for row in reader if row.get("resume_text") and row.get("job_text") and row.get("label")]


def parse_label(value: str) -> int:
    normalized = value.strip().lower()
    if normalized.isdigit():
        numeric = int(normalized)
        if numeric in {0, 1, 2}:
            return numeric
    if normalized in LABEL_MAP:
        return LABEL_MAP[normalized]
    raise SystemExit(f"Unsupported label '{value}'. Use poor/average/good or 0/1/2.")


def import_sklearn() -> dict[str, Any]:
    try:
        import joblib
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        raise SystemExit("Install ML dependencies first: python -m pip install -r requirements-ml.txt") from exc

    return {
        "joblib": joblib,
        "LogisticRegression": LogisticRegression,
        "RandomForestClassifier": RandomForestClassifier,
        "accuracy_score": accuracy_score,
        "classification_report": classification_report,
        "confusion_matrix": confusion_matrix,
        "train_test_split": train_test_split,
    }


def build_models(sklearn: dict[str, Any]) -> dict[str, Any]:
    models = {
        "logistic_regression": sklearn["LogisticRegression"](max_iter=1000, class_weight="balanced"),
        "random_forest": sklearn["RandomForestClassifier"](n_estimators=200, random_state=42, class_weight="balanced"),
    }
    try:
        from xgboost import XGBClassifier

        models["xgboost"] = XGBClassifier(
            n_estimators=120,
            max_depth=3,
            learning_rate=0.08,
            objective="multi:softmax",
            eval_metric="mlogloss",
            random_state=42,
        )
    except ImportError:
        pass
    return models


if __name__ == "__main__":
    main()
