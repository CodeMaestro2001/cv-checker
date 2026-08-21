# AI Resume Screening & Job Matching System

Enterprise-style MVP for screening CVs against job descriptions. Recruiters can upload resumes, add a job description, rank candidates, review missing skills, and export results.

## Features

- FastAPI backend with structured scoring endpoints
- Streamlit recruiter dashboard
- PDF, DOCX, and TXT resume text extraction
- Skill, education, and experience extraction
- Weighted match score with explainable score components
- Candidate ranking and CSV export
- SQLite for local development, PostgreSQL-ready via `DATABASE_URL`
- Docker Compose deployment files
- Pytest coverage for extraction, scoring, and API flow

## Local Setup

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

In another terminal:

```powershell
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements-ui.txt
streamlit run ui/streamlit_app.py
```

API: `http://localhost:8000`

UI: `http://localhost:8501`

## Docker

```powershell
copy .env.example .env
docker compose up --build
```

For Postgres, set:

```env
DATABASE_URL=postgresql+psycopg://resume:resume@db:5432/resume_screening
```

## API Flow

1. `POST /jobs` creates a job description.
2. `POST /candidates/upload` uploads and extracts a CV.
3. `POST /matches/score` scores one candidate against one job.
4. `GET /jobs/{job_id}/rankings` ranks all candidates for a job.

## Notes

The default scorer is a local hybrid scorer. It combines skill overlap, semantic similarity, experience fit, and education fit. When `ENABLE_ML_MODEL=true` and `MATCH_MODEL_PATH` points to a trained artifact, the API uses that trained classifier for the final match score while keeping the hybrid component scores for explainability. A hosted LLM can be added later behind `ENABLE_HOSTED_LLM` for enhanced extraction or recruiter-facing summaries.

For experimentation with heavier ML models, install:

```powershell
pip install -r requirements-ml.txt
```

Then train a labeled matching model:

```powershell
python train_model.py --data data/training_samples.csv --output-dir models
```

Training data must contain these columns:

- `resume_text`
- `job_text`
- `label`

Labels can be `poor`, `average`, `good` or numeric `0`, `1`, `2`. The script compares Logistic Regression, Random Forest, and XGBoost when XGBoost is installed, then saves `models/match_model.joblib` and `models/metrics.json`.

The API loads the saved model automatically by default:

```env
ENABLE_ML_MODEL=true
MATCH_MODEL_PATH=models/match_model.joblib
```

Set `ENABLE_ML_MODEL=false` to use only the baseline weighted scorer.
