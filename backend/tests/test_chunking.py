from app.models.document import PageContent
from app.services.chunking_service import chunk_document


def test_chunk_document_preserves_page_and_document_metadata():
    pages = [
        PageContent(page_number=1, text="First page content about authentication."),
        PageContent(page_number=2, text="Second page content about rate limiting."),
    ]
    chunks = chunk_document(
        document_id="doc-1",
        document_name="architecture.pdf",
        pages=pages,
        chunk_size=1000,
        chunk_overlap=200,
    )

    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 2
    assert all(c.document_id == "doc-1" for c in chunks)
    assert all(c.document_name == "architecture.pdf" for c in chunks)
    # chunk_index is globally sequential across the whole document
    assert [c.chunk_index for c in chunks] == [0, 1]
    # chunk_id is derived from document_id + index, so it's stable/unique
    assert chunks[0].chunk_id == "doc-1_0"
    assert chunks[1].chunk_id == "doc-1_1"


def test_chunk_document_respects_chunk_size():
    long_paragraph = "word " * 500  # ~2500 characters, well over chunk_size
    pages = [PageContent(page_number=1, text=long_paragraph)]

    chunks = chunk_document(
        document_id="doc-2",
        document_name="big.pdf",
        pages=pages,
        chunk_size=500,
        chunk_overlap=50,
    )

    assert len(chunks) > 1
    # Overlap adds a bit of extra text, so allow some slack over chunk_size.
    assert all(len(c.text) <= 500 + 100 for c in chunks)


def test_chunk_document_applies_overlap_between_chunks():
    # Two long paragraphs that won't fit in one chunk together.
    para_a = "Alpha section. " * 40
    para_b = "Beta section. " * 40
    text = f"{para_a}\n\n{para_b}"
    pages = [PageContent(page_number=1, text=text)]

    chunks = chunk_document(
        document_id="doc-3",
        document_name="overlap.pdf",
        pages=pages,
        chunk_size=300,
        chunk_overlap=50,
    )

    assert len(chunks) >= 2
    # The second chunk should start with a tail slice of the first chunk's
    # text (the overlap), not begin exactly where the first chunk ended.
    first_tail = chunks[0].text[-50:]
    assert first_tail.split()[0] in chunks[1].text


def test_chunk_document_skips_empty_pages():
    pages = [
        PageContent(page_number=1, text="Real content here."),
        PageContent(page_number=2, text="   "),  # whitespace-only
    ]
    chunks = chunk_document(
        document_id="doc-4",
        document_name="sparse.pdf",
        pages=pages,
        chunk_size=1000,
        chunk_overlap=200,
    )
    assert len(chunks) == 1
    assert chunks[0].page_number == 1
