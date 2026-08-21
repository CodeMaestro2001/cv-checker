from app.core.config import Settings
from app.services import ml_matching
from app.services.scoring import ScoreOutput


class FakeProbabilityModel:
    classes_ = [0, 1, 2]

    def predict_proba(self, rows):
        return [[0.05, 0.15, 0.80]]


def test_apply_ml_matcher_uses_model_probabilities(monkeypatch):
    artifact = {
        "model": FakeProbabilityModel(),
        "feature_columns": ml_matching.FEATURE_COLUMNS,
        "label_names": {0: "poor", 1: "average", 2: "good"},
    }
    monkeypatch.setattr(ml_matching, "_load_artifact", lambda model_path: artifact)

    baseline = ScoreOutput(
        overall_score=72,
        semantic_score=75,
        skill_score=80,
        experience_score=100,
        education_score=100,
        matched_skills=["python"],
        missing_skills=[],
        recommendation="Baseline recommendation",
        explanation="Baseline explanation.",
    )

    result = ml_matching.apply_ml_matcher(
        baseline,
        "Alex has 4 years of experience in Python and FastAPI. Bachelor degree.",
        "Required Python and FastAPI. Bachelor degree. 3 years of experience.",
        Settings(enable_ml_model=True, match_model_path="fake.joblib"),
    )

    assert result.overall_score == 81.25
    assert result.recommendation.startswith("ML model marks this as a strong match")
    assert "ML model predicts 'good' match" in result.explanation


def test_apply_ml_matcher_falls_back_when_disabled(monkeypatch):
    monkeypatch.setattr(ml_matching, "_load_artifact", lambda model_path: None)
    baseline = ScoreOutput(
        overall_score=72,
        semantic_score=75,
        skill_score=80,
        experience_score=100,
        education_score=100,
        matched_skills=["python"],
        missing_skills=[],
        recommendation="Baseline recommendation",
        explanation="Baseline explanation.",
    )

    result = ml_matching.apply_ml_matcher(
        baseline,
        "resume text",
        "job text",
        Settings(enable_ml_model=False, match_model_path="fake.joblib"),
    )

    assert result is baseline
