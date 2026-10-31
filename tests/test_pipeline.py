from pathlib import Path
from types import SimpleNamespace

import pytest

import pipeline
from file_readers import UnsupportedFileTypeError, read_resume
from models import JobDescription, Resume


def make_job() -> JobDescription:
    return JobDescription.model_construct()


def make_resume() -> Resume:
    return Resume.model_construct()


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    (tmp_path / "alice.pdf").write_bytes(b"alice")
    (tmp_path / "bob.pdf").write_bytes(b"bob")
    (tmp_path / "notes.txt").write_text("ignored")
    return tmp_path


def use_fakes(monkeypatch: pytest.MonkeyPatch, scores: dict[str, int]) -> list[str]:
    parsed: list[str] = []

    def fake_parse(text: str) -> Resume:
        parsed.append(text)
        resume = make_resume()
        object.__setattr__(resume, "__dict__", {**resume.__dict__, "source": text})
        return resume

    def fake_score(_job: JobDescription, resume: Resume) -> SimpleNamespace:
        return SimpleNamespace(score=scores[resume.__dict__["source"]])

    monkeypatch.setattr(pipeline, "read_resume", lambda path: path.read_text())
    monkeypatch.setattr(pipeline, "parse_resume", fake_parse)
    monkeypatch.setattr(pipeline, "score_candidate", fake_score)
    return parsed


def test_candidates_are_ranked_by_score(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_fakes(monkeypatch, {"alice": 40, "bob": 90})

    run = pipeline.screen_folder(folder, make_job())

    assert [result.file_name for result in run.ranked()] == ["bob.pdf", "alice.pdf"]


def test_unsupported_files_are_skipped(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_fakes(monkeypatch, {"alice": 1, "bob": 2})

    run = pipeline.screen_folder(folder, make_job())

    assert len(run.results) == 2


def test_the_cache_avoids_parsing_a_file_twice(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parsed = use_fakes(monkeypatch, {"alice": 1, "bob": 2})
    cache: dict[str, Resume] = {}

    pipeline.screen_folder(folder, make_job(), cache=cache)
    pipeline.screen_folder(folder, make_job(), cache=cache)

    assert len(parsed) == 2


def test_an_empty_resume_is_reported_without_stopping_the_run(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_fakes(monkeypatch, {"bob": 2})
    (folder / "alice.pdf").write_text("   ")

    run = pipeline.screen_folder(folder, make_job())

    assert [result.file_name for result in run.successes] == ["bob.pdf"]
    assert "No extractable text" in run.failures[0].error


def test_progress_is_reported_for_each_file(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_fakes(monkeypatch, {"alice": 1, "bob": 2})
    seen: list[tuple[str, int, int]] = []

    pipeline.screen_folder(
        folder, make_job(), on_progress=lambda *args: seen.append(args)
    )

    assert seen == [("alice.pdf", 1, 2), ("bob.pdf", 2, 2)]


def test_unknown_file_types_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedFileTypeError):
        read_resume(tmp_path / "resume.exe")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("alice.pdf", "alice.pdf"),
        ("../../etc/alice.pdf", "alice.pdf"),
        ("/etc/alice.docx", "alice.docx"),
        ("..\\..\\alice.pdf", "alice.pdf"),
        ("", "resume.pdf"),
    ],
)
def test_uploaded_names_cannot_leave_the_folder(name: str, expected: str) -> None:
    assert pipeline.safe_filename(name) == expected
