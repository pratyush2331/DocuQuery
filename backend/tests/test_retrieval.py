"""
Retrieval tests. The `mock_ai_services` and `clear_vector_store` fixtures
from conftest.py apply automatically (autouse) — no OpenAI key needed.
"""
from app.models.chunk import Chunk
from app.services import embedding_service
from app.services.retrieval_service import retrieve_relevant_chunks
from app.services.vector_store_service import get_vector_store_service


def _index_chunks(document_id: str, document_name: str, texts: list[str]) -> None:
    chunks = [
        Chunk(
            chunk_id=f"{document_id}_{i}",
            document_id=document_id,
            document_name=document_name,
            page_number=i + 1,
            chunk_index=i,
            text=text,
        )
        for i, text in enumerate(texts)
    ]
    embeddings = embedding_service.get_embeddings(texts)
    get_vector_store_service().add_chunks(chunks, embeddings)


def test_retrieve_returns_relevant_chunks():
    _index_chunks(
        "doc-a",
        "a.pdf",
        ["Authentication uses OAuth 2.0 tokens.", "Rate limiting is 100 req/min."],
    )

    results = retrieve_relevant_chunks(
        question="How does authentication work?", document_id="doc-a", top_k=5
    )

    assert len(results) == 2
    assert all(r.document_name == "a.pdf" for r in results)
    assert all(0.0 <= r.similarity_score <= 1.0 for r in results)


def test_retrieve_filters_by_document_id():
    _index_chunks("doc-b", "b.pdf", ["Content about billing."])
    _index_chunks("doc-c", "c.pdf", ["Content about shipping."])

    results = retrieve_relevant_chunks(
        question="Tell me about billing", document_id="doc-b", top_k=5
    )

    assert len(results) == 1
    assert results[0].document_name == "b.pdf"


def test_retrieve_respects_top_k():
    _index_chunks(
        "doc-d",
        "d.pdf",
        [f"Chunk number {i} discussing topic {i}." for i in range(10)],
    )

    results = retrieve_relevant_chunks(
        question="topic 3", document_id="doc-d", top_k=3
    )

    assert len(results) == 3


def test_retrieve_returns_empty_for_unindexed_document():
    results = retrieve_relevant_chunks(
        question="anything", document_id="does-not-exist", top_k=5
    )
    assert results == []
