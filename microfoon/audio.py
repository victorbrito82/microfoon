import shutil
import os
from pathlib import Path
from datetime import datetime
from pydub import AudioSegment
from rich.console import Console

from microfoon.config import STORAGE_DIRECTORY

console = Console()

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}

def find_audio_files(directory: Path):
    """Recursively find audio files in a directory."""
    audio_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.startswith("._"):
                continue
            if Path(file).suffix.lower() in AUDIO_EXTENSIONS:
                audio_files.append(Path(root) / file)
    return audio_files

def copy_and_rename(file_path: Path) -> Path:
    """Copy audio file to storage with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"{timestamp}_{file_path.name}"
    destination = STORAGE_DIRECTORY / new_filename
    
    console.log(f"Copying {file_path} to {destination}...")
    shutil.copy2(file_path, destination)
    return destination

def compress_audio(input_path: Path, output_path: Path = None):
    """Compress audio to low quality MP3 (or Opus if preferred)."""
    if output_path is None:
        output_path = input_path.with_suffix(".compressed.mp3")
    
    console.log(f"Compressing {input_path} to {output_path}...")
    try:
        audio = AudioSegment.from_file(input_path)
        # Export as 64k bitrate MP3
        audio.export(output_path, format="mp3", bitrate="64k")
        return output_path
    except Exception as e:
        console.log(f"[bold red]Compression failed:[/bold red] {e}")
        return None
