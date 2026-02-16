import sys
import os
import argparse
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from microfoon.database import Recording, ProcessingStatus, Base
from microfoon.config import DATABASE_URL, STORAGE_DIRECTORY
from microfoon.intelligence import GeminiProcessor
from microfoon.exporter import ObsidianExporter

console = Console()

def regenerate(recording_id=None, original_filename=None, auto_confirm=False, export_only=False):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    processor = GeminiProcessor()
    exporter = ObsidianExporter()

    query = session.query(Recording)
    if recording_id is not None:
        query = query.filter(Recording.id == recording_id)
    elif original_filename:
        query = query.filter(Recording.original_filename == original_filename)

    recordings = query.order_by(Recording.id.asc()).all()

    if not recordings:
        console.print("[yellow]No recordings found to regenerate for the given filter.[/yellow]")
        return

    console.print(f"[bold]Found {len(recordings)} recordings to regenerate.[/bold]")
    if not auto_confirm and not Confirm.ask("Do you want to proceed? This will overwrite existing Obsidian notes."):
        return

    for rec in recordings:
        # Check if already in new format (starts with bold or paren topic)
        # For now, we comment this out because we WANT to re-process files that might have bad content (English instead of Dutch, or bad dialogue)
        # if rec.summary and (rec.summary.strip().startswith("**(") or rec.summary.strip().startswith("(")):
        #    continue

        console.print(f"\n[blue]Processing:[/blue] {rec.original_filename}")
        
        # Check if stored file exists
        # Note: We prioritize the compressed file if original stored file is gone (though logic usually keeps one)
        # But 'stored_filename' in DB usually points to the one we created initially.
        # If we compressed it, we might have changed the file on disk but maybe not updated DB stored_filename?
        # Let's check.
        
        file_path = STORAGE_DIRECTORY / rec.stored_filename
        
        if not file_path.exists():
             # Try to find compressed version
             compressed_path = file_path.with_suffix(".compressed.mp3")
             if compressed_path.exists():
                 file_path = compressed_path
             else:
                 console.print(f"[red]Audio file not found for {rec.original_filename}. Skipping.[/red]")
                 continue
        
        if export_only:
            try:
                exported_path = exporter.export(rec)
                if exported_path:
                    rec.obsidian_path = str(exported_path)
                    rec.status = ProcessingStatus.EXPORTED
                    session.commit()
                    console.print(f"[green]Re-exported:[/green] {exported_path}")
                else:
                    console.print(f"[red]Export failed for {rec.original_filename}[/red]")
            except Exception as e:
                console.print(f"[red]Error exporting {rec.original_filename}: {e}[/red]")
            continue

        try:
            # Re-process with Gemini (using new PROMPT_CLEANUP and PROMPT_TITLE)
            result = processor.process_audio(file_path)

            if result:
                rec.transcript = result.get("transcript")
                rec.summary = result.get("cleanup")
                rec.title = result.get("title")

                # Re-export
                try:
                    exporter.export(rec)
                    console.print(f"[green]New Title:[/green] {rec.title}")
                except Exception as e:
                    console.print(f"[red]Export failed:[/red] {e}")

                session.commit()
            else:
                console.print(f"[red]Gemini returned no result for {rec.original_filename}[/red]")

        except Exception as e:
            console.print(f"[red]Error processing {rec.original_filename}: {e}[/red]")

    console.print("[bold green]Regeneration Complete![/bold green]")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reprocess recordings and regenerate Obsidian exports from existing DB rows."
    )
    parser.add_argument(
        "--id",
        type=int,
        help="Reprocess only the recording with this database ID."
    )
    parser.add_argument(
        "--original-filename",
        type=str,
        help="Reprocess only recordings matching this original filename (e.g. REC030.WAV)."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt."
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Skip Gemini reprocessing and only re-export existing DB content to Obsidian."
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    regenerate(
        recording_id=args.id,
        original_filename=args.original_filename,
        auto_confirm=args.yes,
        export_only=args.export_only,
    )
