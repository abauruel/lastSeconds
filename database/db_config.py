from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Create the SQLAlchemy engine
import os

# Database stored on USB drive
DATABASE_PATH = "/media/pi/usb64gb/bts/recordings.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
engine = create_engine(DATABASE_URL)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for declarative models
Base = declarative_base()

def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()