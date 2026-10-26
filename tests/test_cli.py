import argparse

import pytest

from yt_document.cli import build_parser, main, normalize_youtube_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abcdefghijk",
        "https://youtu.be/abcdefghijk?si=sharing-code",
        "https://www.youtube.com/shorts/abcdefghijk",
        "https://www.youtube.com/live/abcdefghijk",
        "https://m.youtube.com/watch?v=abcdefghijk&list=example",
    ],
)
def test_normalizes_supported_video_links(url: str) -> None:
    assert normalize_youtube_url(url) == (
        "https://www.youtube.com/watch?v=abcdefghijk"
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/watch?v=abcdefghijk",
        "https://youtube.com.example.com/watch?v=abcdefghijk",
        "file:///tmp/video.mp4",
        "https://www.youtube.com/playlist?list=example",
        "https://youtu.be/short",
        "https://user:password@youtube.com/watch?v=abcdefghijk",
        "https://youtube.com:8080/watch?v=abcdefghijk",
        "https://youtube.com/watch?v=abcdefghijk&v=12345678901",
    ],
)
def test_rejects_unsupported_video_links(url: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        normalize_youtube_url(url)


def test_rejects_unsupported_output_format() -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(
            [
                "export",
                "--request",
                "request.json",
                "--response",
                "response.json",
                "--format",
                "html",
                "--output",
                "document.html",
            ]
        )

    assert exc.value.code == 2


def test_rejects_blank_language() -> None:
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "prepare",
                "https://youtu.be/abcdefghijk",
                "--language",
                " ",
            ]
        )

    assert exc.value.code == 2


