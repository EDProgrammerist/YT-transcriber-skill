"""Load saved transcript requests and validated cleanup responses."""

import json
from pathlib import Path

from yt_document.cleanup import (
    CleanedDocument,
    CleanupValidationError,
    validate_cleanup,
)
from yt_document.models import Segment, Transcript


def load_transcript_request(path: Path) -> Transcript:
    """Reconstruct a transcript from a saved cleanup request."""
    try:
        payload = json.loads(
            path.expanduser().read_text(encoding="utf-8-sig")
        )

        if not isinstance(payload, dict):
            raise ValueError("Request must be a JSON object.")

        if payload.get("schema_version") != 1:
            raise ValueError("Unsupported cleanup-request schema version.")

        source = payload["source"]
        if not isinstance(source, dict):
            raise ValueError("Source metadata must be an object.")

        for field in ("title", "url", "language"):
            if not isinstance(source.get(field), str):
                raise ValueError(f"Source {field!r} must be a string.")

        raw_segments = payload["segments"]
        if not isinstance(raw_segments, list) or not raw_segments:
            raise ValueError("Segments must be a nonempty list.")

        segments = []

        for index, item in enumerate(raw_segments):
            if not isinstance(item, dict):
                raise ValueError("Each segment must be an object.")

            if type(item.get("id")) is not int or item["id"] != index:
                raise ValueError("Source segment IDs must be sequential.")

            if not isinstance(item.get("text"), str):
                raise ValueError("Segment text must be a string.")

            for field in ("start", "end"):
                if type(item.get(field)) not in (int, float):
                    raise ValueError(f"Segment {field} must be numeric.")

            segments.append(
                Segment(
                    start=item["start"],
                    end=item["end"],
                    text=item["text"],
                )
            )

        return Transcript(
            title=source["title"],
            source_url=source["url"],
            language=source["language"],
            segments=tuple(segments),
        )

    except (KeyError, TypeError, ValueError) as exc:
        raise CleanupValidationError(
            f"Invalid cleanup request: {exc}"
        ) from exc


def load_cleaned_document(
    request_path: Path,
    response_path: Path,
) -> CleanedDocument:
    """Load source data and validate the edited response against it."""
    transcript = load_transcript_request(request_path)
    response = json.loads(
        response_path.expanduser().read_text(encoding="utf-8-sig")
    )
    return validate_cleanup(transcript, response)