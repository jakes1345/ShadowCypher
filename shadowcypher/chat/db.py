from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shadowcypher.chat.models import Base
from pathlib import Path

DATABASE_URL = "sqlite:///shadowcypher_chat.db"  # Will be encrypted at rest

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)

def init_db():
    """Create tables and return session factory"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal

SessionLocal = init_db()
