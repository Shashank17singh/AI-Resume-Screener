"""Score a candidate's resume against a job description."""

from llm_client import call_json
from models import JobDescription, MatchResult, Resume

MATCH_SCHEMA = MatchResult.model_json_schema()


def score_candidate(job: JobDescription, resume: Resume) -> MatchResult:
    prompt = f"""You are an HR recruiter. Compare the candidate's resume with
the job description.

JOB DESCRIPTION:
{job.model_dump_json(indent=2)}

CANDIDATE RESUME:
{resume.model_dump_json(indent=2)}

Return JSON matching this schema:
{MATCH_SCHEMA}

Fill in:
1. candidate_name
2. matching_skills — skills the candidate has that the job needs
3. missing_skills — important required skills the candidate is missing
4. experience_requirement_met — true/false/null if the job gives no minimum
5. score — overall match percentage from 0 to 100
6. verdict — a short (1-2 sentence) final verdict

Keep it concise."""

    data = call_json(system_prompt="You are a precise, concise technical recruiter.",
                      user_prompt=prompt)
    data.setdefault("candidate_name", resume.name)
    return MatchResult(**data)
