"""Batch-screen a folder of resumes against a job description.

Improvements over a naive loop:
- Per-file try/except so one corrupt/unreadable resume doesn't kill the
  whole batch — it's reported as a failure and the run continues.
- In-memory cache (by file hash) for parsed resumes, so re-running the
  screener against a new/edited job description doesn't re-spend LLM
  calls re-parsing resumes that haven't changed. The cache is injected
  by the caller (e.g. Streamlit session state) rather than written to
  shared disk, so parsed resumes — which contain candidate PII — never
  persist across users/sessions on a shared server.
- Returns structured results instead of only printing to console, so
  the same pipeline can back a CLI, a Streamlit UI, or tests.
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from file_readers import SUPPORTED_EXTENSIONS, read_resume
from llm_client import LLMError
from models import JobDescription, MatchResult, Resume
from parsing import parse_resume
from scorer import score_candidate


@dataclass
class CandidateResult:
    file_name: str
    resume: Resume | None
    match: MatchResult | None
    error: str | None = None


@dataclass
class ScreeningRun:
    results: list[CandidateResult] = field(default_factory=list)

    @property
    def successes(self) -> list[CandidateResult]:
        return [r for r in self.results if r.error is None]

    @property
    def failures(self) -> list[CandidateResult]:
        return [r for r in self.results if r.error is not None]

    def ranked(self) -> list[CandidateResult]:
        return sorted(self.successes, key=lambda r: r.match.score, reverse=True)


def _file_hash(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]


def _cached_resume(cache: dict[str, Resume], file_path: Path) -> Resume | None:
    return cache.get(_file_hash(file_path))


def _store_resume_cache(cache: dict[str, Resume], file_path: Path, resume: Resume) -> None:
    cache[_file_hash(file_path)] = resume


def screen_folder(
    resume_folder: Path,
    job: JobDescription,
    use_cache: bool = True,
    cache: dict[str, Resume] | None = None,
    on_progress=None,
) -> ScreeningRun:
    """Parse and score every resume in `resume_folder` against `job`.

    `cache` is an in-memory dict the caller owns (e.g. Streamlit
    `session_state`) — resumes are never written to shared disk, so
    candidate PII doesn't persist beyond the caller's own session.
    `on_progress(file_name, index, total)` is called before each file is
    processed, if provided — useful for a progress bar in a UI.
    """
    if cache is None:
        cache = {}

    files = sorted(
        p for p in resume_folder.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    run = ScreeningRun()

    for i, file_path in enumerate(files, start=1):
        if on_progress:
            on_progress(file_path.name, i, len(files))

        try:
            resume = _cached_resume(cache, file_path) if use_cache else None
            if resume is None:
                text = read_resume(file_path)
                if not text.strip():
                    raise ValueError("No extractable text (scanned/empty file?)")
                resume = parse_resume(text)
                if use_cache:
                    _store_resume_cache(cache, file_path, resume)

            match = score_candidate(job, resume)
            run.results.append(CandidateResult(file_path.name, resume, match))
        except (LLMError, ValueError, Exception) as exc:  # noqa: BLE001
            run.results.append(CandidateResult(file_path.name, None, None, str(exc)))

    return run
