"""Pre-parse validation of uploaded resume and career-history files.

Validation runs before any parsing so unsafe or unsupported uploads are
rejected early. The checks, in order, are: a case-insensitive file extension
allow-list, a MIME-type match against the Streamlit upload's declared type, an
authoritative size cap taken from ``MAX_UPLOAD_MB``, and a magic-byte content
sniff that catches files whose extension or MIME lies about their true format.
"""

from __future__ import annotations

import io
import zipfile
from typing import Literal, Protocol, runtime_checkable

from hirely.config import Settings

#: Allowed upload extensions (compared lower-case).
_PDF_EXT = ".pdf"
_DOCX_EXT = ".docx"

#: Accepted MIME types per media kind. Streamlit reports ``UploadedFile.type``.
_PDF_MIME = "application/pdf"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

#: Magic-byte signatures used by the content sniff.
_PDF_MAGIC = b"%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"

#: Internal part every real DOCX (OOXML ZIP) contains.
_DOCX_REQUIRED_PART = "word/document.xml"

_BYTES_PER_MB = 1024 * 1024


class ValidationError(Exception):
    """An upload failed a pre-parse validation check.

    The message is user-safe: it names the reason without leaking file content
    or a stack trace.
    """


@runtime_checkable
class UploadLike(Protocol):
    """Minimal contract matched by a Streamlit ``UploadedFile``.

    Attributes:
        name: Original filename including its extension.
        type: Declared MIME type; may be an empty string if unknown.
    """

    name: str
    type: str

    def getvalue(self) -> bytes:
        """Return the full upload contents as bytes."""
        ...


def _media_type_from_extension(filename: str) -> Literal["pdf", "docx"]:
    """Resolve the media type from a filename's extension.

    Args:
        filename: The original upload filename.

    Returns:
        ``"pdf"`` or ``"docx"``.

    Raises:
        ValidationError: If the extension is neither ``.pdf`` nor ``.docx``.
    """
    lowered = filename.lower()
    if lowered.endswith(_PDF_EXT):
        return "pdf"
    if lowered.endswith(_DOCX_EXT):
        return "docx"
    raise ValidationError("Unsupported file type. Upload a PDF (.pdf) or Word document (.docx).")


def _check_mime(media_type: Literal["pdf", "docx"], declared: str) -> None:
    """Confirm the declared MIME type matches the resolved media type.

    An empty declared type is tolerated: not every client sets it, and the
    magic-byte sniff is the authoritative content check. A present but wrong
    type is rejected.

    Args:
        media_type: The media type resolved from the extension.
        declared: The MIME type declared by the upload.

    Raises:
        ValidationError: If a non-empty declared type does not match.
    """
    if not declared:
        return
    expected = _PDF_MIME if media_type == "pdf" else _DOCX_MIME
    if declared != expected:
        raise ValidationError("The file content type does not match its extension.")


def _check_size(data: bytes, max_upload_mb: int) -> None:
    """Enforce the authoritative upload size cap.

    Args:
        data: The full upload bytes.
        max_upload_mb: The authoritative cap in megabytes.

    Raises:
        ValidationError: If the upload is empty or exceeds the cap. The cap in
            megabytes appears in the message.
    """
    if len(data) == 0:
        raise ValidationError("The uploaded file is empty.")
    if len(data) > max_upload_mb * _BYTES_PER_MB:
        raise ValidationError(f"The file is too large. The maximum upload size is {max_upload_mb} MB.")


def _sniff_pdf(data: bytes) -> None:
    """Confirm the bytes begin with the PDF magic signature.

    Args:
        data: The full upload bytes.

    Raises:
        ValidationError: If the content is not a PDF.
    """
    if not data.startswith(_PDF_MAGIC):
        raise ValidationError("The file is not a valid PDF.")


def _sniff_docx(data: bytes) -> None:
    """Confirm the bytes are a ZIP containing the DOCX document part.

    Args:
        data: The full upload bytes.

    Raises:
        ValidationError: If the content is not a DOCX (OOXML ZIP).
    """
    if not data.startswith(_ZIP_MAGIC):
        raise ValidationError("The file is not a valid Word document.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile as exc:
        raise ValidationError("The file is not a valid Word document.") from exc
    if _DOCX_REQUIRED_PART not in names:
        raise ValidationError("The file is not a valid Word document.")


def validate_upload(upload: UploadLike, settings: Settings) -> Literal["pdf", "docx"]:
    """Validate an upload and return its confirmed media type.

    The checks run in order: extension allow-list, MIME match, size cap, and a
    magic-byte content sniff. The first failure raises a user-safe
    :class:`ValidationError`.

    Args:
        upload: The Streamlit upload (or any object matching :class:`UploadLike`).
        settings: Runtime configuration providing ``max_upload_mb``.

    Returns:
        The confirmed media type, ``"pdf"`` or ``"docx"``.

    Raises:
        ValidationError: If any check fails.
    """
    media_type = _media_type_from_extension(upload.name)
    _check_mime(media_type, upload.type)

    data = upload.getvalue()
    _check_size(data, settings.max_upload_mb)

    if media_type == "pdf":
        _sniff_pdf(data)
    else:
        _sniff_docx(data)

    return media_type
