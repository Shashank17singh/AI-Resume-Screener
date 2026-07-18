"""Turn free-text job descriptions and resumes into structured data via the LLM."""

from llm_client import call_json
from models import JobDescription, Resume

JOB_SCHEMA = JobDescription.model_json_schema()
RESUME_SCHEMA = Resume.model_json_schema()


def parse_job_description(job_text: str) -> JobDescription:
    system_prompt = f"""You are an expert HR assistant. Analyze job descriptions
and extract structured information from them.

Return ONLY valid JSON matching this schema:
{JOB_SCHEMA}

Rules:
- Do NOT return the schema itself, or fields like "properties", "title", "type".
- Fill the schema with actual information extracted from the job description.
- If minimum experience is not mentioned, return null.
- If information for a list is missing, return an empty list.
- Do not invent information."""

    user_prompt = f"Analyze the following job description:\n\n{job_text}"
    data = call_json(system_prompt, user_prompt)
    return JobDescription(**data)


def parse_resume(resume_text: str) -> Resume:
    system_prompt = f"""You are an expert resume parser. Extract information
from the resume based on its meaning, not only exact section headings.
Different resumes use different headings (Experience, Professional
Experience, Work History, Employment, Internships, etc.) — treat all of
these as relevant experience. Skills may appear in a skills section, in
work experience, in internships, or in projects.

Return ONLY valid JSON matching this schema:
{RESUME_SCHEMA}

Rules:
1. Do not invent information.
2. If a value is not available, return null.
3. If a list has no information, return an empty list.
4. Include internships inside experiences.
5. Extract skills mentioned across the entire resume, not just the skills section."""

    user_prompt = f"Parse the following resume:\n\n{resume_text}"
    data = call_json(system_prompt, user_prompt)
    return Resume(**data)
