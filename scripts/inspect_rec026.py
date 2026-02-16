import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from microfoon.database import Recording
from microfoon.config import DATABASE_URL

def inspect_rec026():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Find REC026
    rec = session.query(Recording).filter(Recording.original_filename.like("%REC026.WAV")).first()
    
    if not rec:
        print("REC026.WAV not found in database.")
        return

    print(f"Title: {rec.title}")
    print("-" * 20)
    print("CLEANUP CONTENT:")
    print(rec.summary)
    print("-" * 20)
    print("TRANSCRIPT START:")
    print(rec.transcript[:500] + "..." if rec.transcript else "No transcript")

if __name__ == "__main__":
    inspect_rec026()
