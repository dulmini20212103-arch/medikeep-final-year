#Creates a connection engine to your database.
from sqlalchemy import create_engine
#Base class for SQLAlchemy ORM models.
from sqlalchemy.ext.declarative import declarative_base
#Factory for creating database sessions.
from sqlalchemy.orm import sessionmaker
#Configuration object containing the database URL
from .config import settings

# Create SQLAlchemy engine
engine = create_engine(settings.database_url)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

# Dependency to get DB session
def get_db():
    #Creates a new database session.
    db = SessionLocal()
    try:
        #Makes it available to route functions.
        yield db
    finally:
        db.close() #Ensures the session is closed properly


        #This module provides a clean SQLAlchemy setup with a central engine, session factory, and declarative base. It includes a dependency for FastAPI routes, ensuring per-request session management and safe resource cleanup,