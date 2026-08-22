from dataclasses import dataclass
import math
import re
from collections import Counter


EDUCATION_EQUIVALENTS = {
    "degree": {"degree", "bachelor", "bsc", "master", "msc", "mba", "phd", "doctorate"},
    "bachelor": {"degree", "bachelor", "bsc", "master", "msc", "mba", "phd", "doctorate"},
    "bsc": {"degree", "bachelor", "bsc", "master", "msc", "mba", "phd", "doctorate"},
    "master": {"master", "msc", "mba", "phd", "doctorate"},
    "msc": {"master", "msc", "phd", "doctorate"},
    "mba": {"master", "mba", "phd", "doctorate"},
    "phd": {"phd", "doctorate"},
    "doctorate": {"phd", "doctorate"},
    "diploma": {"diploma"},
}


@dataclass(frozen=True)
class ScoreInput:
    candidate_text: str
    job_text: str
    candidate_skills: list[str]
    required_skills: list[str]
    preferred_skills: list[str]
    candidate_experience_years: float
    min_experience_years: float
    candidate_education: list[str]
    education_requirements: list[str]


@dataclass(frozen=True)
class ScoreOutput:
    overall_score: float
    semantic_score: float
    skill_score: float
    experience_score: float
    education_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    recommendation: str
    explanation: str


def score_match(payload: ScoreInput) -> ScoreOutput:
    candidate_skills = set(payload.candidate_skills)
    required_skills = set(payload.required_skills)
    preferred_skills = set(payload.preferred_skills)
    all_job_skills = required_skills | preferred_skills

    matched_skills = sorted(candidate_skills & all_job_skills)
    missing_skills = sorted(required_skills - candidate_skills)

    required_score = _ratio(len(candidate_skills & required_skills), len(required_skills))
    preferred_score = _ratio(len(candidate_skills & preferred_skills), len(preferred_skills))
    skill_score = round((required_score * 0.75) + (preferred_score * 0.25), 4)

    semantic_score = _semantic_similarity(payload.candidate_text, payload.job_text)
    experience_score = _experience_fit(payload.candidate_experience_years, payload.min_experience_years)
    education_score = _education_fit(payload.candidate_education, payload.education_requirements)

    overall = (
        skill_score * 0.4
        + semantic_score * 0.3
        + experience_score * 0.2
        + education_score * 0.1
    )
    overall_score = round(overall * 100, 2)

    recommendation = _recommendation(overall_score, missing_skills)
    explanation = _explain(overall_score, matched_skills, missing_skills, experience_score, education_score)

    return ScoreOutput(
        overall_score=overall_score,
        semantic_score=round(semantic_score * 100, 2),
        skill_score=round(skill_score * 100, 2),
        experience_score=round(experience_score * 100, 2),
        education_score=round(education_score * 100, 2),
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        recommendation=recommendation,
        explanation=explanation,
    )


def _semantic_similarity(candidate_text: str, job_text: str) -> float:
    candidate_tokens = _tokens(candidate_text)
    job_tokens = _tokens(job_text)
    if not candidate_tokens or not job_tokens:
        return 0.0
    candidate_counts = Counter(candidate_tokens)
    job_counts = Counter(job_tokens)
    shared_terms = set(candidate_counts) & set(job_counts)
    numerator = sum(candidate_counts[term] * job_counts[term] for term in shared_terms)
    candidate_norm = math.sqrt(sum(value * value for value in candidate_counts.values()))
    job_norm = math.sqrt(sum(value * value for value in job_counts.values()))
    return numerator / (candidate_norm * job_norm)


def _tokens(text: str) -> list[str]:
    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "for",
        "in",
        "is",
        "of",
        "or",
        "the",
        "to",
        "with",
    }
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in stop_words]


def _experience_fit(candidate_years: float, required_years: float) -> float:
    if required_years <= 0:
        return 1.0
    return min(candidate_years / required_years, 1.0)


def _education_fit(candidate_education: list[str], requirements: list[str]) -> float:
    if not requirements:
        return 1.0
    candidate = {_normalize_education(value) for value in candidate_education}
    required = {_normalize_education(value) for value in requirements}
    matches = sum(1 for requirement in required if candidate & EDUCATION_EQUIVALENTS.get(requirement, {requirement}))
    return _ratio(matches, len(required))


def _normalize_education(value: str) -> str:
    lowered = value.lower().strip()
    aliases = {
        "b.sc": "bsc",
        "b.sc.": "bsc",
        "bachelors": "bachelor",
        "masters": "master",
        "m.sc": "msc",
        "m.sc.": "msc",
        "doctoral": "doctorate",
    }
    return aliases.get(lowered, lowered)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return numerator / denominator


def _recommendation(overall_score: float, missing_skills: list[str]) -> str:
    if overall_score >= 80 and not missing_skills:
        return "Strong match. Prioritize for recruiter review."
    if overall_score >= 65:
        return "Good match. Review missing skills and validate experience depth."
    if overall_score >= 45:
        return "Partial match. Consider if transferable skills are acceptable."
    return "Low match. Not recommended unless the role requirements are flexible."


def _explain(
    overall_score: float,
    matched_skills: list[str],
    missing_skills: list[str],
    experience_score: float,
    education_score: float,
) -> str:
    matched = ", ".join(matched_skills) if matched_skills else "no required/preferred skills"
    missing = ", ".join(missing_skills) if missing_skills else "no required skills"
    return (
        f"Overall score is {overall_score:.2f}%. Candidate matched {matched}. "
        f"Missing {missing}. Experience fit is {experience_score * 100:.0f}% and "
        f"education fit is {education_score * 100:.0f}%."
    )
