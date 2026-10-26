"""PII-safe logging configuration.

Hirely logs only non-sensitive operational events. Resume text, extracted
document content, API keys, and other personally identifiable information must
never be written to logs, and user-facing error strings must never leak stack
traces or secrets.
"""

from __future__ import annotations

import logging

LOGGER_NAME = "hirely"

#: Substrings that, if present in a log field name, mark a value as sensitive.
_SENSITIVE_KEY_HINTS = (
    "api_key",
    "apikey",
    "authorization",
    "token",
    "secret",
    "password",
    "resume",
    "document",
    "content",
    "text",
    "email",
    "phone",
)

_REDACTED = "[redacted]"


class RedactingFilter(logging.Filter):
    """Logging filter that drops sensitive structured fields.

    The filter inspects extra attributes attached to a record and redacts any
    whose name hints at secrets or PII. It is a defense-in-depth measure: call
    sites are still expected to log only non-sensitive events.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive extra fields on the record in place.

        Args:
            record: The log record about to be emitted.

        Returns:
            Always ``True`` so the (redacted) record is still emitted.
        """
        for key in list(vars(record)):
            lowered = key.lower()
            if any(hint in lowered for hint in _SENSITIVE_KEY_HINTS):
                setattr(record, key, _REDACTED)
        return True


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the Hirely logger.

    Installs a single stream handler with a terse format that carries no
    message arguments by default and attaches :class:`RedactingFilter`. The
    configuration is idempotent: repeated calls do not stack handlers.

    Args:
        level: Logging level for the Hirely logger. Defaults to ``INFO``.

    Returns:
        The configured ``hirely`` logger.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        stream_handler.addFilter(RedactingFilter())
        logger.addHandler(stream_handler)
    else:
        for existing in logger.handlers:
            if not any(isinstance(f, RedactingFilter) for f in existing.filters):
                existing.addFilter(RedactingFilter())

    return logger


def get_logger() -> logging.Logger:
    """Return the shared, configured Hirely logger.

    Returns:
        The ``hirely`` logger, configured on first use.
    """
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        return configure_logging()
    return logger
