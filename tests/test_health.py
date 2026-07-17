"""Health endpoint tests.

Verifies the service health check returns the expected status payload.
"""

from fastapi.testclient import TestClient


def test_health_returns_running_status(client: TestClient) -> None:
    """GET / must return status=running with correct project metadata."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "running"
    assert data["project"] == "Mobiloitte AI Platform"
    assert data["version"] == "1.0.0"


def test_health_returns_all_required_fields(client: TestClient) -> None:
    """GET / response must contain exactly the required keys."""
    response = client.get("/")
    data = response.json()

    expected_keys = {"status", "project", "version"}
    assert set(data.keys()) == expected_keys
