"""Tests for JSON3 caption parsing."""

import json

import pytest

from yt_document.extraction import ExtractionError, parse_json3


def test_parses_text_and_converts_milliseconds() -> None:
    content = json.dumps(
        {
            "events": [
                {
                    "tStartMs": 1500,
                    "dDurationMs": 2000,
                    "segs": [
                        {"utf8": "Hello "},
                        {"utf8": "world."},
                    ],
                }
            ]
        }
    )

    segments = parse_json3(content)

    assert len(segments) == 1
    assert segments[0].start == 1.5
    assert segments[0].end == 3.5
    assert segments[0].text == "Hello world."


def test_skips_display_events_and_orders_segments() -> None:
    content = json.dumps(
        {
            "events": [
                {"tStartMs": 0, "wWinId": 1},
                {
                    "tStartMs": 2000,
                    "dDurationMs": 1000,
                    "segs": [{"utf8": "Second."}],
                },
                {
                    "tStartMs": 0,
                    "dDurationMs": 1000,
                    "segs": [{"utf8": "First."}],
                },
            ]
        }
    )

    segments = parse_json3(content)

    assert [segment.text for segment in segments] == [
        "First.",
        "Second.",
    ]


@pytest.mark.parametrize(
    "content",
    [
        "not JSON",
        '{"events": []}',
        '{"events": {}}',
        '{"events": [{"segs": [{"utf8": "Missing timestamps."}]}]}',
        (
            '{"events": [{"tStartMs": 0, "dDurationMs": -1000, '
            '"segs": [{"utf8": "Invalid duration."}]}]}'
        ),
    ],
)
def test_rejects_unusable_caption_data(content: str) -> None:
    with pytest.raises(ExtractionError):
        parse_json3(content)