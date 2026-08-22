"""
API tests for /api/documents/*. Uses FastAPI's TestClient (backed by
httpx), no live server or network access required.
"""
import io

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_pdf_bytes(pages_text: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_upload_valid_pdf_returns_completed(client):
    pdf_bytes = _make_pdf_bytes(["Hello world", "Second page"])
    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["page_count"] == 2
    assert body["document_name"] == "test.pdf"


def test_upload_rejects_non_pdf(client):
    response = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400


def test_upload_rejects_empty_file(client):
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert response.status_code == 400


def test_list_documents_after_upload(client):
    pdf_bytes = _make_pdf_bytes(["Some content"])
    client.post(
        "/api/documents/upload",
        files={"file": ("a.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    response = client.get("/api/documents")
    assert response.status_code == 200
    assert len(response.json()["documents"]) == 1


def test_get_nonexistent_document_returns_404(client):
    response = client.get("/api/documents/does-not-exist")
    assert response.status_code == 404


def test_delete_document(client):
    pdf_bytes = _make_pdf_bytes(["Some content"])
    upload_resp = client.post(
        "/api/documents/upload",
        files={"file": ("a.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = upload_resp.json()["document_id"]

    delete_resp = client.delete(f"/api/documents/{doc_id}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/api/documents/{doc_id}")
    assert get_resp.status_code == 404


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_query_against_completed_document_returns_grounded_answer(client):
    pdf_bytes = _make_pdf_bytes(["Authentication uses OAuth 2.0 for all API access."])
    upload_resp = client.post(
        "/api/documents/upload",
        files={"file": ("auth.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = upload_resp.json()["document_id"]
    assert upload_resp.json()["status"] == "COMPLETED"

    chat_resp = client.post(
        "/api/chat/query",
        json={"document_id": doc_id, "question": "How does authentication work?"},
    )
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert body["answer"]  # mocked LLM always returns non-empty text
    assert len(body["sources"]) >= 1
    assert body["sources"][0]["document_name"] == "auth.pdf"
    assert len(body["retrieved_chunks"]) >= 1


def test_chat_query_against_nonexistent_document_returns_404(client):
    response = client.post(
        "/api/chat/query",
        json={"document_id": "does-not-exist", "question": "Anything?"},
    )
    assert response.status_code == 404


def test_chat_query_rejects_empty_question(client):
    pdf_bytes = _make_pdf_bytes(["Some content."])
    upload_resp = client.post(
        "/api/documents/upload",
        files={"file": ("a.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = upload_resp.json()["document_id"]

    response = client.post(
        "/api/chat/query", json={"document_id": doc_id, "question": ""}
    )
    assert response.status_code == 422  # Pydantic min_length validation


def test_chat_query_on_unrelated_topic_does_not_hallucinate(client, monkeypatch):
    """
    Acceptance criterion from the spec: uploading a document about one
    topic and asking about something completely unrelated should not
    produce a fabricated answer. We simulate 'no relevant chunks found'
    by forcing the vector store to return nothing, which is the real
    trigger for the fixed no-context response in the chat endpoint.
    """
    from app.services.vector_store_service import get_vector_store_service

    pdf_bytes = _make_pdf_bytes(["This document is only about Kubernetes pods."])
    upload_resp = client.post(
        "/api/documents/upload",
        files={"file": ("k8s.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = upload_resp.json()["document_id"]

    monkeypatch.setattr(
        get_vector_store_service(), "query", lambda **kwargs: []
    )

    response = client.post(
        "/api/chat/query",
        json={"document_id": doc_id, "question": "What is the population of France?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "I couldn't find this information in the provided documents."
    assert body["sources"] == []
