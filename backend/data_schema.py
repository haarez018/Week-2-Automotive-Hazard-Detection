# /backend/data_schema.py (ABSOLUTE PATH FIX APPLIED)

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pydantic import BaseModel
# Import Pathlib for robust, cross-platform file path handling
from pathlib import Path 

# --- 1. Database Configuration (CRITICAL FIX) ---
# Get the absolute path to the project root (up two levels from this file's location)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Define the absolute path for the DB file in the project root
DB_FILE_PATH = PROJECT_ROOT / "hazard_log.db"

# SQLAlchemy connection string now uses the absolute path
# We use .as_posix() to ensure forward slashes, which SQLite prefers, even on Windows
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE_PATH.as_posix()}" 

# Create the SQLAlchemy engine for connecting to the DB
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all model definitions
Base = declarative_base()

# --- 2. Database Model Definition (SQLAlchemy ORM) ---
class Hazard(Base):
    """Defines the 'hazards' table structure in the DB."""
    __tablename__ = "hazards"

    id = Column(Integer, primary_key=True, index=True)
    hazard_type = Column(String, index=True)       # e.g., 'Pothole', 'Rash Driving'
    timestamp = Column(DateTime, default=datetime.utcnow)
    location_data = Column(String)                 # e.g., 'Front Cam | Frame 123'
    severity = Column(Integer)                     # Score 1-10

# --- 3. Pydantic Schema (for API validation) ---
class HazardCreate(BaseModel):
    """Schema for data incoming via the API POST request."""
    hazard_type: str
    location_data: str
    severity: int
    
    class Config:
        orm_mode = True # Allows Pydantic to read ORM objects

# --- 4. Utility Functions ---
def create_db_tables():
    """Ensures the database file and the 'hazards' table exist."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency function for FastAPI to manage sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Execute table creation when the module is loaded
create_db_tables()