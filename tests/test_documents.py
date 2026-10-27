"""Document validation and parsing tests.

Every failure mode is handled without a crash: unsupported extension, oversized
upload, MIME mismatch, encrypted PDF, malformed file, empty file, and a file
whose extension lies about its content.
"""

from __future__ import annotations

import pytest

from hirely.config import Settings
from hirely.documents.parser import DocumentError, parse_document
from hirely.documents.validation import ValidationError, validate_upload
from tests.conftest import FakeUpload, fixture_bytes


def _settings() -> Settings:
    return Settings(ai_provider="ollama", max_upload_mb=10)


def test_valid_pdf_parses() -> None:
    upload = FakeUpload("resume.pdf", fixture_bytes("resume.pdf"), "application/pdf")
    media = validate_upload(upload, _settings())
    assert media == "pdf"
    parsed = parse_document(upload, media)
    assert "Jane Developer" in parsed.text
    assert parsed.char_count > 0
    assert parsed.page_count == 1


def test_valid_docx_parses() -> None:
    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    upload = FakeUpload("resume.docx", fixture_bytes("resume.docx"), mime)
    media = validate_upload(upload, _settings())
    assert media == "docx"
    parsed = parse_document(upload, media)
    assert "Jane Developer" in parsed.text
    assert parsed.page_count is None


def test_unsupported_extension_rejected() -> None:
    upload = FakeUpload("resume.rtf", b"whatever", "")
    with pytest.raises(ValidationError):
        validate_upload(upload, _settings())


def test_oversized_upload_rejected() -> None:
    big = b"%PDF-" + b"0" * (11 * 1024 * 1024)
    upload = FakeUpload("big.pdf", big, "application/pdf")
    with pytest.raises(ValidationError):
        validate_upload(upload, _settings())


def test_empty_file_rejected_at_validation() -> None:
    upload = FakeUpload("empty.pdf", fixture_bytes("empty.pdf"), "application/pdf")
    with pytest.raises(ValidationError):
        validate_upload(upload, _settings())


def test_txt_renamed_to_pdf_rejected_by_sniff() -> None:
    upload = FakeUpload("not_really.pdf", fixture_bytes("not_really.pdf"), "application/pdf")
    with pytest.raises(ValidationError):
        validate_upload(upload, _settings())


def test_mime_mismatch_rejected() -> None:
    upload = FakeUpload("resume.pdf", fixture_bytes("resume.pdf"), "text/plain")
    with pytest.raises(ValidationError):
        validate_upload(upload, _settings())


def test_encrypted_pdf_handled_without_crash() -> None:
    upload = FakeUpload("encrypted.pdf", fixture_bytes("encrypted.pdf"), "application/pdf")
    media = validate_upload(upload, _settings())  # passes validation (real PDF bytes)
    with pytest.raises(DocumentError):
        parse_document(upload, media)


def test_malformed_pdf_handled_without_crash() -> None:
    upload = FakeUpload("corrupt.pdf", fixture_bytes("corrupt.pdf"), "application/pdf")
    media = validate_upload(upload, _settings())
    with pytest.raises(DocumentError):
        parse_document(upload, media)


def test_empty_extraction_raises_document_error() -> None:
    # A valid, parseable PDF with no text should raise rather than return empty.
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    upload = FakeUpload("blank.pdf", data, "application/pdf")
    media = validate_upload(upload, _settings())
    with pytest.raises(DocumentError):
        parse_document(upload, media)
