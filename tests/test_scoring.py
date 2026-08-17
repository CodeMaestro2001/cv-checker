from app.services.scoring import ScoreInput, score_match


def test_score_match_identifies_missing_skills():
    score = score_match(
        ScoreInput(
            candidate_text="Python FastAPI Docker SQL developer with 4 years experience",
            job_text="Required Python FastAPI Docker SQL NLP with 3 years experience",
            candidate_skills=["python", "fastapi", "docker", "sql"],
            required_skills=["python", "fastapi", "docker", "sql", "nlp"],
            preferred_skills=[],
            candidate_experience_years=4,
            min_experience_years=3,
            candidate_education=["bachelor"],
            education_requirements=["bachelor"],
        )
    )

    assert score.overall_score > 70
    assert "nlp" in score.missing_skills
    assert "python" in score.matched_skills
