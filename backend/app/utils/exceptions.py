"""
Custom exceptions for the document pipeline.

Using specific exception types (instead of generic ValueError everywhere)
lets the API layer map each failure to the right HTTP status code and a
clean user-facing message — similar to how you'd define custom Error
subclasses in a Node/Nest service.
"""


class PDFValidationError(Exception):
    """Raised when an uploaded file fails validation (wrong type, too
    large, empty, etc). Maps to HTTP 400."""


class PDFExtractionError(Exception):
    """Raised when a file passes validation but PyMuPDF can't extract any
    usable text from it (e.g. a scanned image PDF with no text layer).
    Maps to HTTP 422."""


class DocumentNotFoundError(Exception):
    """Raised when a document_id doesn't exist in the store. Maps to
    HTTP 404."""


class EmbeddingError(Exception):
    """Raised when the embedding API call fails (bad key, rate limit,
    network error). Maps to HTTP 502 for query-time failures, or marks a
    document FAILED during ingestion."""


class VectorStoreError(Exception):
    """Raised when ChromaDB read/write fails."""


class LLMError(Exception):
    """Raised when the chat/completions API call fails."""
