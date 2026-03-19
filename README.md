# Microfoon

USB Audio Processor with Gemini AI.

## Maintenance Scripts

This project includes scripts to help you manage your recordings. To run them, use the python interpreter from the virtual environment:

#### Reprocess Recordings
If you want to re-process existing recordings (e.g., to use better prompts or regenerate missing fields):
```bash
./venv/bin/python3 scripts/reprocess_transcripts.py --id [ID]
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

To start the application, simply run these commands in your standard terminal (you do **not** need to type `bash` first):

```sh
source venv/bin/activate
python -m microfoon.main
```
