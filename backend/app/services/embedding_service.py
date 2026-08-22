"""
Embedding service.

What an embedding is: a fixed-length list of floats (e.g. 1536 numbers for
text-embedding-3-small) that represents the MEANING of a piece of text.
Two chunks of text discussing the same idea in different words end up
with vectors that are close together in that 1536-dimensional space, even
if they don't share a single word. That's what makes "semantic search"
different from keyword search (like a SQL LIKE '%auth%') — it can find
"How do I log in?" as relevant to a chunk about "OAuth 2.0 authentication"
even though no words overlap.

We call OpenAI directly here (not through LangChain) so the actual API
call is visible rather than hidden behind an abstraction.
"""
from openai import APIError, OpenAI, RateLimitError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.utils.exceptions import EmbeddingError

logger = get_logger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Lazily constructed so importing this module never requires an API
    key to be set (tests monkeypatch the functions below instead of
    hitting this client at all)."""
    global _client
    if _client is None:
        settings = get_settings()
        # _client = OpenAI(api_key=settings.openai_api_key)
        _client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
    return _client


def get_embedding(text: str) -> list[float]:
    """Embeds a single string — used for the user's question at query time."""
    return get_embeddings([text])[0]


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Embeds a batch of strings in one API call — used for a document's
    chunks at ingestion time. Batching is both faster and cheaper than
    one call per chunk.
    """
    if not texts:
        return []

    settings = get_settings()
    if not settings.openai_api_key:
        raise EmbeddingError(
            "OPENAI_API_KEY is not set. Add it to backend/.env to enable "
            "embeddings."
        )

    try:
        response = _get_client().embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
    except RateLimitError as exc:
        logger.warning("Embedding rate limit hit: %s", exc)
        raise EmbeddingError(
            "This demo is temporarily rate-limited. Please try again in a moment."
        ) from exc
    except APIError as exc:
        logger.error("Embedding API call failed: %s", exc)
        raise EmbeddingError(f"Embedding request failed: {exc}") from exc

    # The API returns results in the same order as the input list.
    return [item.embedding for item in response.data]
