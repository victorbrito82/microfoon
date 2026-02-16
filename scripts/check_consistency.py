import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from microfoon.database import Recording
from microfoon.config import DATABASE_URL, OBSIDIAN_VAULT_PATH

def check_consistency():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    recordings = session.query(Recording).all()
    
    issues_found = 0
    
    print(f"Checking {len(recordings)} recordings...")
    
    for rec in recordings:
        if not rec.summary:
            continue
            
        # Construct expected Obsidian path
        # Logic from exporter.py: safe_title + .md
        safe_title = "".join(c for c in rec.title if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_title}.md"
        file_path = OBSIDIAN_VAULT_PATH / filename
        
        if not file_path.exists():
            print(f"[MISSING] {filename} not found in Obsidian vault.")
            issues_found += 1
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Check if the DB summary is present in the file
            # content should contain "## Note\n{rec.summary}"
            # We'll just check if rec.summary is IN content
            
            if rec.summary.strip() not in content:
                print(f"[MISMATCH] {filename}")
                print(f"  DB Start: {rec.summary.strip()[:50]}...")
                print(f"  File Content does not match DB.")
                issues_found += 1
            else:
                 # Optional: Check for third person in DB content
                 lower_summary = rec.summary.lower()
                 if "the speaker" in lower_summary or "he mentions" in lower_summary or "she mentions" in lower_summary:
                     print(f"[THIRD PERSON DETECTED IN DB] {filename}")
                     issues_found += 1

        except Exception as e:
            print(f"[ERROR] Could not read {filename}: {e}")
            issues_found += 1

    if issues_found == 0:
        print("All files match database content and no obvious third-person issues found.")
    else:
        print(f"Found {issues_found} issues.")

if __name__ == "__main__":
    check_consistency()
