"""
Chat endpoint — the query-time RAG pipeline, kept explicit end to end:

    question -> embed -> vector search -> top-K chunks
             -> build context -> build prompt -> call LLM -> answer + sources
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.chat import ChatRequest, ChatResponse, RetrievedChunkInfo, Source
from app.models.document import DocumentStatus
from app.prompts.rag_prompt import build_context, build_prompt
from app.services import llm_service, retrieval_service
from app.services.document_store import document_store
from app.utils.exceptions import EmbeddingError, LLMError, VectorStoreError

logger = get_logger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

NO_CONTEXT_ANSWER = "I couldn't find this information in the provided documents."


@router.post("/query", response_model=ChatResponse)
def query(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    document = document_store.get(request.document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    if document.status != DocumentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is not ready for questions (status={document.status.value}).",
        )

    # --- Step 1 + 2: embed question, similarity search (retrieval_service) ---
    try:
        retrieved = retrieval_service.retrieve_relevant_chunks(
            question=request.question,
            document_id=request.document_id,
            top_k=settings.top_k,
        )
    except EmbeddingError as exc:
        logger.error("Embedding failed during query: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except VectorStoreError as exc:
        logger.error("Vector search failed during query: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    # No relevant chunks at all -> don't waste an LLM call, answer directly.
    # This is also what guarantees the "no hallucination on an unrelated
    # question" acceptance criterion: an empty context always yields the
    # fixed no-answer response, never an LLM guess.
    if not retrieved:
        return ChatResponse(answer=NO_CONTEXT_ANSWER, sources=[], retrieved_chunks=[])

    # --- Step 3 + 4: build context, build prompt ---
    context = build_context(retrieved)
    prompt = build_prompt(context=context, question=request.question)

    # --- Step 5: call the LLM ---
    try:
        answer = llm_service.generate_answer(prompt)
    except LLMError as exc:
        logger.error("LLM call failed during query: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    # --- Step 6: sources, deduplicated by (document_name, page_number) so
    # multiple chunks from the same page collapse into one citation card ---
    seen_pages: set[tuple[str, int]] = set()
    sources: list[Source] = []
    for chunk in retrieved:
        key = (chunk.document_name, chunk.page_number)
        if key in seen_pages:
            continue
        seen_pages.add(key)
        sources.append(
            Source(
                document_name=chunk.document_name,
                page_number=chunk.page_number,
                chunk_id=chunk.chunk_id,
            )
        )

    retrieved_chunks = [
        RetrievedChunkInfo(
            chunk_id=c.chunk_id,
            page_number=c.page_number,
            similarity_score=c.similarity_score,
            text=c.text,
        )
        for c in retrieved
    ]

    logger.info(
        "Query answered for document %s (%d sources)",
        request.document_id,
        len(sources),
    )
    return ChatResponse(answer=answer, sources=sources, retrieved_chunks=retrieved_chunks)
