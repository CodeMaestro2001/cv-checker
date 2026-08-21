from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.features import FEATURE_COLUMNS, build_match_features, features_as_row
from app.services.scoring import ScoreOutput


LABEL_SCORE = {
    "poor": 20.0,
    "average": 55.0,
    "good": 90.0,
}


def apply_ml_matcher(baseline: ScoreOutput, resume_text: str, job_text: str, settings: Settings) -> ScoreOutput:
    if not settings.enable_ml_model:
        return baseline

    artifact = _load_artifact(settings.match_model_path)
    if artifact is None:
        return baseline

    try:
        prediction = _predict_match(artifact, resume_text, job_text)
    except (KeyError, TypeError, ValueError, AttributeError):
        return baseline

    recommendation = _recommendation(prediction["label"], prediction["score"], baseline.missing_skills)
    explanation = (
        f"{baseline.explanation} ML model predicts '{prediction['label']}' match "
        f"with {prediction['confidence']:.0f}% confidence."
    )

    return ScoreOutput(
        overall_score=round(prediction["score"], 2),
        semantic_score=baseline.semantic_score,
        skill_score=baseline.skill_score,
        experience_score=baseline.experience_score,
        education_score=baseline.education_score,
        matched_skills=baseline.matched_skills,
        missing_skills=baseline.missing_skills,
        recommendation=recommendation,
        explanation=explanation,
    )


@lru_cache(maxsize=4)
def _load_artifact(model_path: str) -> dict[str, Any] | None:
    path = Path(model_path)
    if not path.exists():
        return None

    try:
        import joblib
    except ImportError:
        return None

    artifact = joblib.load(path)
    if not isinstance(artifact, dict):
        return None
    if "model" not in artifact or "feature_columns" not in artifact:
        return None
    return artifact


def _predict_match(artifact: dict[str, Any], resume_text: str, job_text: str) -> dict[str, float | str]:
    model = artifact["model"]
    artifact_columns = list(artifact["feature_columns"])
    if artifact_columns != FEATURE_COLUMNS:
        raise ValueError("Model feature columns do not match current feature builder.")

    features = build_match_features(resume_text, job_text)
    row = features_as_row(features)
    x = [[row[column] for column in artifact_columns]]
    label_names = {int(key): value for key, value in artifact.get("label_names", {}).items()}

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(x)[0]
        classes = [int(value) for value in model.classes_]
        class_probabilities = dict(zip(classes, probabilities, strict=True))
        predicted_class = max(class_probabilities, key=class_probabilities.get)
        score = sum(float(probability) * LABEL_SCORE[label_names.get(class_id, "average")] for class_id, probability in class_probabilities.items())
        confidence = float(class_probabilities[predicted_class]) * 100
    else:
        predicted_class = int(model.predict(x)[0])
        score = LABEL_SCORE[label_names.get(predicted_class, "average")]
        confidence = 100.0

    return {
        "label": label_names.get(predicted_class, "average"),
        "score": float(score),
        "confidence": confidence,
    }


def _recommendation(label: str, score: float, missing_skills: list[str]) -> str:
    if label == "good" and not missing_skills:
        return "ML model marks this as a strong match. Prioritize for recruiter review."
    if label == "good":
        return "ML model marks this as a good match. Review missing required skills before shortlisting."
    if label == "average" or score >= 45:
        return "ML model marks this as a partial match. Consider if transferable skills are acceptable."
    return "ML model marks this as a low match. Not recommended unless requirements are flexible."
