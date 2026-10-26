"""Secure document validation and in-memory parsing.

Exposes upload validation (extension/MIME/size/magic-byte checks) and the
in-memory parser that extracts text only, never executing macros or embedded
objects, and maps every failure mode to a handled error.
"""

from __future__ import annotations

from hirely.documents.parser import DocumentError, parse_document
from hirely.documents.validation import ValidationError, validate_upload

__all__ = [
    "DocumentError",
    "ValidationError",
    "parse_document",
    "validate_upload",
]
