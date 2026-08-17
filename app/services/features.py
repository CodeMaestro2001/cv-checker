from dataclasses import asdict, dataclass

from app.services.nlp import extract_job, extract_profile
from app.services.scoring import ScoreInput, score_match


@dataclass(frozen=True)
class MatchFeatures:
    baseline_score: float
    semantic_score: float
    skill_score: float
    experience_score: float
    education_score: float
    matched_skill_count: int
    missing_skill_count: int
    candidate_skill_count: int
    required_skill_count: int
    preferred_skill_count: int
    candidate_experience_years: float
    min_experience_years: float


FEATURE_COLUMNS = [
    "baseline_score",
    "semantic_score",
    "skill_score",
    "experience_score",
    "education_score",
    "matched_skill_count",
    "missing_skill_count",
    "candidate_skill_count",
    "required_skill_count",
    "preferred_skill_count",
    "candidate_experience_years",
    "min_experience_years",
]


def build_match_features(resume_text: str, job_text: str) -> MatchFeatures:
    candidate = extract_profile(resume_text)
    job = extract_job(job_text)
    score = score_match(
        ScoreInput(
            candidate_text=resume_text,
            job_text=job_text,
            candidate_skills=candidate.skills,
            required_skills=job.required_skills,
            preferred_skills=job.preferred_skills,
            candidate_experience_years=candidate.experience_years,
            min_experience_years=job.min_experience_years,
            candidate_education=candidate.education,
            education_requirements=job.education_requirements,
        )
    )

    return MatchFeatures(
        baseline_score=score.overall_score,
        semantic_score=score.semantic_score,
        skill_score=score.skill_score,
        experience_score=score.experience_score,
        education_score=score.education_score,
        matched_skill_count=len(score.matched_skills),
        missing_skill_count=len(score.missing_skills),
        candidate_skill_count=len(candidate.skills),
        required_skill_count=len(job.required_skills),
        preferred_skill_count=len(job.preferred_skills),
        candidate_experience_years=candidate.experience_years,
        min_experience_years=job.min_experience_years,
    )


def features_as_row(features: MatchFeatures) -> dict[str, float]:
    row = asdict(features)
    return {column: float(row[column]) for column in FEATURE_COLUMNS}
