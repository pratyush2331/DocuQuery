"""
Application entrypoint.

Run with:
    uvicorn app.main:app --reload --port 8000
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.api import health, documents, chat

configure_logging(level=logging.INFO)
logger = get_logger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="DocuQuery - A Retrieval-Augmented Generation assistant for PDF documents.",
    version="0.1.0",
)

# CORS: allow the Vite dev server (or whatever FRONTEND_URL is set to) to
# call this API from the browser. Without this, the browser blocks the
# fetch/axios calls due to the Same-Origin Policy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("%s starting up (env=%s)", settings.app_name, settings.environment)
    if not settings.openai_api_key:
        logger.warning(
            "OPENAI_API_KEY is not set. Upload/query endpoints will fail "
            "once implemented until you add it to backend/.env"
        )


@app.get("/")
def root() -> dict:
    return {"message": f"{settings.app_name} API. See /docs for OpenAPI UI."}
