"""
Chunk domain model — the unit that gets embedded and stored in ChromaDB.
"""
from pydantic import BaseModel


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    chunk_index: int
    text: str
