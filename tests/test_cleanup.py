"""Tests for cleanup request generation."""

import json
from pathlib import Path

import pytest

from yt_document.cleanup import save_cleanup_request
from yt_document.models import Segment, Transcript


@pytest.fixture
def transcript() -> Transcript:
    return Transcript(
        title="Sample lesson",
        source_url="https://www.youtube.com/watch?v=abcdefghijk",
        language="en",
        segments=(
            Segment(0.0, 2.0, "we used 15 samples"),
            Segment(2.0, 4.0, "the result might be wrong"),
        ),
    )


def test_request_preserves_source_data(
    tmp_path: Path,
    transcript: Transcript,
) -> None:
    destination = tmp_path / "request.json"

    saved = save_cleanup_request(transcript, destination)
    payload = json.loads(saved.read_text(encoding="utf-8"))

    assert payload["source"]["title"] == "Sample lesson"
    assert payload["segments"] == [
        {
            "id": 0,
            "start": 0.0,
            "end": 2.0,
            "text": "we used 15 samples",
        },
        {
            "id": 1,
            "start": 2.0,
            "end": 4.0,
            "text": "the result might be wrong",
        },
    ]


def test_request_does_not_overwrite_existing_file(
    tmp_path: Path,
    transcript: Transcript,
) -> None:
    destination = tmp_path / "request.json"
    destination.write_text("existing content", encoding="utf-8")

    with pytest.raises(FileExistsError):
        save_cleanup_request(transcript, destination)

    assert destination.read_text(encoding="utf-8") == "existing content"