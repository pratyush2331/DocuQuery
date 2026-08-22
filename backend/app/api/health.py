"""
Health check endpoint.

Useful for the frontend to detect "backend not running" vs a real error,
and later for Docker healthchecks.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter(prefix="/api/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    openai_key_configured: bool


@router.get("", response_model=HealthResponse)
def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
        # We surface WHETHER the key is set, never the key itself.
        openai_key_configured=bool(settings.openai_api_key),
    )
