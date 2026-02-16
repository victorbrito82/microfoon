import time
import os
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
from rich.panel import Panel

from microfoon.database import init_db, get_db, Recording, ProcessingStatus
from microfoon.usb_monitor import USBMonitor
from microfoon.audio import find_audio_files, copy_and_rename, compress_audio
from microfoon.intelligence import GeminiProcessor
from microfoon.exporter import ObsidianExporter
from microfoon.config import STORAGE_DIRECTORY, TARGET_VOLUME_NAME

console = Console()

def process_usb_drive(drive_path: Path):
    """
    Handles the workflow when a USB drive is detected.
    """
    console.print(Panel(f"[bold blue]USB Drive Detected:[/bold blue] {drive_path}"))

    # 1. Find Audio Files
    audio_files = find_audio_files(drive_path)
    if not audio_files:
        console.print("[yellow]No audio files found on this drive.[/yellow]")
        return

    # 2. Show files and ask to start
    table = Table(title="Found Audio Files")
    table.add_column("Filename", style="cyan")
    table.add_column("Size", style="magenta")
    
    for file in audio_files:
        size_mb = file.stat().st_size / (1024 * 1024)
        table.add_row(file.name, f"{size_mb:.2f} MB")
    
    console.print(table)
    
    if not Confirm.ask("Do you want to start transcribing these files?"):
        console.print("[yellow]Skipping transcription.[/yellow]")
        return

    # Initialize components
    db_session = next(get_db())
    processor = GeminiProcessor()
    exporter = ObsidianExporter()

    # 3. Process each file
    processed_files = []
    
    for file_path in audio_files:
        console.print(f"\n[bold green]Processing:[/bold green] {file_path.name}")
        
        # Copy to storage
        stored_path = copy_and_rename(file_path)
        
        # Create DB record
        recording = Recording(
            original_filename=file_path.name,
            stored_filename=stored_path.name,
            source_path=str(file_path),
            status=ProcessingStatus.PROCESSING
        )
        db_session.add(recording)
        db_session.commit()

        # Transcribe & Summarize via Gemini
        try:
            result = processor.process_audio(stored_path)
            
            if result:
                recording.transcript = result.get("transcript")
                recording.summary = result.get("cleanup")
                recording.title = result.get("title")
                recording.status = ProcessingStatus.COMPLETED
                
                console.print(f"[bold]Title:[/bold] {recording.title}")
                console.print(f"[bold]Summary:[/bold] {recording.summary[:200]}...")

                # Export to Obsidian
                obsidian_path = exporter.export(recording)
                if obsidian_path:
                    recording.obsidian_path = str(obsidian_path)
                    recording.status = ProcessingStatus.EXPORTED
            else:
                 recording.status = ProcessingStatus.FAILED
                 recording.error_message = "Gemini processing returned no result"

        except Exception as e:
            console.print(f"[bold red]Error processing {file_path.name}:[/bold red] {e}")
            recording.status = ProcessingStatus.FAILED
            recording.error_message = str(e)
        
        db_session.commit()
        processed_files.append((file_path, stored_path))

    # 4. Post-processing (Delete / Compress)
    console.print(Panel("[bold blue]Post-Processing[/bold blue]"))
    
    if Confirm.ask("Do you want to delete the original files from the USB stick?"):
        for original, _ in processed_files:
            try:
                os.remove(original)
                console.print(f"[red]Deleted:[/red] {original}")
            except Exception as e:
                 console.print(f"[bold red]Failed to delete {original}:[/bold red] {e}")

    if Confirm.ask("Do you want to compress the stored audio files to low-quality MP3?"):
         for _, stored in processed_files:
             compressed_path = compress_audio(stored)
             if compressed_path:
                 console.print(f"[green]Compressed:[/green] {compressed_path}")
                 # Option: Delete original heavy wav? 
                 # User didn't explicitly ask to delete the local high-quality copy, 
                 # but usually 'compress' implies replacing or saving space. 
                 # I'll keep it simple for now and just create the compressed version.

def main():
    init_db()
    
    # Ensure directories exist
    if not STORAGE_DIRECTORY.exists():
        STORAGE_DIRECTORY.mkdir(parents=True)

    console.print(Panel.fit(f"[bold yellow]Microfoon[/bold yellow] - USB Audio Processor\nWaiting for '{TARGET_VOLUME_NAME}' USB drive...", border_style="yellow"))
    
    monitor = USBMonitor(process_usb_drive)
    monitor.start()
    
    # Scan for existing volumes on startup
    console.print(f"[dim]Scanning for existing volume '{TARGET_VOLUME_NAME}'...[/dim]")
    for path in Path("/Volumes").glob("*"):
        if path.is_dir() and path.name == TARGET_VOLUME_NAME:
             process_usb_drive(path)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("Stopping...")
        monitor.stop()

if __name__ == "__main__":
    main()
