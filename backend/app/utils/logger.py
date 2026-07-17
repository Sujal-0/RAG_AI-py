"""Standard logging configuration.

Exposes a pre-configured logger instance to be shared across the application.
"""

import logging
import sys

from app.core.settings import settings

# Configure logging level and format
log_level = logging.DEBUG if settings.app.debug else logging.INFO
log_format = (
    "%(asctime)s [%(levelname)s] [Request:%(request_id)s] %(name)s: %(message)s"
)


class RequestIdFilter(logging.Filter):
    """Logging filter to inject request_id attribute if missing.

    Ensures that log records always have a request_id attribute to prevent KeyError.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def get_logger(name: str) -> logging.Logger:
    """Get a pre-configured logger with the given name.

    Args:
        name: Name of the logger (usually __name__).

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if logger is already configured
    if not logger.handlers:
        logger.setLevel(log_level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(handler)
        logger.addFilter(RequestIdFilter())

    return logger


# Default application-wide logger
logger = get_logger("app")
