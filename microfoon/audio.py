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

def get_audio_duration(file_path: Path) -> float:
    """Get the duration of an audio file in seconds using ffprobe."""
    import subprocess
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", str(file_path)
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except:
        return 0.0

def chunk_audio(file_path: Path, chunk_duration_sec: int = 600) -> list[Path]:
    """Splits a large audio file into smaller chunks of 'chunk_duration_sec' seconds."""
    import subprocess
    duration = get_audio_duration(file_path)
    if duration <= chunk_duration_sec:
        return [file_path]
    
    console.log(f"Audio is {duration:.1f}s long. Chunking into {chunk_duration_sec}s segments...")
    
    base_name = file_path.stem
    output_pattern = file_path.parent / f"{base_name}_part%03d.mp3"
    
    cmd = [
        "ffmpeg", "-y", "-i", str(file_path),
        "-f", "segment", "-segment_time", str(chunk_duration_sec),
        "-c:a", "libmp3lame", "-b:a", "64k",
        str(output_pattern)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        console.log(f"[bold red]Chunking failed:[/bold red]\n{result.stderr}")
        return [file_path]
    
    chunks = sorted(list(file_path.parent.glob(f"{base_name}_part*.mp3")))
    console.log(f"Generated {len(chunks)} chunks.")
    return chunks

def compress_audio(input_path: Path, output_path: Path = None):
    """Compress audio to low quality MP3 (or Opus if preferred)."""
    if output_path is None:
        output_path = input_path.with_suffix(".compressed.mp3")
    
    console.log(f"Compressing {input_path} to {output_path}...")
    try:
        import subprocess
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-c:a", "libmp3lame", "-b:a", "64k", str(output_path)
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            console.log(f"[bold red]Compression failed (ffmpeg error):[/bold red]\n{result.stderr}")
            if output_path.exists():
                output_path.unlink()
            return None
            
        return output_path
    except Exception as e:
        console.log(f"[bold red]Compression failed:[/bold red] {e}")
        if output_path and output_path.exists():
            output_path.unlink()
        return None
