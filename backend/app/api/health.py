"""Health check endpoint.

Provides a simple liveness probe confirming the service is running.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def health_check() -> dict[str, str]:
    """Return service health status.

    Returns:
        Dictionary with status, project name, and version.
    """
    print(">>> [health_check] Incoming health request")
    return {
        "status": "running",
        "project": "Mobiloitte AI Platform",
        "version": "1.0.0",
    }
