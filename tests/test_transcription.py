"""Tests for audio preparation."""

import shutil
import wave
from pathlib import Path

import pytest

from yt_document.transcription import TranscriptionError, prepare_audio


def test_missing_audio_produces_clear_error(tmp_path: Path) -> None:
    with pytest.raises(TranscriptionError, match="does not exist"):
        prepare_audio(
            tmp_path / "missing.wav",
            tmp_path / "prepared.wav",
        )


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="FFmpeg is required for the conversion test.",
)
def test_converts_audio_to_required_format(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    destination = tmp_path / "prepared.wav"

    # Generate one second of stereo silence at 44.1 kHz.
    with wave.open(str(source), "wb") as recording:
        recording.setnchannels(2)
        recording.setsampwidth(2)
        recording.setframerate(44100)
        recording.writeframes(b"\x00" * 44100 * 2 * 2)

    prepare_audio(source, destination)

    with wave.open(str(destination), "rb") as recording:
        assert recording.getnchannels() == 1
        assert recording.getframerate() == 16000
        assert recording.getsampwidth() == 2
        assert recording.getnframes() == 16000