from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from microfoon.database import Recording, Base
from microfoon.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Check the last updated recordings
# We don't have an 'updated_at' field in the model shown earlier, but we can check the content of the summary field
# to see if it starts with the new bold topic format like "**("

recordings = session.query(Recording).all()
updated_count = 0
total_count = len(recordings)

for rec in recordings:
    # Check for the new format: "**(Topic)**" or "(Topic)"
    if rec.summary and (rec.summary.strip().startswith("**(") or rec.summary.strip().startswith("(")):
        updated_count += 1

print(f"Total Recordings: {total_count}")
print(f"Updated Recordings (estimated): {updated_count}")
