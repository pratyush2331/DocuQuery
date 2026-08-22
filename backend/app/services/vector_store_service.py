"""
Vector store service — wraps a persisted ChromaDB collection.

Mental model if you're coming from Mongo/Couchbase: a normal database
index lets you find documents by an EXACT or RANGE match on a field
(WHERE status = 'COMPLETED'). A vector index lets you find documents by
SIMILARITY of meaning — "give me the N chunks whose embedding vector is
closest to this query's embedding vector" (nearest-neighbor search in
1536-dimensional space). ChromaDB stores the vectors, the raw chunk text,
and arbitrary metadata (document_id, page_number, ...) together, and
`collection.query()` does the nearest-neighbor search for you.

`PersistentClient` writes to disk under CHROMA_PERSIST_DIRECTORY, which is
why restarting the backend doesn't require re-embedding already-processed
PDFs — the vectors are already on disk.
"""
import chromadb

from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.utils.exceptions import VectorStoreError

logger = get_logger(__name__)

COLLECTION_NAME = "document_chunks"


class VectorStoreService:
    def __init__(self, persist_directory: str) -> None:
        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                f"Chunk/embedding count mismatch: {len(chunks)} vs {len(embeddings)}"
            )
        try:
            self._collection.add(
                ids=[c.chunk_id for c in chunks],
                embeddings=embeddings,
                documents=[c.text for c in chunks],
                metadatas=[
                    {
                        "document_id": c.document_id,
                        "document_name": c.document_name,
                        "page_number": c.page_number,
                        "chunk_index": c.chunk_index,
                    }
                    for c in chunks
                ],
            )
        except Exception as exc:  # chromadb raises assorted internal errors
            raise VectorStoreError(f"Failed to index chunks: {exc}") from exc

        logger.info("Indexed %d chunks into ChromaDB", len(chunks))

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        document_id: str | None = None,
    ) -> list[dict]:
        """
        Returns the top_k most similar chunks as a list of dicts:
        {chunk_id, text, page_number, document_name, similarity_score}

        similarity_score is derived from cosine DISTANCE (0 = identical,
        2 = opposite) returned by Chroma, converted to a 0-1 similarity
        where 1 = most similar, so the frontend can show something more
        intuitive than a raw distance.
        """
        where = {"document_id": document_id} if document_id else None
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
            )
        except Exception as exc:
            raise VectorStoreError(f"Vector search failed: {exc}") from exc

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        retrieved = []
        for chunk_id, text, metadata, distance in zip(
            ids, documents, metadatas, distances
        ):
            similarity_score = max(0.0, 1 - (distance / 2))
            retrieved.append(
                {
                    "chunk_id": chunk_id,
                    "text": text,
                    "document_name": metadata.get("document_name"),
                    "page_number": metadata.get("page_number"),
                    "similarity_score": round(similarity_score, 4),
                }
            )
        return retrieved

    def delete_document(self, document_id: str) -> None:
        try:
            self._collection.delete(where={"document_id": document_id})
        except Exception as exc:
            raise VectorStoreError(f"Failed to delete document vectors: {exc}") from exc
        logger.info("Deleted vectors for document %s", document_id)


_vector_store_service: VectorStoreService | None = None


def get_vector_store_service() -> VectorStoreService:
    """Lazy singleton — constructed on first use so import order doesn't
    matter and tests can set CHROMA_PERSIST_DIRECTORY before first call."""
    global _vector_store_service
    if _vector_store_service is None:
        from app.core.config import get_settings

        settings = get_settings()
        _vector_store_service = VectorStoreService(settings.chroma_persist_directory)
    return _vector_store_service
