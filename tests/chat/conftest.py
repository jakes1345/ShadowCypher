import pytest
from pathlib import Path
from shadowcypher.main import app
from shadowcypher.chat.db import engine
from shadowcypher.chat.models import Base


@pytest.fixture(autouse=True)
def clear_db():
    """Clear database before each test"""
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    # Recreate all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app)
