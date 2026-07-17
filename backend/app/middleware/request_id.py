"""Request ID middleware.

Injects a unique request identifier (UUID) into each request's state and response headers.
"""

import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware for injecting unique request correlation IDs."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract request ID from incoming header or generate a new one
        request_id = request.headers.get("x-request-id")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Bind to request state so it is accessible within the request lifecycle
        request.state.request_id = request_id

        # Proceed with request execution
        response = await call_next(request)

        # Set the request ID header in the response
        response.headers["X-Request-ID"] = request_id

        return response
