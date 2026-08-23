"""
Document endpoints: upload, list, status, delete.

Processing is synchronous for V1 (per the "do not introduce Celery/Kafka
yet" constraint) — the upload request extracts text before returning. This
is fine for typical PDFs; will extend this same synchronous flow
to also chunk, embed, and index before marking a document COMPLETED.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.document import (
    Document,
    DocumentListResponse,
    DocumentResponse,
    DocumentStatus,
)
from app.services import chunking_service, embedding_service, pdf_service
from app.services.document_store import document_store
from app.services.vector_store_service import get_vector_store_service
from app.utils.exceptions import (
    EmbeddingError,
    PDFExtractionError,
    PDFValidationError,
    VectorStoreError,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post(
    "/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> DocumentResponse:
    contents = await file.read()

    # --- 1. Validate before writing anything to disk ---
    try:
        pdf_service.validate_upload(
            filename=file.filename or "",
            content_type=file.content_type,
            file_size_bytes=len(contents),
            max_file_size_mb=settings.max_file_size_mb,
        )
    except PDFValidationError as exc:
        logger.warning("Upload rejected: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # --- 2. Persist the file under a generated, safe ID (never trust the
    #        original filename for the on-disk path) ---
    document_id = pdf_service.generate_safe_document_id()
    safe_display_name = pdf_service.sanitize_filename(file.filename or "document.pdf")

    upload_dir = Path(settings.upload_directory)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{document_id}.pdf"
    file_path.write_bytes(contents)

    document = Document(
        document_id=document_id,
        document_name=safe_display_name,
        status=DocumentStatus.PROCESSING,
        file_path=str(file_path),
        file_size_bytes=len(contents),
    )
    document_store.add(document)
    logger.info("Document uploaded: %s (%s)", document_id, safe_display_name)

    # --- 3. Process: extract -> chunk -> embed -> index (all
    #        synchronous for V1). Any failure at any step marks the
    #        document FAILED with a specific error_message. ---
    try:
        pages = pdf_service.extract_pages(str(file_path))
        document_store.set_pages(document_id, pages)

        chunks = chunking_service.chunk_document(
            document_id=document_id,
            document_name=safe_display_name,
            pages=pages,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        embeddings = embedding_service.get_embeddings([c.text for c in chunks])
        get_vector_store_service().add_chunks(chunks, embeddings)

        document_store.update_status(
            document_id,
            DocumentStatus.COMPLETED,
            page_count=len(pages),
            chunk_count=len(chunks),
        )
        logger.info(
            "Document processed: %s (%d pages, %d chunks)",
            document_id,
            len(pages),
            len(chunks),
        )
    except PDFExtractionError as exc:
        document_store.update_status(
            document_id, DocumentStatus.FAILED, error_message=str(exc)
        )
        logger.error("Document processing failed: %s (%s)", document_id, exc)
    except (EmbeddingError, VectorStoreError) as exc:
        document_store.update_status(
            document_id, DocumentStatus.FAILED, error_message=str(exc)
        )
        logger.error("Document indexing failed: %s (%s)", document_id, exc)
        # We still return 201 — the document WAS created, it just ended in
        # FAILED status. The frontend surfaces error_message from the
        # returned object rather than treating this as an HTTP error.

    updated = document_store.get(document_id)
    assert updated is not None
    return DocumentResponse.from_document(updated)


@router.get("", response_model=DocumentListResponse)
def list_documents() -> DocumentListResponse:
    docs = document_store.list_all()
    return DocumentListResponse(
        documents=[DocumentResponse.from_document(d) for d in docs]
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str) -> DocumentResponse:
    doc = document_store.get(document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse.from_document(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str) -> None:
    doc = document_store.get(document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_path = Path(doc.file_path)
    if file_path.exists():
        file_path.unlink()

    document_store.delete(document_id)
    get_vector_store_service().delete_document(document_id)
    logger.info("Document deleted: %s", document_id)
