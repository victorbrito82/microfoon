import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from microfoon.database import Recording
from microfoon.config import DATABASE_URL, STORAGE_DIRECTORY, OBSIDIAN_VAULT_PATH

def repair_db():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    recordings = session.query(Recording).all()
    
    # Get all files in storage directory
    existing_files = [f.name for f in STORAGE_DIRECTORY.iterdir() if f.is_file()]
    
    repaired_count = 0
    obsidian_updated_count = 0

    for rec in recordings:
        # 1. Update Obsidian Path
        target_obsidian_dir = str(OBSIDIAN_VAULT_PATH)
        if rec.obsidian_path and not rec.obsidian_path.startswith(target_obsidian_dir):
             file_name = Path(rec.obsidian_path).name
             rec.obsidian_path = str(OBSIDIAN_VAULT_PATH / file_name)
             obsidian_updated_count += 1

        # 2. Repair Stored Filename
        # Check if current stored_filename exists
        current_path = STORAGE_DIRECTORY / rec.stored_filename
        if not current_path.exists():
            # Try to find a matching file by timestamp and original filename pattern
            # Pattern: YYYYMMDD_HHMMSS_original_filename or .compressed.mp3
            match = None
            
            # Look for compressed version first
            compressed_variant = rec.stored_filename.replace(".WAV", ".compressed.mp3").replace(".wav", ".compressed.mp3")
            if (STORAGE_DIRECTORY / compressed_variant).exists():
                match = compressed_variant
            else:
                # Look for ANY file containing the original_filename
                for f in existing_files:
                    if rec.original_filename in f:
                        match = f
                        break
            
            if match:
                print(f"Repairing {rec.original_filename}: {rec.stored_filename} -> {match}")
                rec.stored_filename = match
                repaired_count += 1
            else:
                print(f"Warning: Could not find file for {rec.original_filename} (tried {rec.stored_filename})")

    session.commit()
    print(f"Done! Repaired {repaired_count} filenames and updated {obsidian_updated_count} obsidian paths.")

if __name__ == "__main__":
    repair_db()
