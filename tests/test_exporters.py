"""Tests for plain-text document export."""

from pathlib import Path

import pytest

from yt_document.cleanup import CleanedDocument, CleanedParagraph
from yt_document.exporters import export_txt, format_timestamp


@pytest.fixture
def document() -> CleanedDocument:
    return CleanedDocument(
        title="Sample lesson",
        source_url="https://www.youtube.com/watch?v=abcdefghijk",
        language="en",
        paragraphs=(
            CleanedParagraph(
                heading="Results",
                text="We used 15 samples at the café.",
                segment_ids=(0,),
                start=1.5,
                end=65.2,
            ),
        ),
    )


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0.0, "00:00:00"),
        (59.9, "00:00:59"),
        (60.0, "00:01:00"),
        (3600.0, "01:00:00"),
        (3723.8, "01:02:03"),
    ],
)
def test_formats_timestamps(seconds: float, expected: str) -> None:
    assert format_timestamp(seconds) == expected


@pytest.mark.parametrize(
    "seconds",
    [-1.0, float("nan"), float("inf")],
)
def test_rejects_invalid_timestamps(seconds: float) -> None:
    with pytest.raises(ValueError):
        format_timestamp(seconds)


def test_exports_readable_utf8_document(
    tmp_path: Path,
    document: CleanedDocument,
) -> None:
    destination = tmp_path / "exports" / "lesson.txt"

    saved = export_txt(document, destination)

    assert saved.read_text(encoding="utf-8") == (
        "Sample lesson\n"
        "Source: https://www.youtube.com/watch?v=abcdefghijk\n"
        "Language: en\n"
        "\n"
        "Results\n"
        "\n"
        "[00:00:01 - 00:01:05]\n"
        "We used 15 samples at the café.\n"
    )


def test_does_not_overwrite_existing_document(
    tmp_path: Path,
    document: CleanedDocument,
) -> None:
    destination = tmp_path / "lesson.txt"
    destination.write_text("Keep this document.", encoding="utf-8")

    with pytest.raises(FileExistsError):
        export_txt(document, destination)

    assert destination.read_text(encoding="utf-8") == "Keep this document."


def test_rejects_wrong_extension(
    tmp_path: Path,
    document: CleanedDocument,
) -> None:
    with pytest.raises(ValueError, match=".txt"):
        export_txt(document, tmp_path / "lesson.pdf")