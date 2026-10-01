"""Data models shared across the resume screener."""
from pydantic import BaseModel, Field
class JobDescription(BaseModel):
    """
    Structured representation of a parsed job description.
    """
    role: str
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    minimum_experience: float | None = None
    education_requirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
class Experience(BaseModel):
    """
    Structured representation of a candidate's work experience.
    """
    company: str | None = None
    role: str | None = None
    duration: str | None = None
    description: str | None = None
    skills_used: list[str] = Field(default_factory=list)
class Resume(BaseModel):
    """
    Structured representation of a parsed resume.
    """
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    total_experience_years: float | None = None
    skills: list[str] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
class MatchResult(BaseModel):
    """
    Result of evaluating a candidate's resume against a job description.
    """
    candidate_name: str | None = None
    score: float
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    experience_requirement_met: bool | None = None
    verdict: str = ""
