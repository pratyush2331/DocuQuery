"""
Document domain models.

These are the Pydantic equivalent of the DTOs/interfaces you'd write in a
Node service — used both for internal state and for API response shapes
(FastAPI auto-generates the OpenAPI schema from these).
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PageContent(BaseModel):
    """Raw extracted text for a single PDF page. Produced by pdf_service,
    consumed by the chunking service"""

    page_number: int
    text: str


class Document(BaseModel):
    """
    Internal representation of an uploaded document, held in the in-memory
    DocumentStore. Will attach chunk_count / indexed_at once
    chunking and embedding are implemented.
    """

    document_id: str
    document_name: str
    status: DocumentStatus = DocumentStatus.UPLOADED
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    file_path: str
    file_size_bytes: int
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentResponse(BaseModel):
    """Public API shape — deliberately excludes file_path so we never leak
    server filesystem layout to the client."""

    document_id: str
    document_name: str
    status: DocumentStatus
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime

    @classmethod
    def from_document(cls, doc: Document) -> "DocumentResponse":
        return cls(
            document_id=doc.document_id,
            document_name=doc.document_name,
            status=doc.status,
            page_count=doc.page_count,
            chunk_count=doc.chunk_count,
            error_message=doc.error_message,
            created_at=doc.created_at,
        )


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
