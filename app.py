"""
Streamlit UI for the AI Resume Screener.
Orchestrates resume parsing, LLM candidate scoring, and ranking pipelines with an enterprise talent ATS design.
"""

import tempfile
from pathlib import Path

import streamlit as st

from llm_client import LLMError
from parsing import parse_job_description
from pipeline import safe_filename, screen_folder

st.set_page_config(page_title="AI Resume Screener & ATS Shortlist", layout="wide")

CUSTOM_CSS = """
<style>
/* Hallmark & UI/UX Pro Max Design System · Enterprise Talent ATS
 * Theme: Modern Dark Slate (#0d1117) with Emerald Accent (#10b981)
 */
:root {
  --bg-canvas: #0d1117;
  --bg-surface: #161b22;
  --bg-surface-elevated: #21262d;
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-default: #30363d;
  --border-focus: #10b981;
  --text-primary: #f0f6fc;
  --text-secondary: #8b949e;
  --accent-primary: #10b981;
  --accent-hover: #059669;
  --pill-green-bg: rgba(16, 185, 129, 0.15);
  --pill-green-border: rgba(16, 185, 129, 0.35);
  --pill-slate-bg: rgba(148, 163, 184, 0.12);
  --pill-slate-border: rgba(148, 163, 184, 0.25);
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}

.stApp {
  background-color: var(--bg-canvas) !important;
  color: var(--text-primary) !important;
}

[data-testid="stHeader"] {
  background: transparent !important;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
  background-color: var(--bg-surface) !important;
  border-right: 1px solid var(--border-subtle) !important;
}

/* Form inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
[data-baseweb="textarea"] > textarea {
  background-color: var(--bg-canvas) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-primary) !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
[data-baseweb="textarea"]:focus-within {
  border-color: var(--border-focus) !important;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.25) !important;
}

/* Buttons */
.stButton > button[kind="primary"] {
  background-color: var(--accent-primary) !important;
  border: 1px solid var(--accent-primary) !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  border-radius: var(--radius-sm) !important;
  transition: background-color 0.15s ease !important;
}

.stButton > button[kind="primary"]:hover {
  background-color: var(--accent-hover) !important;
}

/* Candidate Card Containers */
.candidate-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.ats-badge {
  display: inline-block;
  background-color: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #34d399;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.2rem 0.6rem;
  border-radius: 9999px;
  margin-bottom: 0.5rem;
}

.skill-chip-match {
  display: inline-block;
  background-color: var(--pill-green-bg);
  border: 1px solid var(--pill-green-border);
  color: #6ee7b7;
  font-size: 0.8rem;
  font-weight: 500;
  padding: 0.2rem 0.55rem;
  border-radius: 4px;
  margin: 0.2rem 0.2rem 0.2rem 0;
}

.skill-chip-missing {
  display: inline-block;
  background-color: var(--pill-slate-bg);
  border: 1px solid var(--pill-slate-border);
  color: #94a3b8;
  font-size: 0.8rem;
  font-weight: 500;
  padding: 0.2rem 0.55rem;
  border-radius: 4px;
  margin: 0.2rem 0.2rem 0.2rem 0;
}

[data-testid="stMetricValue"] {
  color: var(--accent-primary) !important;
  font-weight: 700 !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div style="margin-bottom: 1.5rem;">
        <span class="ats-badge">Talent Intelligence</span>
        <h1 style="margin: 0.25rem 0 0.5rem 0; font-size: 2rem; font-weight: 700;">AI Resume Screener & ATS Shortlist</h1>
        <p style="color: var(--text-secondary); margin: 0; font-size: 0.95rem;">
            Automated semantic matching, experience verification, and candidate shortlisting against job specifications.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if "resume_cache" not in st.session_state:
    st.session_state.resume_cache = {}

with st.sidebar:
    st.subheader("1. Job Specification")
    job_text = st.text_area(
        "Job Description Text",
        height=280,
        placeholder="Paste full job description, required qualifications, and core tech stack...",
    )

    st.subheader("2. Candidate Resumes")
    uploaded_files = st.file_uploader(
        "Upload Resumes (PDF / DOCX)",
        type=["pdf", "docx"],
        accept_multiple_files=True,
    )

    use_cache = st.checkbox(
        "Cache parsed resumes across runs",
        value=True,
        help="Avoids re-extracting unchanged resumes on subsequent reruns.",
    )
    st.write("")
    run_button = st.button("Screen Candidates", type="primary", use_container_width=True)

if run_button:
    if not job_text.strip():
        st.error("Please provide a job description in the sidebar.")
        st.stop()
    if not uploaded_files:
        st.error("Please upload at least one candidate resume.")
        st.stop()

    with st.spinner("Extracting job criteria & skill taxonomy..."):
        try:
            job = parse_job_description(job_text)
        except LLMError as exc:
            st.error(f"Error parsing job description: {exc}")
            st.stop()

    with st.expander("Parsed Job Requirements & Taxonomy", expanded=False):
        st.json(job.model_dump())

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        for uploaded in uploaded_files:
            (tmp_path / safe_filename(uploaded.name)).write_bytes(uploaded.getvalue())

        progress_bar = st.progress(0.0, text="Evaluating candidates...")

        def on_progress(file_name: str, index: int, total: int) -> None:
            progress_bar.progress(
                index / total, text=f"Analyzing {file_name} ({index}/{total})"
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
        st.subheader(f"Ranked Candidate Shortlist ({len(ranked)})")
        for rank, result in enumerate(ranked, start=1):
            m = result.match
            with st.container(border=True):
                cols = st.columns([3, 1])
                candidate_title = m.candidate_name or result.file_name
                cols[0].markdown(f"### #{rank} — {candidate_title}")
                cols[1].metric("Match Score", f"{m.score:.0f}%")

                if m.experience_requirement_met is not None:
                    exp_badge = (
                        "Meets required experience threshold"
                        if m.experience_requirement_met
                        else "Does not meet required experience threshold"
                    )
                    st.caption(exp_badge)

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Matching Skills:**")
                    if m.matching_skills:
                        chips = "".join(f'<span class="skill-chip-match">{s}</span>' for s in m.matching_skills)
                        st.markdown(chips, unsafe_allow_html=True)
                    else:
                        st.caption("No direct skill matches identified")

                with col_b:
                    st.markdown("**Skill Gaps / Missing:**")
                    if m.missing_skills:
                        chips = "".join(f'<span class="skill-chip-missing">{s}</span>' for s in m.missing_skills)
                        st.markdown(chips, unsafe_allow_html=True)
                    else:
                        st.caption("No significant skill gaps identified")

                st.write("")
                st.markdown(f"**Evaluation Summary:** _{m.verdict}_")

    if run.failures:
        st.subheader(f"Ingestion Exceptions ({len(run.failures)})")
        for result in run.failures:
            st.warning(f"{result.file_name}: {result.error}")
