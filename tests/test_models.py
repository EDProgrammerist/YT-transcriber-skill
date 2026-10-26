import pytest

from yt_document.models import Segment, Transcript


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (-1.0, 2.0),
        (3.0, 2.0),
        (2.0, 2.0),
        (float("nan"), 2.0),
        (0.0, float("inf")),
    ],
)
def test_segment_rejects_invalid_timestamps(
    start: float,
    end: float,
) -> None:
    with pytest.raises(ValueError):
        Segment(start=start, end=end, text="Hello.")


def test_segment_rejects_blank_text() -> None:
    with pytest.raises(ValueError):
        Segment(start=0.0, end=1.0, text=" \n ")


def make_transcript(segments: tuple[Segment, ...]) -> Transcript:
    """Build a transcript with consistent test metadata."""
    return Transcript(
        title="Sample lesson",
        source_url="https://www.youtube.com/watch?v=abcdefghijk",
        language="en",
        segments=segments,
    )


def test_transcript_rejects_empty_segments() -> None:
    with pytest.raises(ValueError):
        make_transcript(())


def test_transcript_rejects_out_of_order_segments() -> None:
    with pytest.raises(ValueError):
        make_transcript(
            (
                Segment(start=5.0, end=7.0, text="Later."),
                Segment(start=0.0, end=2.0, text="Earlier."),
            )
        )


def test_transcript_preserves_overlapping_captions() -> None:
    transcript = make_transcript(
        (
            Segment(start=0.0, end=3.0, text="First caption."),
            Segment(start=2.0, end=4.0, text="Second caption."),
        )
    )

    assert len(transcript.segments) == 2
    assert transcript.segments[1].start == 2.0
    assert transcript.segments[1].text == "Second caption."