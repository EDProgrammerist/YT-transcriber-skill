"""Coordinate subtitle extraction and local transcription."""

from pathlib import Path
from tempfile import TemporaryDirectory

from yt_document.extraction import (
    SubtitlesUnavailable,
    download_audio,
    extract_subtitles,
)
from yt_document.models import Transcript
from yt_document.transcription import transcribe_audio


def build_transcript(
    url: str,
    *,
    caption_language: str = "en",
    whisper_language: str | None = None,
    model_size: str = "base",
) -> Transcript:
    """Build a transcript from a previously validated YouTube URL."""
    try:
        return extract_subtitles(url, caption_language)
    except SubtitlesUnavailable:
        pass

    with TemporaryDirectory(prefix="yt-audio-") as temporary_dir:
        audio_path, title = download_audio(url, Path(temporary_dir))

        return transcribe_audio(
            audio_path,
            title=title,
            source_url=url,
            language=whisper_language,
            model_size=model_size,
        )