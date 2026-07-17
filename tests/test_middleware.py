"""Request ID middleware integration tests."""

import uuid

from fastapi.testclient import TestClient


def test_request_id_middleware_generates_uuid(client: TestClient) -> None:
    """A unique UUID must be generated in headers if x-request-id is missing."""
    response = client.get("/")
    assert response.status_code == 200

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    # Validate it is a valid UUID
    parsed_uuid = uuid.UUID(request_id)
    assert parsed_uuid.version == 4


def test_request_id_middleware_preserves_given_id(client: TestClient) -> None:
    """An incoming X-Request-ID must be preserved in headers and response context."""
    provided_id = "test-custom-request-id-12345"
    response = client.get("/", headers={"X-Request-ID": provided_id})
    assert response.status_code == 200

    returned_id = response.headers.get("X-Request-ID")
    assert returned_id == provided_id
