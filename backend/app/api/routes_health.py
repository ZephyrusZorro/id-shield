"""Health check endpoint."""
from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        tagline=settings.app_tagline,
        time=datetime.now(timezone.utc),
    )
