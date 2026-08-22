"""
In-memory document store.

For V1 we intentionally avoid adding Postgres/Mongo here (see the "do not
overengineer" constraint) — a process-lifetime dict is enough to learn the
RAG pipeline. The store also holds each document's extracted pages in
memory so Phase 3 (chunking) can read them without re-parsing the PDF.

Swapping this for a real database later only means reimplementing this
one class — nothing in the API layer needs to change, since routes only
depend on this interface.
"""
import threading
from typing import Optional

from app.models.document import Document, PageContent


class DocumentStore:
    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._pages: dict[str, list[PageContent]] = {}
        self._lock = threading.Lock()

    def add(self, document: Document) -> None:
        with self._lock:
            self._documents[document.document_id] = document

    def get(self, document_id: str) -> Optional[Document]:
        return self._documents.get(document_id)

    def list_all(self) -> list[Document]:
        return sorted(
            self._documents.values(), key=lambda d: d.created_at, reverse=True
        )

    def update_status(
        self,
        document_id: str,
        status,
        page_count: Optional[int] = None,
        chunk_count: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        with self._lock:
            doc = self._documents.get(document_id)
            if doc is None:
                return
            doc.status = status
            if page_count is not None:
                doc.page_count = page_count
            if chunk_count is not None:
                doc.chunk_count = chunk_count
            if error_message is not None:
                doc.error_message = error_message

    def delete(self, document_id: str) -> bool:
        with self._lock:
            self._pages.pop(document_id, None)
            return self._documents.pop(document_id, None) is not None

    def set_pages(self, document_id: str, pages: list[PageContent]) -> None:
        with self._lock:
            self._pages[document_id] = pages

    def get_pages(self, document_id: str) -> Optional[list[PageContent]]:
        return self._pages.get(document_id)


# Process-wide singleton, mirroring how you'd inject a single repository
# instance via FastAPI's Depends() elsewhere.
document_store = DocumentStore()
