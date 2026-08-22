"""
LLM service — the final step of the RAG pipeline: takes the constructed
prompt (context + question) and calls the chat/completions API to
generate a grounded answer.
"""
from openai import APIError, OpenAI, RateLimitError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.utils.exceptions import LLMError

logger = get_logger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        # _client = OpenAI(api_key=settings.openai_api_key)
        # _client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
        _client = OpenAI(api_key=settings.openai_api_key, base_url="https://router.huggingface.co/v1")

    return _client


def generate_answer(prompt: str) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMError(
            "OPENAI_API_KEY is not set. Add it to backend/.env to enable "
            "answer generation."
        )

    try:
        response = _get_client().chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # low temperature: favor grounded, consistent
            # answers over creative ones, appropriate for a QA assistant.
        )
    except RateLimitError as exc:
        logger.warning("LLM rate limit hit: %s", exc)
        raise LLMError(
            "This demo is temporarily rate-limited. Please try again in a moment."
        ) from exc
    except APIError as exc:
        logger.error("LLM API call failed: %s", exc)
        raise LLMError(f"LLM request failed: {exc}") from exc

    answer = response.choices[0].message.content
    return (answer or "").strip()
