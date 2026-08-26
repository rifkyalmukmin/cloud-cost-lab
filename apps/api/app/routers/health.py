from fastapi import APIRouter

from app.config import settings

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
    data_loaded = settings.demo_mode
    return {
        "status": "ready" if data_loaded else "not_ready",
        "database": "mock" if settings.demo_mode else "postgresql",
        "data_loaded": data_loaded,
    }
