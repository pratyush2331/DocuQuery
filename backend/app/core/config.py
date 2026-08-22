"""
Central application configuration.

Why this exists: instead of scattering os.getenv() calls across services
(hard to test, easy to typo a var name), we load everything once into a
typed Settings object. This is the same idea as a NestJS ConfigService or
a typed `config.ts` you'd write in a Node backend.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- LLM / Embeddings ---
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # --- Chunking ---
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # --- Retrieval ---
    top_k: int = 5

    # --- Storage ---
    chroma_persist_directory: str = "./data/chroma"
    upload_directory: str = "./data/uploads"
    max_file_size_mb: int = 20

    # --- CORS ---
    frontend_url: str = "http://localhost:5173"

    # --- App ---
    app_name: str = "DocuQuery"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """
    Cached so we don't re-read/re-parse the .env file on every request.
    Equivalent to a singleton config module in Node.
    """
    return Settings()
