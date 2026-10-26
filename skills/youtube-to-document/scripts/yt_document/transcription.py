"""Prepare local audio and transcribe it with Whisper."""

import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from yt_document.models import Segment, Transcript


class TranscriptionError(Exception):
    """Audio preparation or local speech recognition failed."""


def prepare_audio(source: Path, destination: Path) -> None:
    """Convert a local recording into mono, 16 kHz PCM WAV."""
    source = source.expanduser().resolve()
    destination = destination.expanduser().resolve()

    if not source.is_file():
        raise TranscriptionError(f"Audio file does not exist: {source}")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise TranscriptionError("FFmpeg is not available on PATH.")

    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-n",
        "-i",
        str(source),
        "-map",
        "0:a:0",
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    except subprocess.CalledProcessError as exc:
        details = exc.stderr.strip() or "Unknown FFmpeg error."
        raise TranscriptionError(
            f"Audio conversion failed: {details}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise TranscriptionError(
            "Audio conversion exceeded the 10-minute limit."
        ) from exc
    except OSError as exc:
        raise TranscriptionError(f"Cannot run FFmpeg: {exc}") from exc


def transcribe_audio(
    audio_path: Path,
    *,
    title: str,
    source_url: str,
    language: str | None = None,
    model_size: str = "base",
) -> Transcript:
    """Transcribe local audio using a multilingual Whisper model."""
    if model_size not in {"tiny", "base", "small"}:
        raise ValueError("Model size must be tiny, base, or small.")

    if language is not None:
        language = language.strip()
        if not language:
            raise ValueError("Language must not be blank.")

    try:
        with TemporaryDirectory(prefix="yt-whisper-") as temporary_dir:
            prepared = Path(temporary_dir) / "audio.wav"
            prepare_audio(audio_path, prepared)

            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise TranscriptionError(
                    "Install the transcription dependency group first."
                ) from exc

            try:
                model = WhisperModel(
                    model_size,
                    device="cpu",
                    compute_type="int8",
                )
                recognized, info = model.transcribe(
                    str(prepared),
                    language=language,
                    task="transcribe",
                    beam_size=5,
                    vad_filter=True,
                )

                # Whisper returns a generator: iteration performs the work.
                segments = tuple(
                    Segment(
                        start=segment.start,
                        end=segment.end,
                        text=segment.text.strip(),
                    )
                    for segment in recognized
                    if segment.text.strip()
                )
            except Exception as exc:
                # Wrap errors at the external model-library boundary.
                raise TranscriptionError(
                    f"Whisper transcription failed: {exc}"
                ) from exc

            if not segments:
                raise TranscriptionError("No speech was detected.")

            return Transcript(
                title=title,
                source_url=source_url,
                language=info.language,
                segments=segments,
            )

    except OSError as exc:
        raise TranscriptionError(
            f"Cannot manage temporary audio files: {exc}"
        ) from exc