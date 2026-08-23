"""
Embedding service.

What an embedding is: a fixed-length list of floats that represents the
MEANING of a piece of text. Two chunks discussing the same idea in
different words end up with vectors close together in that space, even
if they don't share a single word — that's what makes semantic search
different from keyword search.

Uses Hugging Face's Inference Providers feature-extraction endpoint via
the huggingface_hub client, since HF's OpenAI-compatible /v1 router only
covers chat completions, not embeddings.
"""
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.utils.exceptions import EmbeddingError

logger = get_logger(__name__)

_client: InferenceClient | None = None


def _get_client() -> InferenceClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = InferenceClient(
            provider="hf-inference",
            api_key=settings.openai_api_key,  # holds the HF token
        )
    return _client


def get_embedding(text: str) -> list[float]:
    """Embeds a single string — used for the user's question at query time."""
    return get_embeddings([text])[0]


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Embeds a batch of strings — used for a document's chunks at
    ingestion time."""
    if not texts:
        return []

    settings = get_settings()
    if not settings.openai_api_key:
        raise EmbeddingError(
            "No Hugging Face token configured. Add it to backend/.env."
        )

    try:
        embeddings = []
        for text in texts:
            result = _get_client().feature_extraction(
                text,
                model=settings.embedding_model,
            )
            # result is a numpy array; convert to a plain list of floats
            # for JSON/Chroma compatibility.
            embeddings.append(result.tolist() if hasattr(result, "tolist") else list(result))
        return embeddings
    except HfHubHTTPError as exc:
        logger.error("Embedding API call failed: %s", exc)
        raise EmbeddingError(f"Embedding request failed: {exc}") from exc