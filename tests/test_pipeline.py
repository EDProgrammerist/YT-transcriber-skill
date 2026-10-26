"""Tests for subtitle-first pipeline behavior."""

from pathlib import Path

import pytest

from yt_document import pipeline
from yt_document.extraction import ExtractionError, SubtitlesUnavailable
from yt_document.models import Segment, Transcript

VIDEO_URL = "https://www.youtube.com/watch?v=abcdefghijk"


def test_uses_available_subtitles(monkeypatch) -> None:
    expected = Transcript(
        title="Captioned video",
        source_url=VIDEO_URL,
        language="en",
        segments=(Segment(0.0, 1.0, "Caption text."),),
    )

    def available_subtitles(url: str, language: str) -> Transcript:
        return expected

    def unexpected_download(*args, **kwargs):
        pytest.fail("Audio must not download when subtitles are available.")

    monkeypatch.setattr(pipeline, "extract_subtitles", available_subtitles)
    monkeypatch.setattr(pipeline, "download_audio", unexpected_download)

    result = pipeline.build_transcript(VIDEO_URL)

    assert result.segments[0].text == "Caption text."


def test_network_error_does_not_trigger_fallback(monkeypatch) -> None:
    def failed_extraction(url: str, language: str) -> Transcript:
        raise ExtractionError("Network unavailable.")

    def unexpected_download(*args, **kwargs):
        pytest.fail("An extraction error must not trigger audio download.")

    monkeypatch.setattr(pipeline, "extract_subtitles", failed_extraction)
    monkeypatch.setattr(pipeline, "download_audio", unexpected_download)

    with pytest.raises(ExtractionError, match="Network unavailable"):
        pipeline.build_transcript(VIDEO_URL)


def test_missing_subtitles_uses_audio_and_removes_temporary_files(
    monkeypatch,
) -> None:
    downloaded_paths: list[Path] = []

    def missing_subtitles(url: str, language: str) -> Transcript:
        raise SubtitlesUnavailable("No matching captions.")

    def fake_download(url: str, directory: Path) -> tuple[Path, str]:
        path = directory / "sample.wav"
        path.write_bytes(b"test audio")
        downloaded_paths.append(path)
        return path, "Spoken lesson"

    def fake_transcription(
        audio_path: Path,
        *,
        title: str,
        source_url: str,
        language: str | None,
        model_size: str,
    ) -> Transcript:
        assert audio_path.read_bytes() == b"test audio"
        return Transcript(
            title=title,
            source_url=source_url,
            language="en",
            segments=(Segment(0.0, 1.0, "Recognized speech."),),
        )

    monkeypatch.setattr(pipeline, "extract_subtitles", missing_subtitles)
    monkeypatch.setattr(pipeline, "download_audio", fake_download)
    monkeypatch.setattr(pipeline, "transcribe_audio", fake_transcription)

    result = pipeline.build_transcript(VIDEO_URL)

    assert result.title == "Spoken lesson"
    assert result.segments[0].text == "Recognized speech."
    assert len(downloaded_paths) == 1
    assert not downloaded_paths[0].exists()