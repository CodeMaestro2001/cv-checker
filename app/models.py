from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Candidate(TimestampMixin, Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="Unknown Candidate")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_filename: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text)

    profile: Mapped["ExtractedProfile"] = relationship(back_populates="candidate", cascade="all, delete-orphan", uselist=False)
    matches: Mapped[list["MatchResult"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")


class ExtractedProfile(TimestampMixin, Base):
    __tablename__ = "extracted_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), unique=True)
    skills: Mapped[str] = mapped_column(Text, default="[]")
    education: Mapped[str] = mapped_column(Text, default="[]")
    experience_years: Mapped[float] = mapped_column(Float, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")

    candidate: Mapped[Candidate] = relationship(back_populates="profile")


class JobDescription(TimestampMixin, Base):
    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[str] = mapped_column(Text, default="[]")
    preferred_skills: Mapped[str] = mapped_column(Text, default="[]")
    min_experience_years: Mapped[float] = mapped_column(Float, default=0)
    education_requirements: Mapped[str] = mapped_column(Text, default="[]")

    matches: Mapped[list["MatchResult"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class MatchResult(TimestampMixin, Base):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_descriptions.id"), index=True)
    overall_score: Mapped[float] = mapped_column(Float)
    semantic_score: Mapped[float] = mapped_column(Float)
    skill_score: Mapped[float] = mapped_column(Float)
    experience_score: Mapped[float] = mapped_column(Float)
    education_score: Mapped[float] = mapped_column(Float)
    matched_skills: Mapped[str] = mapped_column(Text, default="[]")
    missing_skills: Mapped[str] = mapped_column(Text, default="[]")
    recommendation: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)

    candidate: Mapped[Candidate] = relationship(back_populates="matches")
    job: Mapped[JobDescription] = relationship(back_populates="matches")


class AuditEvent(TimestampMixin, Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(255), default="system")
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str] = mapped_column(String(120))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str] = mapped_column(Text, default="{}")
