from datetime import datetime

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    description: str = Field(min_length=20)


class JobRead(BaseModel):
    id: int
    title: str
    company: str | None
    raw_text: str
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience_years: float
    education_requirements: list[str]
    created_at: datetime


class CandidateRead(BaseModel):
    id: int
    full_name: str
    email: str | None
    phone: str | None
    source_filename: str
    skills: list[str]
    education: list[str]
    experience_years: float
    summary: str
    created_at: datetime


class ScoreRequest(BaseModel):
    candidate_id: int
    job_id: int


class MatchRead(BaseModel):
    id: int
    candidate_id: int
    candidate_name: str
    job_id: int
    overall_score: float
    semantic_score: float
    skill_score: float
    experience_score: float
    education_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    recommendation: str
    explanation: str
    created_at: datetime
