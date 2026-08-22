"""
Retrieval service — the explicit question -> embedding -> similarity
search -> top-K chunks flow. Deliberately not hidden behind a single
`.invoke()` call so each step is visible and separately testable:

    question
        |
        v
    create embedding      (embedding_service.get_embedding)
        |
        v
    vector similarity search   (vector_store_service.query)
        |
        v
    top-K relevant chunks
"""
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services import embedding_service
from app.services.vector_store_service import get_vector_store_service

logger = get_logger(__name__)


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    document_name: str
    page_number: int
    similarity_score: float


def retrieve_relevant_chunks(
    question: str,
    document_id: str,
    top_k: int,
) -> list[RetrievedChunk]:
    # Step 1: embed the question with the SAME embedding model used for
    # the chunks, so both live in the same vector space and distances are
    # meaningful.
    question_embedding = embedding_service.get_embedding(question)

    # Step 2: similarity search, scoped to this document only.
    raw_results = get_vector_store_service().query(
        query_embedding=question_embedding,
        top_k=top_k,
        document_id=document_id,
    )

    # Step 3: shape into a typed result.
    chunks = [RetrievedChunk(**r) for r in raw_results]
    logger.info(
        "Retrieved %d chunks for document %s (top_k=%d)",
        len(chunks),
        document_id,
        top_k,
    )
    return chunks
