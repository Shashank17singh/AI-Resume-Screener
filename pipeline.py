"""
Coordinates the end-to-end resume screening pipeline:
File reading -> Parsing -> Scoring -> Ranking.
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


def _store_resume_cache(
    cache: dict[str, Resume], file_path: Path, resume: Resume
) -> None:
    cache[_file_hash(file_path)] = resume


def screen_folder(
    resume_folder: Path,
    job: JobDescription,
    use_cache: bool = True,
    cache: dict[str, Resume] | None = None,
    on_progress=None,
) -> ScreeningRun:
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
        except (LLMError, ValueError, Exception) as exc:
            run.results.append(CandidateResult(file_path.name, None, None, str(exc)))
    return run
