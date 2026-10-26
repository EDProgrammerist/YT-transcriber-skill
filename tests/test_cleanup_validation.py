"""Tests for edited transcript validation."""

import pytest

from yt_document.cleanup import CleanupValidationError, validate_cleanup
from yt_document.models import Segment, Transcript


@pytest.fixture
def transcript() -> Transcript:
    return Transcript(
        title="Sample lesson",
        source_url="https://www.youtube.com/watch?v=abcdefghijk",
        language="en",
        segments=(
            Segment(0.0, 4.0, "we used 15 samples"),
            Segment(2.0, 3.0, "the result might be wrong"),
        ),
    )


def test_derives_timestamps_from_original_segments(
    transcript: Transcript,
) -> None:
    response = {
        "paragraphs": [
            {
                "heading": "Results",
                "segment_ids": [0, 1],
                "text": (
                    "We used 15 samples. "
                    "The result might be wrong."
                ),
            }
        ]
    }

    document = validate_cleanup(transcript, response)

    assert document.title == "Sample lesson"
    assert document.paragraphs[0].start == 0.0
    assert document.paragraphs[0].end == 4.0
    assert document.paragraphs[0].segment_ids == (0, 1)


@pytest.mark.parametrize(
    "segment_ids",
    [
        [],
        [0],
        [1, 0],
        [0, 0],
        [0, 1, 2],
        [False, 1],
    ],
)
def test_rejects_invalid_segment_coverage(
    transcript: Transcript,
    segment_ids: list[int],
) -> None:
    response = {
        "paragraphs": [
            {
                "heading": "",
                "segment_ids": segment_ids,
                "text": "Edited text.",
            }
        ]
    }

    with pytest.raises(CleanupValidationError):
        validate_cleanup(transcript, response)


@pytest.mark.parametrize(
    "response",
    [
        None,
        {},
        {"paragraphs": []},
        {"paragraphs": "not a list"},
        {
            "paragraphs": [
                {
                    "heading": "",
                    "segment_ids": [0, 1],
                    "text": " ",
                }
            ]
        },
        {
            "paragraphs": [
                {
                    "heading": "",
                    "segment_ids": [0, 1],
                    "text": "Edited text.",
                    "start": 999,
                }
            ]
        },
    ],
)
def test_rejects_invalid_response_structure(
    transcript: Transcript,
    response: object,
) -> None:
    with pytest.raises(CleanupValidationError):
        validate_cleanup(transcript, response)