from app.services.nlp import extract_job, extract_profile


def test_extract_profile_skills_experience_and_contact():
    profile = extract_profile(
        """
        Alex Perera
        alex@example.com
        +94 77 123 4567
        Machine Learning Engineer with 4 years of experience in Python, FastAPI, Docker, SQL and NLP.
        Bachelor degree in Computer Science.
        """
    )

    assert profile.full_name == "Alex Perera"
    assert profile.email == "alex@example.com"
    assert "python" in profile.skills
    assert "fastapi" in profile.skills
    assert profile.experience_years == 4
    assert "bachelor" in profile.education


def test_extract_job_required_and_preferred_skills():
    job = extract_job(
        "Required: Python, FastAPI, Docker and SQL. Preferred experience with XGBoost. 3+ years of experience."
    )

    assert "python" in job.required_skills
    assert "xgboost" in job.preferred_skills
    assert job.min_experience_years == 3


def test_extract_profile_normalizes_bsc_as_bachelor():
    profile = extract_profile("Tharusha Rathnayaka\nBSc (Hons) in Information Technology")

    assert profile.education == ["bachelor"]
