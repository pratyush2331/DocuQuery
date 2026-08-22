"""
Chunking service.

WHY chunk size and overlap matter (this is worth understanding, not just
configuring):

- Embedding models turn text into a fixed-length vector that represents
  its MEANING. A single vector for an entire 10-page PDF would be so
  "averaged out" that it stops being useful for finding a specific fact.
  Smaller chunks give more precise, specific vectors — but too small and
  a chunk loses the surrounding context needed to answer a question.
- CHUNK_OVERLAP exists because naive splitting can cut a sentence (or an
  idea) exactly at a chunk boundary. If chunk N ends mid-sentence and
  chunk N+1 starts with the rest, neither chunk alone contains the full
  thought. Overlap duplicates a bit of trailing text from the previous
  chunk into the next one so that boundary content is still retrievable
  in at least one complete chunk.
- We chunk PER PAGE (never spanning a page boundary) so every chunk has
  one unambiguous page_number for citations. The trade-off: a paragraph
  that straddles a page break may be split even with overlap on. That's
  an acceptable V1 simplification — noted here rather than hidden.
"""
import re

from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.document import PageContent

logger = get_logger(__name__)


def _split_into_paragraphs(text: str) -> list[str]:
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _split_oversized_paragraph(
    paragraph: str, chunk_size: int, chunk_overlap: int
) -> list[str]:
    """A single paragraph longer than chunk_size can't be packed whole, so
    we fall back to a sliding character window over it."""
    pieces = []
    start = 0
    step = max(chunk_size - chunk_overlap, 1)  # guard against overlap >= size
    while start < len(paragraph):
        end = start + chunk_size
        pieces.append(paragraph[start:end].strip())
        start += step
    return [p for p in pieces if p]


def _chunk_page_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    Greedily packs paragraphs into chunks up to chunk_size characters,
    then prepends a trailing slice of the previous chunk to each
    subsequent chunk to create the configured overlap.
    """
    if not text.strip():
        return []

    paragraphs = _split_into_paragraphs(text)
    raw_chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate_len = len(current) + len(paragraph) + 2
        if candidate_len <= chunk_size:
            current = f"{current}\n\n{paragraph}" if current else paragraph
            continue

        if current:
            raw_chunks.append(current)
            current = ""

        if len(paragraph) > chunk_size:
            raw_chunks.extend(
                _split_oversized_paragraph(paragraph, chunk_size, chunk_overlap)
            )
        else:
            current = paragraph

    if current:
        raw_chunks.append(current)

    if not raw_chunks:
        return []

    # Apply overlap: each chunk (after the first) is prefixed with the
    # tail of the previous chunk.
    overlapped: list[str] = [raw_chunks[0]]
    for i in range(1, len(raw_chunks)):
        prev_tail = raw_chunks[i - 1][-chunk_overlap:] if chunk_overlap > 0 else ""
        overlapped.append(f"{prev_tail} {raw_chunks[i]}".strip())

    return overlapped


def chunk_document(
    document_id: str,
    document_name: str,
    pages: list[PageContent],
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Turns a document's extracted pages into page-aware chunks with
    globally unique, sequential chunk_index values."""
    chunks: list[Chunk] = []
    chunk_index = 0

    for page in pages:
        page_texts = _chunk_page_text(page.text, chunk_size, chunk_overlap)
        for text in page_texts:
            chunks.append(
                Chunk(
                    chunk_id=f"{document_id}_{chunk_index}",
                    document_id=document_id,
                    document_name=document_name,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    text=text,
                )
            )
            chunk_index += 1

    logger.info(
        "Chunked document %s into %d chunks (chunk_size=%d, overlap=%d)",
        document_id,
        len(chunks),
        chunk_size,
        chunk_overlap,
    )
    return chunks
