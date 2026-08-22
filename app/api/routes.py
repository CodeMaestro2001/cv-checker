import csv
from io import StringIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app import models
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas import CandidateRead, JobCreate, JobRead, MatchRead, ScoreRequest
from app.services.json_utils import loads_list
from app.services.nlp import extract_job, extract_profile
from app.services.ml_matching import apply_ml_matcher
from app.services.repository import (
    candidate_to_schema,
    create_candidate,
    create_job,
    delete_candidate,
    delete_job,
    job_to_schema,
    match_to_schema,
    save_match,
)
from app.services.scoring import ScoreInput, score_match
from app.services.text_extraction import UnsupportedFileType, extract_text_from_bytes

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/jobs", response_model=JobRead)
def create_job_description(payload: JobCreate, db: Session = Depends(get_db)) -> JobRead:
    job_data = extract_job(payload.description)
    job = create_job(db, payload.title, payload.company, payload.description, job_data)
    return job_to_schema(job)


@router.get("/jobs", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)) -> list[JobRead]:
    jobs = db.scalars(select(models.JobDescription).order_by(desc(models.JobDescription.created_at))).all()
    return [job_to_schema(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobRead:
    job = db.get(models.JobDescription, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_schema(job)


@router.delete("/jobs/{job_id}", status_code=204)
def remove_job(job_id: int, db: Session = Depends(get_db)) -> None:
    job = db.get(models.JobDescription, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    delete_job(db, job)


@router.post("/candidates/upload", response_model=CandidateRead)
async def upload_candidate(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CandidateRead:
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit")
    try:
        raw_text = extract_text_from_bytes(file.filename or "resume.txt", content)
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    if len(raw_text.strip()) < 20:
        raise HTTPException(status_code=422, detail="Could not extract enough text from resume")
    profile = extract_profile(raw_text)
    candidate = create_candidate(db, file.filename or "resume.txt", raw_text, profile)
    return candidate_to_schema(candidate)


@router.get("/candidates", response_model=list[CandidateRead])
def list_candidates(db: Session = Depends(get_db)) -> list[CandidateRead]:
    candidates = db.scalars(
        select(models.Candidate).options(joinedload(models.Candidate.profile)).order_by(desc(models.Candidate.created_at))
    ).all()
    return [candidate_to_schema(candidate) for candidate in candidates]


@router.get("/candidates/{candidate_id}", response_model=CandidateRead)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)) -> CandidateRead:
    candidate = db.scalar(
        select(models.Candidate).options(joinedload(models.Candidate.profile)).where(models.Candidate.id == candidate_id)
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate_to_schema(candidate)


@router.delete("/candidates/{candidate_id}", status_code=204)
def remove_candidate(candidate_id: int, db: Session = Depends(get_db)) -> None:
    candidate = db.scalar(
        select(models.Candidate).options(joinedload(models.Candidate.profile)).where(models.Candidate.id == candidate_id)
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    delete_candidate(db, candidate)


@router.post("/matches/score", response_model=MatchRead)
def score_candidate(
    payload: ScoreRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MatchRead:
    candidate = db.scalar(
        select(models.Candidate).options(joinedload(models.Candidate.profile)).where(models.Candidate.id == payload.candidate_id)
    )
    job = db.get(models.JobDescription, payload.job_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    score = _score(candidate, job, settings)
    match = save_match(db, candidate.id, job.id, score)
    match.candidate = candidate
    match.job = job
    return match_to_schema(match)


@router.get("/jobs/{job_id}/rankings", response_model=list[MatchRead])
def rank_candidates(
    job_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[MatchRead]:
    return _rank_candidates(job_id, db, settings)


def _rank_candidates(job_id: int, db: Session, settings: Settings) -> list[MatchRead]:
    job = db.get(models.JobDescription, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidates = db.scalars(select(models.Candidate).options(joinedload(models.Candidate.profile))).all()
    for candidate in candidates:
        save_match(db, candidate.id, job.id, _score(candidate, job, settings))

    matches = db.scalars(
        select(models.MatchResult)
        .options(joinedload(models.MatchResult.candidate), joinedload(models.MatchResult.job))
        .where(models.MatchResult.job_id == job_id)
        .order_by(desc(models.MatchResult.overall_score))
    ).all()
    return [match_to_schema(match) for match in matches]


@router.get("/jobs/{job_id}/rankings.csv")
def export_rankings(
    job_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    rankings = _rank_candidates(job_id, db, settings)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["candidate_id", "candidate_name", "overall_score", "matched_skills", "missing_skills", "recommendation"])
    for row in rankings:
        writer.writerow(
            [
                row.candidate_id,
                row.candidate_name,
                row.overall_score,
                "; ".join(row.matched_skills),
                "; ".join(row.missing_skills),
                row.recommendation,
            ]
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=job-{job_id}-rankings.csv"},
    )


def _score(candidate: models.Candidate, job: models.JobDescription, settings: Settings):
    profile = candidate.profile
    baseline = score_match(
        ScoreInput(
            candidate_text=candidate.raw_text,
            job_text=job.raw_text,
            candidate_skills=loads_list(profile.skills),
            required_skills=loads_list(job.required_skills),
            preferred_skills=loads_list(job.preferred_skills),
            candidate_experience_years=profile.experience_years,
            min_experience_years=job.min_experience_years,
            candidate_education=loads_list(profile.education),
            education_requirements=loads_list(job.education_requirements),
        )
    )
    return apply_ml_matcher(baseline, candidate.raw_text, job.raw_text, settings)
