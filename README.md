# Microfoon

USB Audio Processor with Gemini AI.

## Maintenance Scripts

This project includes scripts to help you manage your recordings. To run them, use the python interpreter from the virtual environment:

### Regenerate Exports
If you change the prompts (`cleanup.txt` or `title.txt`), you can re-process your existing audio files to update the Obsidian notes:

```bash
venv/bin/python scripts/regenerate_exports.py
```

### Check Consistency
Verifies if your database records match what is actually in your Obsidian folder:

```bash
venv/bin/python scripts/check_consistency.py
```

## General Setup

1.  Create `.env` from `.env.example`.
2.  Run `./setup_env.sh`.
3.  Install ffmpeg: `brew install ffmpeg`.

## Usage

```bash
source venv/bin/activate
python -m microfoon.main
```
