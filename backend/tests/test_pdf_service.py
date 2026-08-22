"""
Unit tests for pdf_service. No OpenAI key or network access required —
these only exercise PDF validation and PyMuPDF extraction.
"""
import fitz
import pytest

from app.services import pdf_service
from app.utils.exceptions import PDFExtractionError, PDFValidationError


def _make_pdf(path: str, pages_text: list[str]) -> None:
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_validate_upload_rejects_non_pdf_extension():
    with pytest.raises(PDFValidationError, match="Only .pdf files"):
        pdf_service.validate_upload("notes.txt", "text/plain", 100, 20)


def test_validate_upload_rejects_empty_file():
    with pytest.raises(PDFValidationError, match="empty"):
        pdf_service.validate_upload("doc.pdf", "application/pdf", 0, 20)


def test_validate_upload_rejects_oversized_file():
    too_big = 21 * 1024 * 1024
    with pytest.raises(PDFValidationError, match="too large"):
        pdf_service.validate_upload("doc.pdf", "application/pdf", too_big, 20)


def test_validate_upload_accepts_valid_pdf():
    # Should not raise.
    pdf_service.validate_upload("doc.pdf", "application/pdf", 1024, 20)


def test_extract_pages_preserves_page_numbers_and_text(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(str(pdf_path), ["Authentication uses OAuth 2.0.", "Rate limiting details."])

    pages = pdf_service.extract_pages(str(pdf_path))

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert "OAuth" in pages[0].text
    assert "Rate limiting" in pages[1].text


def test_extract_pages_raises_when_no_text(tmp_path):
    pdf_path = tmp_path / "blank.pdf"
    _make_pdf(str(pdf_path), ["", ""])  # pages with no inserted text

    with pytest.raises(PDFExtractionError, match="No extractable text"):
        pdf_service.extract_pages(str(pdf_path))


def test_sanitize_filename_strips_path_and_special_chars():
    assert pdf_service.sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert pdf_service.sanitize_filename("my report (final)!.pdf") == "my report _final__.pdf"
