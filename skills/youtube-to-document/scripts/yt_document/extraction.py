"""Download YouTube captions and audio for transcript generation."""

import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from yt_document.models import Segment, Transcript


class ExtractionError(Exception):
    """Metadata retrieval, downloading, or caption parsing failed."""


class SubtitlesUnavailable(ExtractionError):
    """No caption track exists for the requested language."""


def parse_json3(content: str) -> tuple[Segment, ...]:
    """Parse JSON3 captions without rewriting the speaker's words."""
    try:
        payload = json.loads(content)
        events = payload["events"]

        if not isinstance(events, list):
            raise ValueError("Caption events must be a list.")

        segments = []

        for event in events:
            # Display-control events may contain no spoken text.
            parts = event.get("segs", [])
            text = "".join(part["utf8"] for part in parts).strip()

            if not text:
                continue

            start = float(event["tStartMs"]) / 1000
            duration = float(event["dDurationMs"]) / 1000

            segments.append(
                Segment(
                    start=start,
                    end=start + duration,
                    text=text,
                )
            )

        if not segments:
            raise ValueError("Caption file contains no usable text.")

        return tuple(sorted(segments, key=lambda segment: segment.start))

    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ExtractionError(f"Invalid JSON3 captions: {exc}") from exc


def youtube_options(directory: Path) -> dict[str, object]:
    """Build shared download settings for one YouTube video."""
    return {
        "noplaylist": True,
        "outtmpl": str(directory / "%(id)s.%(ext)s"),
        "socket_timeout": 30,
        "retries": 3,
        "ignoreerrors": False,
        "cachedir": False,
        "quiet": True,
    }


def extract_subtitles(url: str, language: str = "en") -> Transcript:
    """Extract captions from a previously validated YouTube video URL."""
    language = language.strip()
    if not language:
        raise ValueError("Caption language must not be empty.")

    try:
        with TemporaryDirectory(prefix="yt-document-") as temporary_dir:
            options = {
                **youtube_options(Path(temporary_dir)),
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": [re.escape(language)],
                "subtitlesformat": "json3",
            }

            with YoutubeDL(options) as downloader:
                info = downloader.extract_info(url, download=True)

            if not info or info.get("_type", "video") != "video":
                raise ExtractionError("Expected metadata for one video.")

            requested = info.get("requested_subtitles") or {}
            selected = requested.get(language)

            if selected is None:
                raise SubtitlesUnavailable(
                    f"No subtitles found for language {language!r}."
                )

            if selected.get("ext") != "json3":
                raise ExtractionError(
                    "The selected caption track is not available as JSON3."
                )

            filepath = selected.get("filepath")
            if not filepath:
                raise ExtractionError(
                    "The caption track was selected but not saved."
                )

            content = Path(filepath).read_text(encoding="utf-8-sig")
            segments = parse_json3(content)

            return Transcript(
                title=info.get("title") or info["id"],
                source_url=url,
                language=language,
                segments=segments,
            )

    except DownloadError as exc:
        raise ExtractionError(f"YouTube extraction failed: {exc}") from exc
    except (OSError, UnicodeError) as exc:
        raise ExtractionError(f"Cannot read or store captions: {exc}") from exc


def download_audio(url: str, directory: Path) -> tuple[Path, str]:
    """Download audio into a caller-owned directory.

    The URL must already be validated. Returns the file path and video title.
    """
    directory = directory.expanduser().resolve()

    try:
        directory.mkdir(parents=True, exist_ok=True)

        options = {
            **youtube_options(directory),
            "format": "bestaudio/best",
        }

        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=False)

            if not info or info.get("_type", "video") != "video":
                raise ExtractionError("Expected metadata for one video.")

            if info.get("live_status") in {
                "is_live",
                "is_upcoming",
                "post_live",
            }:
                raise ExtractionError(
                    "Use a completed, processed video for transcription."
                )

            # Reuse metadata instead of extracting the same video again.
            downloader.process_info(info)
            audio_path = Path(downloader.prepare_filename(info))

        if not audio_path.is_file():
            raise ExtractionError("The audio download did not create a file.")

        return audio_path, info.get("title") or info["id"]

    except DownloadError as exc:
        raise ExtractionError(f"Audio download failed: {exc}") from exc
    except OSError as exc:
        raise ExtractionError(f"Cannot store downloaded audio: {exc}") from exc