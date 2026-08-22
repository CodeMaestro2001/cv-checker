import re
from dataclasses import dataclass


SKILL_CANONICAL = {
    "python": ["python"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "sql": ["sql", "postgres", "postgresql", "mysql"],
    "fastapi": ["fastapi"],
    "streamlit": ["streamlit"],
    "docker": ["docker", "docker compose", "container"],
    "machine learning": ["machine learning", "ml", "scikit-learn", "sklearn"],
    "nlp": ["nlp", "natural language processing"],
    "sentence transformers": ["sentence transformer", "sentence-transformers", "embeddings"],
    "xgboost": ["xgboost"],
    "random forest": ["random forest"],
    "logistic regression": ["logistic regression"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure"],
    "gcp": ["gcp", "google cloud"],
    "git": ["git", "github", "gitlab"],
    "api development": ["api", "rest api", "restful"],
    "data analysis": ["data analysis", "analytics"],
    "deep learning": ["deep learning", "neural network"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch", "torch"],
    "excel": ["excel", "spreadsheet"],
    "power bi": ["power bi", "powerbi"],
    "tableau": ["tableau"],
    "java": ["java"],
    "javascript": ["javascript", "typescript", "node.js", "nodejs"],
    "react": ["react", "react.js"],
    "kubernetes": ["kubernetes", "k8s"],
}

EDUCATION_CANONICAL = {
    "phd": ["phd", "doctorate", "doctoral"],
    "master": ["master", "masters", "msc", "mba", "m.sc"],
    "bachelor": ["bachelor", "bachelors", "bsc", "b.sc", "undergraduate"],
    "degree": ["degree"],
    "diploma": ["diploma"],
}


@dataclass(frozen=True)
class ExtractedProfileData:
    full_name: str
    email: str | None
    phone: str | None
    skills: list[str]
    education: list[str]
    experience_years: float
    summary: str


@dataclass(frozen=True)
class ExtractedJobData:
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience_years: float
    education_requirements: list[str]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_profile(text: str) -> ExtractedProfileData:
    cleaned = normalize_text(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    full_name = _guess_name(lines)
    email = _find_email(text)
    phone = _find_phone(text)
    skills = extract_skills(text)
    education = extract_education(text)
    experience_years = extract_experience_years(text)
    summary = cleaned[:700]
    return ExtractedProfileData(full_name, email, phone, skills, education, experience_years, summary)


def extract_job(text: str) -> ExtractedJobData:
    skills = extract_skills(text)
    required = []
    preferred = []
    for skill in skills:
        context = _skill_context_kind(text, skill)
        if context == "preferred":
            preferred.append(skill)
        else:
            required.append(skill)
    return ExtractedJobData(
        required_skills=required or skills,
        preferred_skills=preferred,
        min_experience_years=extract_experience_years(text),
        education_requirements=extract_education(text),
    )


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    found = []
    for canonical, aliases in SKILL_CANONICAL.items():
        if any(_contains_phrase(lowered, alias) for alias in aliases):
            found.append(canonical)
    return sorted(found)


def extract_education(text: str) -> list[str]:
    lowered = text.lower()
    found = [
        canonical
        for canonical, aliases in EDUCATION_CANONICAL.items()
        if any(_contains_phrase(lowered, alias) for alias in aliases)
    ]
    if "bachelor" in found:
        found = [degree for degree in found if degree != "degree"]
    return sorted(set(found))


def extract_experience_years(text: str) -> float:
    lowered = text.lower()
    values = []
    for match in re.finditer(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\s+(?:of\s+)?experience", lowered):
        values.append(float(match.group(1)))
    for match in re.finditer(r"experience\s+(?:of\s+)?(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)", lowered):
        values.append(float(match.group(1)))
    return max(values) if values else 0.0


def _guess_name(lines: list[str]) -> str:
    for line in lines[:5]:
        if "@" not in line and not re.search(r"\d", line) and len(line.split()) <= 5:
            return line[:255]
    return "Unknown Candidate"


def _find_email(text: str) -> str | None:
    match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    return match.group(0) if match else None


def _find_phone(text: str) -> str | None:
    match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", text)
    return match.group(0).strip() if match else None


def _contains_phrase(text: str, phrase: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _skill_context_kind(text: str, skill: str) -> str:
    lowered = text.lower()
    skill_index = lowered.find(skill)
    if skill_index == -1:
        return "required"

    markers = {
        "preferred": ["preferred", "nice to have", "bonus", "advantage"],
        "required": ["required", "must have", "mandatory", "need"],
    }
    nearest_kind = "required"
    nearest_distance = 10_000
    for kind, keywords in markers.items():
        for keyword in keywords:
            marker_index = lowered.rfind(keyword, 0, skill_index + 1)
            if marker_index == -1:
                continue
            distance = skill_index - marker_index
            if distance < nearest_distance:
                nearest_kind = kind
                nearest_distance = distance
    return nearest_kind
