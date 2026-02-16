import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Configuration variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WATCH_DIRECTORY = Path(os.getenv("WATCH_DIRECTORY", "/Volumes"))
STORAGE_DIRECTORY = Path(os.getenv("STORAGE_DIRECTORY", "./recordings"))
OBSIDIAN_VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", "./obsidian_vault"))
TARGET_VOLUME_NAME = os.getenv("TARGET_VOLUME_NAME", "VOICE")
DATABASE_URL = f"sqlite:///{BASE_DIR}/microfoon.db"

# Prompts
def load_prompt(filename, default):
    try:
        with open(BASE_DIR / "prompts" / filename, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return default

PROMPT_CLEANUP = load_prompt("cleanup.txt", "Clean up the following audio transcript.")
PROMPT_TITLE = load_prompt("title.txt", "Generate a concise title for this audio transcript.")

# Ensure storage directories exist
if not STORAGE_DIRECTORY.exists():
    STORAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
