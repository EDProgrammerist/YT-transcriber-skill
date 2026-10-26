"""Command-line interface for transcript preparation and document export."""

import argparse
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from yt_document.cleanup import save_cleanup_request
from yt_document.document_io import load_cleaned_document
from yt_document.exporters import export_docx, export_pdf, export_txt
from yt_document.extraction import ExtractionError
from yt_document.pipeline import build_transcript
from yt_document.transcription import TranscriptionError

VIDEO_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{11}")
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}


def normalize_youtube_url(value: str) -> str:
    """Return a canonical YouTube video URL or reject invalid input."""
    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Malformed URL.") from exc

    if parsed.scheme not in {"http", "https"}:
        raise argparse.ArgumentTypeError(
            "Use a YouTube URL beginning with https:// or http://."
        )

    if parsed.username is not None or parsed.password is not None:
        raise argparse.ArgumentTypeError(
            "URLs containing login credentials are not supported."
        )

    if port is not None:
        raise argparse.ArgumentTypeError(
            "URLs with explicit port numbers are not supported."
        )

    host = parsed.hostname
    path_parts = parsed.path.strip("/").split("/")
    video_id = ""

    if host == "youtu.be" and len(path_parts) == 1:
        video_id = path_parts[0]
    elif host in YOUTUBE_HOSTS:
        if parsed.path == "/watch":
            values = parse_qs(parsed.query).get("v", [])
            if len(values) == 1:
                video_id = values[0]
        elif len(path_parts) == 2 and path_parts[0] in {"shorts", "live"}:
            video_id = path_parts[1]
    else:
        raise argparse.ArgumentTypeError(
            "Only youtube.com and youtu.be video links are supported."
        )

    if VIDEO_ID_PATTERN.fullmatch(video_id) is None:
        raise argparse.ArgumentTypeError(
            "The URL must identify one video with an 11-character ID."
        )

    return f"https://www.youtube.com/watch?v={video_id}"


def build_parser() -> argparse.ArgumentParser:
    """Build the prepare and export command parsers."""
    parser = argparse.ArgumentParser(
        description="Prepare YouTube transcripts and export edited documents."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser(
        "prepare",
        help="Extract a transcript and save a Codex cleanup request.",
    )
    prepare.add_argument("url", type=normalize_youtube_url)
    prepare.add_argument(
        "--language",
        default="en",
        help="Exact caption language code (default: en).",
    )
    prepare.add_argument(
        "--whisper-language",
        default=None,
        help="Whisper language code; omit for automatic detection.",
    )
    prepare.add_argument(
        "--model",
        choices=("tiny", "base", "small"),
        default="base",
        help="Local Whisper model size (default: base).",
    )
    prepare.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Cleanup-request directory (default: ./output).",
    )

    export = commands.add_parser(
        "export",
        help="Validate edited JSON and export a document.",
    )
    export.add_argument("--request", type=Path, required=True)
    export.add_argument("--response", type=Path, required=True)
    export.add_argument(
        "--format",
        choices=("txt", "docx", "pdf"),
        required=True,
    )
    export.add_argument("--output", type=Path, required=True)
    export.add_argument(
        "--font",
        type=Path,
        help="Optional replacement font for PDF output.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one workflow stage and report expected failures clearly."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "prepare":
        args.language = args.language.strip()
        if not args.language:
            parser.error("--language must not be empty.")

        if args.whisper_language is not None:
            args.whisper_language = args.whisper_language.strip()
            if not args.whisper_language:
                parser.error("--whisper-language must not be empty.")
    else:
        if args.output.suffix.lower() != f".{args.format}":
            parser.error("--output extension must match --format.")

        if args.font is not None and args.format != "pdf":
            parser.error("--font is only supported for PDF output.")

    try:
        if args.command == "prepare":
            print("Preparing transcript; Whisper runs if captions are absent.")

            transcript = build_transcript(
                args.url,
                caption_language=args.language,
                whisper_language=args.whisper_language,
                model_size=args.model,
            )

            destination = (
                args.output_dir
                / f"cleanup-request-{uuid4().hex}.json"
            )
            saved = save_cleanup_request(transcript, destination)

            print(f"Cleanup request saved: {saved}")
            print("Have Codex edit it using references/cleanup-guidelines.md.")
            print("Save the edited JSON separately, then run export.")
        else:
            document = load_cleaned_document(args.request, args.response)

            if args.format == "pdf":
                saved = export_pdf(
                    document,
                    args.output,
                    font_path=args.font,
                )
            else:
                exporters = {
                    "txt": export_txt,
                    "docx": export_docx,
                }
                saved = exporters[args.format](document, args.output)

            print(f"Saved: {saved}")

    except FileExistsError:
        parser.exit(1, "Error: output already exists. Choose another filename.\n")
    except ImportError as exc:
        parser.exit(1, f"Error: a required dependency is unavailable: {exc}\n")
    except (
        ExtractionError,
        TranscriptionError,
        OSError,
        ValueError,
    ) as exc:
        parser.exit(1, f"Error: {exc}\n")

    return 0