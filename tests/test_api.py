from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.core.database import Base, get_db
from app.main import app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_end_to_end_api_flow(client: TestClient):
    job_response = client.post(
        "/jobs",
        json={
            "title": "ML Engineer",
            "company": "Client",
            "description": "Required Python FastAPI Docker SQL NLP. Bachelor degree. 3 years of experience.",
        },
    )
    assert job_response.status_code == 200
    job = job_response.json()

    resume = (
        "Alex Perera\nalex@example.com\nMachine Learning Engineer with 4 years of experience "
        "in Python, FastAPI, Docker, SQL and NLP. Bachelor degree."
    )
    candidate_response = client.post(
        "/candidates/upload",
        files={"file": ("resume.txt", resume.encode("utf-8"), "text/plain")},
    )
    assert candidate_response.status_code == 200
    candidate = candidate_response.json()

    score_response = client.post("/matches/score", json={"candidate_id": candidate["id"], "job_id": job["id"]})
    assert score_response.status_code == 200
    assert score_response.json()["overall_score"] > 80

    rankings_response = client.get(f"/jobs/{job['id']}/rankings")
    assert rankings_response.status_code == 200
    assert rankings_response.json()[0]["candidate_name"] == "Alex Perera"
