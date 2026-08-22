"""
Shared pytest fixtures.

Two important things happen here:
1. CHROMA_PERSIST_DIRECTORY / UPLOAD_DIRECTORY are pointed at fresh temp
   dirs BEFORE any app module is imported, so tests never touch (or
   pollute) backend/data/.
2. `mock_ai_services` monkeypatches the embedding and LLM services with
   deterministic fakes, so the entire test suite runs with NO OpenAI API
   key and NO network access (per the "do not require an actual OpenAI
   API key to run the test suite" requirement).
"""
import hashlib
import os
import tempfile

# Must happen before any `app.*` module is imported anywhere in the test
# session, since Settings() reads the environment once and get_settings()
# is cached.
os.environ["CHROMA_PERSIST_DIRECTORY"] = tempfile.mkdtemp(prefix="chroma_test_")
os.environ["UPLOAD_DIRECTORY"] = tempfile.mkdtemp(prefix="uploads_test_")

import pytest  # noqa: E402


def _fake_embedding(text: str, dims: int = 16) -> list[float]:
    """Deterministic, dependency-free 'embedding': hash the text into a
    fixed-length float vector. Not semantically meaningful, but stable
    and good enough to exercise chunking/indexing/retrieval plumbing
    without calling OpenAI."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [b / 255 for b in digest[:dims]]


@pytest.fixture(autouse=True)
def mock_ai_services(monkeypatch):
    from app.services import embedding_service, llm_service

    def fake_get_embeddings(texts: list[str]) -> list[list[float]]:
        return [_fake_embedding(t) for t in texts]

    def fake_get_embedding(text: str) -> list[float]:
        return _fake_embedding(text)

    def fake_generate_answer(prompt: str) -> str:
        return "This is a mocked answer generated without calling OpenAI."

    monkeypatch.setattr(embedding_service, "get_embeddings", fake_get_embeddings)
    monkeypatch.setattr(embedding_service, "get_embedding", fake_get_embedding)
    monkeypatch.setattr(llm_service, "generate_answer", fake_generate_answer)


@pytest.fixture(autouse=True)
def clear_document_store():
    from app.services.document_store import document_store

    document_store._documents.clear()
    document_store._pages.clear()
    yield


@pytest.fixture(autouse=True)
def clear_vector_store():
    """Each test gets a clean Chroma collection so retrieval tests don't
    see chunks left over from other tests."""
    from app.services.vector_store_service import get_vector_store_service

    store = get_vector_store_service()
    try:
        store._collection.delete(where={"document_id": {"$ne": "__never__"}})
    except Exception:
        pass
    yield
