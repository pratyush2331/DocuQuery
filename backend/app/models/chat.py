"""
Chat/query domain models.
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    document_id: str
    question: str = Field(min_length=1, max_length=2000)


class Source(BaseModel):
    document_name: str
    page_number: int
    chunk_id: str


class RetrievedChunkInfo(BaseModel):
    """Debug/inspection info for the 'View retrieved context' UI panel."""

    chunk_id: str
    page_number: int
    similarity_score: float
    text: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    retrieved_chunks: list[RetrievedChunkInfo]
