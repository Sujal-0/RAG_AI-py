"""Shared pytest fixtures for the Mobiloitte AI Platform test suite."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a FastAPI test client.

    Returns:
        TestClient instance bound to the application.
    """
    return TestClient(app)
