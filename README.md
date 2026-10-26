<h1 align="center">YouTube to Document</h1>

<p align="center">Turn a YouTube lesson into a readable, timestamped document with Codex.</p>

<p align="center">
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&amp;logo=python&amp;logoColor=blue"></a>
  <a href="https://www.youtube.com/"><img alt="YouTube" src="https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&amp;logo=youtube&amp;logoColor=white"></a>
  <a href="skills/youtube-to-document/SKILL.md"><img alt="Codex Skill" src="https://img.shields.io/badge/Codex-Skill-111111?style=for-the-badge"></a>
  <img alt="TXT, DOCX, PDF" src="https://img.shields.io/badge/Export-TXT%20%7C%20DOCX%20%7C%20PDF-2563EB?style=for-the-badge">
</p>

<p align="center">
  <a href="#install-the-skill">Install</a> ·
  <a href="#use-in-codex">Use in Codex</a> ·
  <a href="#command-line-workflow">CLI</a> ·
  <a href="#development">Development</a>
</p>

## What it does

Convert lectures, tutorials, and other spoken YouTube videos into full transcript documents for study and reference.

- Prefer human-written captions, then automatic captions in the requested language.
- Fall back to local Whisper transcription when that caption language is unavailable.
- Let Codex correct grammar, punctuation, and formatting using conservative editing instructions.
- Organize the transcript into headings and paragraphs with source timestamps.
- Export **TXT**, **DOCX**, or **PDF** without overwriting existing documents.
- Keep the original transcript and edited response as separate JSON files for review.

**No additional API key, paid transcription API, or Ollama installation is required.** Cleanup happens in your Codex conversation, so Codex access and usage limits still apply. Whisper inference runs locally; model weights may download on first use. This is not an entirely offline workflow: YouTube extraction needs internet access, and Codex processes the transcript for editing.

## How it works

```text
YouTube URL
    |
    +-- Captions available --> yt-dlp subtitle extraction
    |
    +-- Requested captions unavailable --> audio download --> FFmpeg --> Whisper
    |
Timestamped source transcript
    |
Codex cleanup and paragraph organization
    |
Validate segment coverage and derive paragraph timestamps
    |
TXT / DOCX / PDF
```

Python handles extraction, validation, and export. The [skill instructions](skills/youtube-to-document/SKILL.md) guide Codex through editing using the [cleanup guidelines](skills/youtube-to-document/references/cleanup-guidelines.md).

## Requirements

| Requirement | Purpose |
| --- | --- |
| Codex with local file and command access | Run the skill and edit transcripts |
| Python 3.11+ with compatible dependency wheels | Run the Python scripts |
| Node.js 22.20+ and npm/npx | Install through the Skills CLI |
| Deno, or another supported yt-dlp JavaScript runtime | YouTube challenge handling |
| FFmpeg | Prepare audio for the Whisper fallback |
| Python dependency groups | Enable local transcription and document export |

The development checks have been run on Windows with standard Python 3.14. Other platforms have not yet been verified in this project. A GPU is not required: the current Whisper implementation uses CPU INT8 inference.

The Node requirement comes from the [Skills CLI](https://github.com/vercel-labs/skills#install-a-skill). See [yt-dlp's runtime setup](https://github.com/yt-dlp/yt-dlp/wiki/EJS) for supported JavaScript runtimes.

## Install the skill

From the project where you want to use it:

```sh
npx skills add EDProgrammerist/YT-transcriber-skill --skill youtube-to-document --agent codex --copy
```

This command installs from the published GitHub repository. For an unpublished local checkout, run this from the repository root instead:

```sh
npx skills add ./skills/youtube-to-document --agent codex --copy
```

Check the installation:

```sh
npx skills list
```

The project installation normally lives in `.agents/skills/youtube-to-document`. Open a new Codex chat in that project; restart Codex if the skill does not appear. Installation options are documented by the [Skills CLI](https://github.com/vercel-labs/skills/blob/main/docs/commands.md), and discovery behavior by [OpenAI](https://learn.chatgpt.com/docs/build-skills).

> Installing the skill copies its instructions, scripts, and assets. It does **not** install Python packages, FFmpeg, Deno, or Whisper model weights.

### Set up the runtime on Windows

Use a standard Python 3.11+ interpreter. Check your selected interpreter before creating a virtual environment:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip

$skillPath = ".\.agents\skills\youtube-to-document"
.\.venv\Scripts\python.exe -m pip install -e "${skillPath}[documents,transcription]"
```

For a source checkout without an installed copy, set `$skillPath` to `".\skills\youtube-to-document"` instead. Reuse a compatible existing virtual environment if you already have one.

Check the external tools:

```powershell
deno --version
ffmpeg -version
```

If missing, install them and open a fresh terminal:

```powershell
winget install --id DenoLand.Deno --exact
winget install "FFmpeg (Essentials Build)"
```

These installation methods are documented by [Deno](https://docs.deno.com/runtime/getting_started/installation/) and [Gyan's FFmpeg builds](https://www.gyan.dev/ffmpeg/builds/).

On macOS/Linux, use `python3 -m venv .venv` and `.venv/bin/python` in place of the Windows interpreter path. Install the external tools for your operating system using their official instructions.

## Use in Codex

After installation and runtime setup, send a prompt like this, replacing the example URL:

```text
Use $youtube-to-document to convert this video into a cleaned TXT document:

https://www.youtube.com/watch?v=VIDEO_ID

Save it in this project's output folder.
Use the existing Python virtual environment in .venv.
Preserve the speaker's meaning and timestamps.
Run preparation, cleanup, validation, and export.
```

Ask for **DOCX** or **PDF** instead of TXT to change the format. You can also specify the caption language and a destination filename.

Codex should create a source request, save its edited response separately, validate the response, and provide the final document. Existing output files are protected from overwriting.

## Command-line workflow

The CLI has two stages. It does not call a language-model API or automatically perform grammar correction by itself.

The following PowerShell commands assume an installed project skill and the virtual environment above. For source development, change `$skillPath` as described in runtime setup.

```powershell
$skillPath = ".\.agents\skills\youtube-to-document"
$scriptPath = Join-Path $skillPath "scripts/youtube_to_document.py"
$videoUrl = Read-Host "YouTube URL"

.\.venv\Scripts\python.exe "$scriptPath" prepare "$videoUrl" --language en --output-dir output
```

The command prints the path to `cleanup-request-<identifier>.json`. Have Codex read that file and the cleanup guidelines, then save the edited response as a separate JSON file. Preserve the original request.

Export the edited response:

```powershell
$requestPath = (Read-Host "Original cleanup-request JSON path").Trim().Trim('"')
$responsePath = (Read-Host "Edited response JSON path").Trim().Trim('"')

.\.venv\Scripts\python.exe "$scriptPath" export --request "$requestPath" --response "$responsePath" --format txt --output "output/transcript.txt"
```

Change both `--format` and the output extension for DOCX or PDF.

| Option | Behavior |
| --- | --- |
| `prepare --language en` | Request the exact caption language; defaults to `en` |
| `prepare --whisper-language en` | Specify the speech language; omitted means automatic detection |
| `prepare --model tiny\|base\|small` | Choose a Whisper model; defaults to `base` |
| `prepare --output-dir PATH` | Choose where the source request is saved |
| `export --format txt\|docx\|pdf` | Choose the document format |
| `export --output PATH` | Choose a new output filename with the matching extension |
| `export --font PATH` | Use an alternative font for PDF export |

Caption codes such as `en-US` and Whisper language codes such as `en` are separate. Transcription preserves the spoken language; it is not a translation feature.

## Output and validation

| File | Contents |
| --- | --- |
| `cleanup-request-<identifier>.json` | Original text, timestamps, metadata, and sequential segment IDs |
| Separate edited response JSON | Codex-edited paragraphs, headings, and source segment references |
| `.txt`, `.docx`, or `.pdf` | The validated, formatted transcript |

The validator checks that every source segment ID appears exactly once and in order. Paragraph timestamps come from the source, not the model. These checks **do not prove semantic equivalence**: review names, numbers, negation, uncertainty, and technical terminology against the original.

Temporary downloaded media is removed after transcription. Source requests and edited responses remain available for review. Generated files in the repository's `output/` directory are ignored by Git.

## Current limitations

- Long transcripts may exceed Codex context limits; automatic chunking is not implemented.
- Network failures, access restrictions, and malformed captions stop the workflow rather than triggering Whisper.
- Caption parsing currently supports JSON3. Unsupported caption formats report an error.
- Use completed videos. The audio fallback rejects live, upcoming, and still-processing live streams.
- PDF export embeds Noto Sans and checks character coverage. It does not support every writing system or configure complex-script shaping.
- Whisper and editing can make mistakes. The first Whisper run may download weights, and CPU transcription can be slow.
- The bundled default PDF font path assumes a complete skill folder or editable source installation. Standalone wheel distribution is not currently supported.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Skill is not visible | Run `npx skills list`, open the correct project, then restart Codex if needed |
| Python runtime not found | Select an installed standard Python 3.11+ interpreter before creating `.venv` |
| Module import fails | Install dependencies into the same virtual environment used to run the script |
| Deno or FFmpeg is not found | Install it, reopen the terminal, and verify its version command |
| YouTube extraction fails | Read the reported error; check video access and the installed yt-dlp version |
| Cleanup validation fails | Fix missing, repeated, or out-of-order segment IDs without modifying the source |
| Output already exists | Choose a new filename |
| PDF font is missing or lacks characters | Keep the skill's assets folder intact or supply a suitable `--font` |

## Development

```sh
git clone https://github.com/EDProgrammerist/YT-transcriber-skill.git
cd YT-transcriber-skill
```

Create a virtual environment, then install development dependencies from the source folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "./skills/youtube-to-document[documents,transcription,dev]"
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m ruff check --config skills/youtube-to-document/pyproject.toml skills/youtube-to-document/scripts tests
```

Tests cover input validation, transcript models, caption parsing, fallback decisions, cleanup coverage, TXT/DOCX output, and audio preparation. The FFmpeg conversion test skips when FFmpeg is unavailable. Passing tests do not establish live YouTube access, Whisper recognition quality, or PDF visual layout; check those separately with a short video and the generated document.

```text
skills/youtube-to-document/
├── SKILL.md
├── pyproject.toml
├── assets/fonts/                  # PDF font and its license
├── references/cleanup-guidelines.md
└── scripts/
    ├── youtube_to_document.py     # CLI entry point
    └── yt_document/
        ├── __init__.py
        ├── cli.py
        ├── models.py
        ├── extraction.py
        ├── transcription.py
        ├── pipeline.py
        ├── cleanup.py
        ├── document_io.py
        └── exporters.py
tests/                            # Automated checks
output/                           # Local generated files; ignored by Git
```

## Credits and licensing

- Badge designs: [Badges4-README.md-Profile](https://github.com/alexandresanlim/Badges4-README.md-Profile), rendered with [Shields.io](https://shields.io/). Python and YouTube badges use the collection's designs; project badges follow the same style.
- Extraction: [yt-dlp](https://github.com/yt-dlp/yt-dlp).
- Audio preparation and recognition: [FFmpeg](https://ffmpeg.org/) and [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
- Document generation: [python-docx](https://python-docx.readthedocs.io/) and [fpdf2](https://py-pdf.github.io/fpdf2/).
- Noto Sans is bundled with its [SIL Open Font License](skills/youtube-to-document/assets/fonts/OFL.txt).

**Project code license: not yet specified.** No project-level `LICENSE` file is currently included. Third-party components retain their own licenses.
