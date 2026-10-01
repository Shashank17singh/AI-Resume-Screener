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

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif !important;
}

.stApp {
    background-color: #F8FAFC;
    color: #0F172A;
}

[data-testid="stHeader"] {
    background-color: rgba(248,250,252,0.9) !important;
}

h1, h2, h3, h4, h5, h6 {
    color: #1E3A5F !important;
    font-weight: 700 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #E9EEF5 !important;
    border-right: 1px solid #CBD5E1;
}

/* Metric styling */
[data-testid="stMetricValue"] {
    color: #2563EB !important;
    font-weight: 700;
}

[data-testid="stMetricLabel"] {
    color: #475569 !important;
    font-weight: 500;
    text-transform: uppercase;
    font-size: 0.85rem;
}

/* Primary Buttons */
.stButton > button[kind="primary"] {
    background-color: #1E3A5F;
    color: #FFFFFF;
    font-weight: 600;
    border: none;
    border-radius: 4px;
    transition: all 0.2s ease;
}

.stButton > button[kind="primary"]:hover {
    background-color: #2563EB;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

/* Containers / Expanders */
[data-testid="stExpander"], [data-testid="stVerticalBlock"] > div > div > div[data-testid="stContainer"] {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

/* Inputs */
.stTextArea > div > div > textarea, .stFileUploader > div > div {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    color: #0F172A;
}
.stTextArea > div > div > textarea:focus {
    border-color: #2563EB;
    box-shadow: 0 0 0 2px rgba(37,99,235,0.2);
}

hr {
    border-color: #CBD5E1 !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

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
    use_cache = st.checkbox(
        "Cache parsed resumes (skip re-parsing on rerun)", value=True
    )
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
            progress_bar.progress(
                index / total, text=f"Processing {file_name} ({index}/{total})"
            )
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
                cols[0].markdown(
                    f"**#{rank} - {m.candidate_name or result.file_name}**"
                )
                cols[1].metric("Match score", f"{m.score:.0f}%")
                if m.experience_requirement_met is not None:
                    st.caption(
                        " Meets experience requirement"
                        if m.experience_requirement_met
                        else " Does not meet stated experience requirement"
                    )
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Matching skills**")
                    st.write(", ".join(m.matching_skills) or "-")
                with col_b:
                    st.markdown("**Missing skills**")
                    st.write(", ".join(m.missing_skills) or "-")
                st.markdown(f"_{m.verdict}_")
    if run.failures:
        st.subheader(f"Could not process ({len(run.failures)})")
        for result in run.failures:
            st.warning(f"{result.file_name}: {result.error}")
