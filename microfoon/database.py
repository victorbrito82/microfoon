from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
import enum

from microfoon.config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPORTED = "exported"

class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String, index=True)
    stored_filename = Column(String)
    source_path = Column(String)
    
    # AI Generated Content
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    title = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    reprocessed_at = Column(DateTime, nullable=True)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    obsidian_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Recording(id={self.id}, title='{self.title}', status='{self.status}')>"

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
