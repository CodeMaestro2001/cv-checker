from app.services.features import FEATURE_COLUMNS, build_match_features, features_as_row


def test_build_match_features_contains_training_columns():
    features = build_match_features(
        "Alex has 4 years of experience in Python, FastAPI, Docker, SQL and NLP. Bachelor degree.",
        "Required Python, FastAPI, Docker, SQL and NLP. Bachelor degree. 3 years of experience.",
    )
    row = features_as_row(features)

    assert list(row.keys()) == FEATURE_COLUMNS
    assert row["baseline_score"] > 80
    assert row["missing_skill_count"] == 0
