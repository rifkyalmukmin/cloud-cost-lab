from fastapi import APIRouter

from app.config import settings
from app.services.cost_service import cost_service

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.app_env,
        "demo_mode": settings.demo_mode,
    }


@router.get("/ready")
def ready():
    provider_available = cost_service.provider.is_available()
    return {
        "status": "ready" if provider_available else "not_ready",
        "provider": "mock" if settings.demo_mode else "gcp",
        "data_loaded": provider_available,
    }


@router.get("/data-freshness")
def data_freshness():
    """Get data freshness status (FRESH/STALE/UNKNOWN)."""
    return cost_service.get_data_freshness()
