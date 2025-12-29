# Local AI Video Editing Pipeline

Local-only video editing workflow that shells out to FFmpeg/ffprobe, Whisper CLI, and Ollama. Supports longform edits and short-form clip generation (Shorts/Reels/TikTok) with minimal Python dependencies.

## Features
- Extract + transcribe audio with Whisper CLI
- LLM-generated edit plans via Ollama (JSON clip suggestions)
- Longform: cut suggested clips and concatenate
- Shorts: generate multiple vertical clips with metadata sidecars
- Uses only external CLIs; no heavy Python libs

## Requirements
- Python 3.9+
- CLI tools on PATH:
  - ffmpeg, ffprobe
  - whisper (OpenAI Whisper CLI)
  - ollama (with a local model pulled, e.g., `llama3:8b`)

## Install
```bash
pip install --upgrade pip
# No extra Python deps required beyond stdlib
```
Ensure FFmpeg, Whisper CLI, and Ollama are installed and visible on PATH.

## Usage
General form:
```bash
python video_edit.py <command> [options]
```

### Configuration file (optional)
Create or edit `video_edit.config.json` to set defaults:
```json
{
  "common": {
    "workdir": "./.video_work",
    "whisper_model": "medium",
    "ollama_model": "llama3:8b"
  },
  "longform": {
    "max_clips": 6
  },
  "shorts": {
    "max_clips": 6,
    "max_duration": 60.0,
    "vertical": true
  }
}
```
The script loads `video_edit.config.json` automatically if present; override with `--config path/to/file`. Any CLI flag takes precedence over config.

### Longform edit
Produce a stitched edit from LLM-suggested clips.
```bash
python video_edit.py longform \
  --input raw.mp4 \
  --output edit.mp4 \
  --workdir ./.video_work \
  --whisper-model medium \
  --ollama-model llama3:8b \
  --max-clips 6
```
Outputs: `edit.mp4` plus intermediates in `--workdir`.

### Shorts / vertical clips
Generate multiple short clips with optional 9:16 crop/scale.
```bash
python video_edit.py shorts \
  --input raw.mp4 \
  --output-dir ./shorts \
  --vertical \
  --max-duration 60 \
  --workdir ./.video_work \
  --whisper-model medium \
  --ollama-model llama3:8b \
  --max-clips 6
```
Outputs: `short_XX.mp4` and matching `short_XX.json` metadata files under `--output-dir`.

## How it works
1) Extract audio with FFmpeg
2) Transcribe with Whisper CLI (JSON)
3) Build a prompt and ask Ollama for clip suggestions (expects JSON array)
4) Cut clips with FFmpeg; longform concatenates, shorts export individually

## Tips
- Pull your Ollama model beforehand: `ollama pull llama3:8b`
- Tune `--max-clips`, `--max-duration`, and your chosen models for speed/quality
- For GPU, rely on FFmpeg/Whisper/Ollama flags configured in those tools (not in this script)

## Troubleshooting
- Missing tool errors: ensure ffmpeg/ffprobe/whisper/ollama are on PATH
- Empty LLM plan: script falls back to a single clip; adjust prompt/model
- Whisper JSON not found: verify Whisper CLI produced `.json` next to the audio file

## File reference
- [video_edit.py](video_edit.py): CLI and pipeline implementation

## Roadmap ideas
- Burn-in captions from Whisper SRT/ASS
- Smarter scene/shot detection hints for prompting
- Safer JSON parsing/validation for diverse model outputs
- Audio leveling and loudness normalization
