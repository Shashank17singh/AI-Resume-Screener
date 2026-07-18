"""Streamlit front-end for the AI resume screener.

Run with: streamlit run app.py
"""

import tempfile
from pathlib import Path

import streamlit as st

from llm_client import LLMError
from parsing import parse_job_description
from pipeline import screen_folder

st.set_page_config(page_title="AI Resume Screener", layout="wide")
st.title("AI Resume Screener")
st.caption("Paste a job description, upload resumes, get a ranked shortlist.")

if "resume_cache" not in st.session_state:
    st.session_state.resume_cache = {}

with st.sidebar:
    st.header("1. Job description")
    job_text = st.text_area("Paste the job description", height=300)

    st.header("2. Resumes")
    uploaded_files = st.file_uploader(
        "Upload PDF or DOCX resumes", type=["pdf", "docx"], accept_multiple_files=True
    )

    use_cache = st.checkbox("Cache parsed resumes (skip re-parsing on rerun)", value=True)
    run_button = st.button("Screen candidates", type="primary")

if run_button:
    if not job_text.strip():
        st.error("Paste a job description first.")
        st.stop()
    if not uploaded_files:
        st.error("Upload at least one resume.")
        st.stop()

    with st.spinner("Reading the job description..."):
        try:
            job = parse_job_description(job_text)
        except LLMError as exc:
            st.error(f"Couldn't parse the job description: {exc}")
            st.stop()

    with st.expander("Parsed job requirements", expanded=False):
        st.json(job.model_dump())

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        for uploaded in uploaded_files:
            (tmp_path / uploaded.name).write_bytes(uploaded.getvalue())

        progress_bar = st.progress(0.0, text="Starting...")

        def on_progress(file_name: str, index: int, total: int) -> None:
            progress_bar.progress(index / total, text=f"Processing {file_name} ({index}/{total})")

        run = screen_folder(
            tmp_path,
            job,
            use_cache=use_cache,
            cache=st.session_state.resume_cache,
            on_progress=on_progress,
        )
        progress_bar.empty()

    ranked = run.ranked()

    if ranked:
        st.subheader(f"Ranked candidates ({len(ranked)})")
        for rank, result in enumerate(ranked, start=1):
            m = result.match
            with st.container(border=True):
                cols = st.columns([3, 1])
                cols[0].markdown(f"**#{rank} — {m.candidate_name or result.file_name}**")
                cols[1].metric("Match score", f"{m.score:.0f}%")

                if m.experience_requirement_met is not None:
                    st.caption(
                        "✅ Meets experience requirement"
                        if m.experience_requirement_met
                        else "⚠️ Does not meet stated experience requirement"
                    )

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Matching skills**")
                    st.write(", ".join(m.matching_skills) or "—")
                with col_b:
                    st.markdown("**Missing skills**")
                    st.write(", ".join(m.missing_skills) or "—")

                st.markdown(f"_{m.verdict}_")

    if run.failures:
        st.subheader(f"Could not process ({len(run.failures)})")
        for result in run.failures:
            st.warning(f"{result.file_name}: {result.error}")
