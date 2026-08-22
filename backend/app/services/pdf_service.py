"""
PDF processing: validation, page-by-page text extraction, and light
cleaning.

Kept deliberately dependency-light (just PyMuPDF/fitz) so the extraction
logic is easy to read end to end rather than hidden behind a framework.
"""
import re
import uuid
from pathlib import Path

import fitz  # PyMuPDF

from app.core.logging import get_logger
from app.models.document import PageContent
from app.utils.exceptions import PDFExtractionError, PDFValidationError

logger = get_logger(__name__)

ALLOWED_EXTENSION = ".pdf"
ALLOWED_MIME_TYPES = {"application/pdf"}


def generate_safe_document_id() -> str:
    """UUID4 — never derived from the user-supplied filename, so it can't
    be used for path traversal."""
    return str(uuid.uuid4())


def sanitize_filename(original_filename: str) -> str:
    """
    Keep the display name user-friendly but strip anything that could be
    used as a path (../, absolute paths, null bytes, etc). We never use
    this value to construct a filesystem path directly — the on-disk
    filename is always `{document_id}.pdf`.
    """
    name = Path(original_filename).name  # drops any directory components
    name = re.sub(r"[^A-Za-z0-9._\- ]", "_", name)
    return name[:255] if name else "document.pdf"


def validate_upload(
    filename: str,
    content_type: str | None,
    file_size_bytes: int,
    max_file_size_mb: int,
) -> None:
    """Raises PDFValidationError with a user-friendly message on any
    validation failure. Called BEFORE we touch the file contents."""

    if not filename.lower().endswith(ALLOWED_EXTENSION):
        raise PDFValidationError("Only .pdf files are supported.")

    if content_type and content_type not in ALLOWED_MIME_TYPES:
        raise PDFValidationError(
            f"Invalid file type '{content_type}'. Expected application/pdf."
        )

    if file_size_bytes == 0:
        raise PDFValidationError("The uploaded file is empty.")

    max_bytes = max_file_size_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise PDFValidationError(
            f"File is too large ({file_size_bytes / (1024*1024):.1f} MB). "
            f"Maximum allowed size is {max_file_size_mb} MB."
        )


def _clean_text(raw_text: str) -> str:
    """
    Light cleaning only — we deliberately do NOT aggressively rewrite the
    text, since that risks destroying meaning before it ever reaches the
    embedding model.
    """
    text = raw_text.replace("\x00", "")
    # Collapse 3+ blank lines down to a single blank line.
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse runs of horizontal whitespace (not newlines) to one space.
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def extract_pages(file_path: str) -> list[PageContent]:
    """
    Opens the PDF with PyMuPDF and extracts text page by page, preserving
    page numbers (1-indexed, matching what a human would see in a PDF
    viewer). This is the ONLY place page numbers are assigned — every
    downstream chunk/citation traces back to this.
    """
    try:
        doc = fitz.open(file_path)
    except Exception as exc:  # PyMuPDF raises its own exception types
        raise PDFExtractionError(f"Could not open PDF: {exc}") from exc

    if doc.page_count == 0:
        doc.close()
        raise PDFExtractionError("The PDF has no pages.")

    pages: list[PageContent] = []
    for index in range(doc.page_count):
        page = doc.load_page(index)
        raw_text = page.get_text()
        cleaned = _clean_text(raw_text)
        pages.append(PageContent(page_number=index + 1, text=cleaned))

    doc.close()

    total_chars = sum(len(p.text) for p in pages)
    if total_chars == 0:
        raise PDFExtractionError(
            "No extractable text was found in this PDF. It may be a "
            "scanned/image-only document — OCR is not yet supported."
        )

    logger.info(
        "Extracted %d pages (%d total characters) from %s",
        len(pages),
        total_chars,
        file_path,
    )
    return pages
