from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.schemas import CandidateRead, JobRead, MatchRead
from app.services.json_utils import dumps, loads_list
from app.services.nlp import ExtractedJobData, ExtractedProfileData
from app.services.scoring import ScoreOutput


def create_audit_event(db: Session, action: str, entity_type: str, entity_id: int | None, details: dict) -> None:
    db.add(models.AuditEvent(action=action, entity_type=entity_type, entity_id=entity_id, details=dumps(details)))


def create_candidate(db: Session, filename: str, raw_text: str, profile: ExtractedProfileData) -> models.Candidate:
    candidate = models.Candidate(
        full_name=profile.full_name,
        email=profile.email,
        phone=profile.phone,
        source_filename=filename,
        raw_text=raw_text,
    )
    candidate.profile = models.ExtractedProfile(
        skills=dumps(profile.skills),
        education=dumps(profile.education),
        experience_years=profile.experience_years,
        summary=profile.summary,
    )
    db.add(candidate)
    db.flush()
    create_audit_event(db, "candidate_uploaded", "candidate", candidate.id, {"filename": filename})
    db.commit()
    db.refresh(candidate)
    return candidate


def create_job(db: Session, title: str, company: str | None, raw_text: str, job_data: ExtractedJobData) -> models.JobDescription:
    job = models.JobDescription(
        title=title,
        company=company,
        raw_text=raw_text,
        required_skills=dumps(job_data.required_skills),
        preferred_skills=dumps(job_data.preferred_skills),
        min_experience_years=job_data.min_experience_years,
        education_requirements=dumps(job_data.education_requirements),
    )
    db.add(job)
    db.flush()
    create_audit_event(db, "job_created", "job", job.id, {"title": title})
    db.commit()
    db.refresh(job)
    return job


def save_match(db: Session, candidate_id: int, job_id: int, score: ScoreOutput) -> models.MatchResult:
    existing = db.scalar(
        select(models.MatchResult).where(
            models.MatchResult.candidate_id == candidate_id,
            models.MatchResult.job_id == job_id,
        )
    )
    match = existing or models.MatchResult(candidate_id=candidate_id, job_id=job_id)
    match.overall_score = score.overall_score
    match.semantic_score = score.semantic_score
    match.skill_score = score.skill_score
    match.experience_score = score.experience_score
    match.education_score = score.education_score
    match.matched_skills = dumps(score.matched_skills)
    match.missing_skills = dumps(score.missing_skills)
    match.recommendation = score.recommendation
    match.explanation = score.explanation
    db.add(match)
    db.flush()
    create_audit_event(db, "match_scored", "match", match.id, {"candidate_id": candidate_id, "job_id": job_id})
    db.commit()
    db.refresh(match)
    return match


def candidate_to_schema(candidate: models.Candidate) -> CandidateRead:
    profile = candidate.profile
    return CandidateRead(
        id=candidate.id,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        source_filename=candidate.source_filename,
        skills=loads_list(profile.skills),
        education=loads_list(profile.education),
        experience_years=profile.experience_years,
        summary=profile.summary,
        created_at=candidate.created_at,
    )


def job_to_schema(job: models.JobDescription) -> JobRead:
    return JobRead(
        id=job.id,
        title=job.title,
        company=job.company,
        raw_text=job.raw_text,
        required_skills=loads_list(job.required_skills),
        preferred_skills=loads_list(job.preferred_skills),
        min_experience_years=job.min_experience_years,
        education_requirements=loads_list(job.education_requirements),
        created_at=job.created_at,
    )


def match_to_schema(match: models.MatchResult) -> MatchRead:
    return MatchRead(
        id=match.id,
        candidate_id=match.candidate_id,
        candidate_name=match.candidate.full_name,
        job_id=match.job_id,
        overall_score=match.overall_score,
        semantic_score=match.semantic_score,
        skill_score=match.skill_score,
        experience_score=match.experience_score,
        education_score=match.education_score,
        matched_skills=loads_list(match.matched_skills),
        missing_skills=loads_list(match.missing_skills),
        recommendation=match.recommendation,
        explanation=match.explanation,
        created_at=match.created_at,
    )
