"""Logging safety test.

A representative run-style log capture must contain no resume text, API key, or
PII. The redacting filter drops sensitive structured fields. The Hirely logger
intentionally does not propagate to the root logger, so capture is performed on
the logger's own handler.
"""

from __future__ import annotations

import io
import logging

from hirely.logging_setup import LOGGER_NAME, RedactingFilter, configure_logging


def test_redacting_filter_redacts_sensitive_fields_in_place() -> None:
    record = logging.LogRecord(
        name=LOGGER_NAME,
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="feature run complete",
        args=(),
        exc_info=None,
    )
    record.resume_text = "Jane Developer, SSN 123-45-6789"
    record.api_key = "sk-secret-value"
    record.user_email = "jane@example.com"
    record.model = "llama3"

    assert RedactingFilter().filter(record) is True
    assert record.resume_text == "[redacted]"
    assert record.api_key == "[redacted]"
    assert record.user_email == "[redacted]"
    # Non-sensitive operational fields are preserved.
    assert record.model == "llama3"


def test_full_run_log_output_has_no_secret_or_pii() -> None:
    logger = configure_logging()
    logger.setLevel(logging.INFO)

    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s %(resume_text)s %(api_key)s")
    )
    handler.addFilter(RedactingFilter())
    logger.addHandler(handler)
    try:
        logger.info(
            "feature run complete",
            extra={
                "resume_text": "Jane Developer, SSN 123-45-6789",
                "api_key": "sk-secret-value",
            },
        )
    finally:
        logger.removeHandler(handler)

    blob = buffer.getvalue()
    assert "sk-secret-value" not in blob
    assert "123-45-6789" not in blob
    assert "[redacted]" in blob
