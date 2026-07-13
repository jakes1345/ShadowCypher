"""Conftest for integration tests — creates DB tables before each test."""
import pytest
from shadowcypher.chat.db import engine
from shadowcypher.chat.models import Base


@pytest.fixture(autouse=True)
def integration_db():
    """Ensure DB tables exist and are clean for each integration test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
