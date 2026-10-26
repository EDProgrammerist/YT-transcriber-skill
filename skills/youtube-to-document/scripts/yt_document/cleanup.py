"""Prepare transcript data for editing by Codex."""
import json
from dataclasses import dataclass
from pathlib import Path

from yt_document.models import Transcript


def build_cleanup_request(transcript: Transcript) -> dict[str, object]:
    """Build a cleanup request while preserving original transcript data."""
    segments = [
        {
            "id": index,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
        }
        for index, segment in enumerate(transcript.segments)
    ]

    return {
        "schema_version": 1,
        "source": {
            "title": transcript.title,
            "url": transcript.source_url,
            "language": transcript.language,
        },
        "segments": segments,
        "expected_response": {
            "paragraphs": [
                {
                    "heading": "A short topic heading, or an empty string",
                    "segment_ids": [0],
                    "text": "Edited text from the referenced segments",
                }
            ]
        },
    }


class CleanupValidationError(ValueError):
    """The edited response does not match the source transcript."""


@dataclass(frozen=True)
class CleanedParagraph:
    """Edited text linked to its original transcript segments."""

    heading: str
    text: str
    segment_ids: tuple[int, ...]
    start: float
    end: float


@dataclass(frozen=True)
class CleanedDocument:
    """Validated document content ready for export."""

    title: str
    source_url: str
    language: str
    paragraphs: tuple[CleanedParagraph, ...]


def validate_cleanup(
    transcript: Transcript,
    response: object,
) -> CleanedDocument:
    """Validate coverage and derive timestamps from the source."""
    if not isinstance(response, dict) or set(response) != {"paragraphs"}:
        raise CleanupValidationError(
            "Response must contain only a 'paragraphs' field."
        )

    paragraphs = response["paragraphs"]
    if not isinstance(paragraphs, list) or not paragraphs:
        raise CleanupValidationError("Paragraphs must be a nonempty list.")

    cleaned = []
    next_id = 0
    source_count = len(transcript.segments)
    required_fields = {"heading", "segment_ids", "text"}

    for position, paragraph in enumerate(paragraphs, start=1):
        if not isinstance(paragraph, dict):
            raise CleanupValidationError(
                f"Paragraph {position} must be an object."
            )

        if set(paragraph) != required_fields:
            raise CleanupValidationError(
                f"Paragraph {position} has missing or unexpected fields."
            )

        heading = paragraph["heading"]
        text = paragraph["text"]
        segment_ids = paragraph["segment_ids"]

        if not isinstance(heading, str):
            raise CleanupValidationError(
                f"Paragraph {position} heading must be a string."
            )

        if not isinstance(text, str) or not text.strip():
            raise CleanupValidationError(
                f"Paragraph {position} text must be a nonempty string."
            )

        if not isinstance(segment_ids, list) or not segment_ids:
            raise CleanupValidationError(
                f"Paragraph {position} needs a nonempty segment ID list."
            )

        # bool is a subclass of int, so check the exact type.
        if any(type(segment_id) is not int for segment_id in segment_ids):
            raise CleanupValidationError("Segment IDs must be integers.")

        end_id = next_id + len(segment_ids)
        expected_ids = list(range(next_id, end_id))

        if end_id > source_count or segment_ids != expected_ids:
            raise CleanupValidationError(
                "Segment IDs must cover the source exactly once, in order."
            )

        source_segments = transcript.segments[next_id:end_id]

        cleaned.append(
            CleanedParagraph(
                heading=heading.strip(),
                text=text.strip(),
                segment_ids=tuple(segment_ids),
                start=source_segments[0].start,
                end=max(segment.end for segment in source_segments),
            )
        )
        next_id = end_id

    if next_id != source_count:
        raise CleanupValidationError(
            "The edited response does not cover every source segment."
        )

    return CleanedDocument(
        title=transcript.title,
        source_url=transcript.source_url,
        language=transcript.language,
        paragraphs=tuple(cleaned),
    )

def save_cleanup_request(
    transcript: Transcript,
    destination: Path,
) -> Path:
    """Save a UTF-8 cleanup request without replacing an existing file."""
    destination = destination.expanduser().resolve()
    content = json.dumps(
        build_cleanup_request(transcript),
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("x", encoding="utf-8") as handle:
        handle.write(content)
        handle.write("\n")

    return destination