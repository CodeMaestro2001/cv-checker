import os
from io import BytesIO

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


st.set_page_config(page_title="AI Resume Screening", page_icon="AI", layout="wide")

st.title("AI Resume Screening")
st.caption("Upload CVs, create a job profile, rank candidates, and review explainable match results.")


def api_get(path: str):
    response = requests.get(f"{API_BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def api_post(path: str, json=None, files=None):
    response = requests.post(f"{API_BASE_URL}{path}", json=json, files=files, timeout=60)
    response.raise_for_status()
    return response.json()


def api_delete(path: str):
    response = requests.delete(f"{API_BASE_URL}{path}", timeout=30)
    response.raise_for_status()


def load_jobs():
    try:
        return api_get("/jobs")
    except requests.RequestException as exc:
        st.error(f"API unavailable: {exc}")
        return []


def load_candidates():
    try:
        return api_get("/candidates")
    except requests.RequestException:
        return []


left, right = st.columns([0.36, 0.64], gap="large")

with left:
    st.subheader("Job Description")
    with st.form("job_form", clear_on_submit=False):
        title = st.text_input("Job title", value="Machine Learning Engineer")
        company = st.text_input("Company", value="Client Company")
        description = st.text_area(
            "Job description",
            height=220,
            value=(
                "We need a Machine Learning Engineer with 3+ years of experience in Python, "
                "Pandas, scikit-learn, NLP, FastAPI, Docker, SQL, and embeddings. "
                "Bachelor degree required. Experience with XGBoost and cloud deployment preferred."
            ),
        )
        submitted = st.form_submit_button("Create job")
        if submitted:
            try:
                job = api_post("/jobs", json={"title": title, "company": company, "description": description})
                st.success(f"Created job #{job['id']}: {job['title']}")
            except requests.RequestException as exc:
                st.error(f"Could not create job: {exc}")

    st.subheader("Candidate Upload")
    files = st.file_uploader("Upload CV files", type=["pdf", "docx", "txt"], accept_multiple_files=True)
    if st.button("Upload candidates", disabled=not files):
        for uploaded in files or []:
            try:
                file_bytes = BytesIO(uploaded.getvalue())
                result = api_post(
                    "/candidates/upload",
                    files={"file": (uploaded.name, file_bytes, uploaded.type or "application/octet-stream")},
                )
                st.success(f"Uploaded {result['full_name']} from {uploaded.name}")
            except requests.RequestException as exc:
                st.error(f"Could not upload {uploaded.name}: {exc}")

with right:
    jobs = load_jobs()
    candidates = load_candidates()

    st.subheader("Screening Workspace")
    if not jobs:
        st.info("Create a job description to begin ranking candidates.")
    else:
        job_options = {f"#{job['id']} - {job['title']}": job["id"] for job in jobs}
        job_select_col, job_remove_col = st.columns([0.82, 0.18], vertical_alignment="bottom")
        selected_label = job_select_col.selectbox("Active job", list(job_options.keys()))
        selected_job_id = job_options[selected_label]
        selected_job = next(job for job in jobs if job["id"] == selected_job_id)

        if job_remove_col.button("Remove job", key=f"remove_job_{selected_job_id}"):
            try:
                api_delete(f"/jobs/{selected_job_id}")
                st.session_state.pop("rankings", None)
                st.success(f"Removed job #{selected_job_id}: {selected_job['title']}")
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Could not remove job: {exc}")

        metric_cols = st.columns(3)
        metric_cols[0].metric("Jobs", len(jobs))
        metric_cols[1].metric("Candidates", len(candidates))
        metric_cols[2].metric("API", API_BASE_URL)

        if st.button("Rank all candidates", disabled=not candidates):
            try:
                rankings = api_get(f"/jobs/{selected_job_id}/rankings")
                st.session_state["rankings"] = rankings
            except requests.RequestException as exc:
                st.error(f"Could not rank candidates: {exc}")

        rankings = st.session_state.get("rankings", [])
        if rankings:
            display_rows = [
                {
                    "Candidate": row["candidate_name"],
                    "Overall": row["overall_score"],
                    "Skills": row["skill_score"],
                    "Semantic": row["semantic_score"],
                    "Experience": row["experience_score"],
                    "Education": row["education_score"],
                    "Recommendation": row["recommendation"],
                }
                for row in rankings
            ]
            st.dataframe(display_rows, hide_index=True, use_container_width=True)

            selected_candidate = st.selectbox("Candidate detail", [row["candidate_name"] for row in rankings])
            detail = next(row for row in rankings if row["candidate_name"] == selected_candidate)

            detail_cols = st.columns(2)
            with detail_cols[0]:
                st.markdown("**Matched skills**")
                st.write(", ".join(detail["matched_skills"]) or "None")
                st.markdown("**Missing required skills**")
                st.write(", ".join(detail["missing_skills"]) or "None")
            with detail_cols[1]:
                st.markdown("**Recommendation**")
                st.write(detail["recommendation"])
                st.markdown("**Explanation**")
                st.write(detail["explanation"])

            csv_url = f"{API_BASE_URL}/jobs/{selected_job_id}/rankings.csv"
            st.link_button("Download CSV", csv_url)
        elif candidates:
            st.info("Click rank all candidates to generate match results.")

st.divider()
st.subheader("Candidate Inventory")
if candidates:
    header_cols = st.columns([0.18, 0.2, 0.08, 0.34, 0.14, 0.06])
    header_cols[0].markdown("**Name**")
    header_cols[1].markdown("**Email**")
    header_cols[2].markdown("**Experience**")
    header_cols[3].markdown("**Skills**")
    header_cols[4].markdown("**File**")
    header_cols[5].markdown("**Remove**")

    for candidate in candidates:
        row_cols = st.columns([0.18, 0.2, 0.08, 0.34, 0.14, 0.06])
        row_cols[0].write(candidate["full_name"])
        row_cols[1].write(candidate["email"] or "-")
        row_cols[2].write(candidate["experience_years"])
        row_cols[3].write(", ".join(candidate["skills"]) or "-")
        row_cols[4].write(candidate["source_filename"])
        if row_cols[5].button("Remove", key=f"remove_candidate_{candidate['id']}"):
            try:
                api_delete(f"/candidates/{candidate['id']}")
                st.session_state.pop("rankings", None)
                st.success(f"Removed {candidate['full_name']}")
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Could not remove {candidate['full_name']}: {exc}")
else:
    st.write("No candidates uploaded yet.")
