#!/usr/bin/env python3
"""
Script to reprocess failed recordings in the database.
Attempts to use compressed MP3 files if original WAV files are missing.
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

# Add parent directory to path to import microfoon modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from microfoon.database import get_db, Recording, ProcessingStatus
from microfoon.intelligence import GeminiProcessor
from microfoon.exporter import ObsidianExporter
from microfoon.config import STORAGE_DIRECTORY

console = Console()

def reprocess_failed_recordings():
    """Find and reprocess all failed recordings."""
    db_session = next(get_db())
    processor = GeminiProcessor()
    exporter = ObsidianExporter()
    
    # Query all failed recordings
    failed_recordings = db_session.query(Recording).filter(
        Recording.status == ProcessingStatus.FAILED
    ).all()
    
    if not failed_recordings:
        console.print("[green]No failed recordings found![/green]")
        return
    
    # Display failed recordings
    table = Table(title="Failed Recordings to Reprocess")
    table.add_column("ID", style="cyan")
    table.add_column("Filename", style="magenta")
    table.add_column("Error", style="red")
    
    for rec in failed_recordings:
        table.add_row(
            str(rec.id),
            rec.original_filename or "N/A",
            rec.error_message or "Unknown error"
        )
    
    console.print(table)
    console.print(f"\n[bold]Found {len(failed_recordings)} failed recording(s)[/bold]")
    
    # Process each failed recording
    success_count = 0
    still_failed_count = 0
    
    for recording in failed_recordings:
        console.print(f"\n[bold blue]Reprocessing ID {recording.id}:[/bold blue] {recording.original_filename}")
        
        # Determine which file to use
        stored_path = STORAGE_DIRECTORY / recording.stored_filename
        
        # If WAV doesn't exist, try compressed MP3
        if not stored_path.exists():
            mp3_path = stored_path.with_suffix('.compressed.mp3')
            if mp3_path.exists():
                console.print(f"[yellow]WAV not found, using compressed MP3: {mp3_path.name}[/yellow]")
                stored_path = mp3_path
                # Update the database to reflect the actual file
                recording.stored_filename = mp3_path.name
            else:
                console.print(f"[bold red]File not found: {stored_path} or {mp3_path}[/bold red]")
                recording.error_message = f"File not found: {stored_path.name}"
                db_session.commit()
                still_failed_count += 1
                continue
        
        # Reset status to processing
        recording.status = ProcessingStatus.PROCESSING
        recording.error_message = None
        db_session.commit()
        
        # Try to process with Gemini
        try:
            result = processor.process_audio(stored_path, retry=True)
            
            if result:
                recording.transcript = result.get("transcript")
                recording.summary = result.get("cleanup")
                recording.title = result.get("title")
                recording.status = ProcessingStatus.COMPLETED
                
                console.print(f"[bold green]✓ Success![/bold green]")
                console.print(f"[bold]Title:[/bold] {recording.title}")
                console.print(f"[bold]Summary:[/bold] {recording.summary[:100]}...")
                
                # Export to Obsidian
                obsidian_path = exporter.export(recording)
                if obsidian_path:
                    recording.obsidian_path = str(obsidian_path)
                    recording.status = ProcessingStatus.EXPORTED
                    console.print(f"[bold green]✓ Exported to Obsidian[/bold green]")
                
                success_count += 1
            else:
                recording.status = ProcessingStatus.FAILED
                recording.error_message = "Gemini processing returned no result (after retry)"
                console.print(f"[bold red]✗ Still failed after retry[/bold red]")
                still_failed_count += 1
        
        except Exception as e:
            console.print(f"[bold red]✗ Error:[/bold red] {e}")
            recording.status = ProcessingStatus.FAILED
            recording.error_message = str(e)
            still_failed_count += 1
        
        db_session.commit()
    
    # Summary
    console.print("\n" + "="*60)
    console.print(f"[bold]Reprocessing Complete![/bold]")
    console.print(f"[green]Successfully processed: {success_count}[/green]")
    console.print(f"[red]Still failed: {still_failed_count}[/red]")
    console.print("="*60)

if __name__ == "__main__":
    console.print("[bold yellow]Microfoon - Reprocess Failed Recordings[/bold yellow]\n")
    reprocess_failed_recordings()
