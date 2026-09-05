"""Application configuration.

Every value comes from environment variables (optionally a `.env` file at the
repository root — see `.env.example`). Nothing is hardcoded: the placeholder
database password below only exists so local demo mode boots without any
setup, and it is not a secret.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- runtime mode (ADR-003: mock by default) ---
    demo_mode: bool = True
    log_level: str = "INFO"
    mock_data_dir: str = "data/mock"

    # --- database (Phase 1: local PostgreSQL via docker compose) ---
    database_url: str | None = None  # full override; built from POSTGRES_* otherwise
    test_database_url: str | None = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "cloud_cost_lab"
    postgres_user: str = "cloud_cost_lab"
    postgres_password: str = "change-me-local-only"  # local-only placeholder

    # --- api ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_version: str = "0.1.0"
    # Comma-separated origins allowed to call the API from a browser (Phase 2 dashboard).
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sync_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            "postgresql+psycopg2://"
            f"{quote_plus(self.postgres_user)}:{quote_plus(self.postgres_password)}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_test_database_url(self) -> str:
        """Dedicated database for the test suite, derived from the dev URL by default."""
        if self.test_database_url:
            return self.test_database_url
        return f"{self.sync_database_url}_test"


@lru_cache
def get_settings() -> Settings:
    return Settings()
