"""Schemas for parsed uploaded documents.

A :class:`ParsedDocument` is the in-memory result of securely parsing an
uploaded resume or career-history file. It carries extracted text only; no
macros, scripts, or embedded objects are represented or executed.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ParsedDocument(BaseModel):
    """Text extracted from a validated upload.

    Attributes:
        filename: Original filename of the upload.
        media_type: Detected document type.
        text: Extracted plain text.
        page_count: Number of pages for PDFs; ``None`` for DOCX.
        char_count: Number of characters in :attr:`text`.
    """

    filename: str
    media_type: Literal["pdf", "docx"]
    text: str
    page_count: int | None = None
    char_count: int
