"""Application configuration.

Every value comes from environment variables (optionally a `.env` file at the
repository root — see `.env.example`). Nothing is hardcoded: the placeholder
database password below only exists so local demo mode boots without any
setup, and it is not a secret.
"""

from __future__ import annotations

import re
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_KEY_MIN_LENGTH = 16
_API_KEY_NAME = re.compile(r"^[A-Za-z0-9._-]{1,64}$")  # audit_logs.actor is VARCHAR(64)


def parse_api_keys(raw: str) -> dict[str, str]:
    """Parse `name:key,name:key` into {key: name}. Raises ValueError when malformed.

    Misconfiguration must fail at startup, not silently leave writes open or
    attribute them to the wrong person.
    """
    keys: dict[str, str] = {}
    names: set[str] = set()
    for entry in (part.strip() for part in raw.split(",")):
        if not entry:
            continue
        name, sep, key = entry.partition(":")
        if not sep or not _API_KEY_NAME.match(name):
            raise ValueError(
                "API_KEYS entries must look like name:key (name = [A-Za-z0-9._-]{1,64})."
            )
        if len(key) < API_KEY_MIN_LENGTH:
            raise ValueError(
                f"API key for {name!r} must be at least {API_KEY_MIN_LENGTH} characters."
            )
        if key in keys or name in names:
            raise ValueError(f"API_KEYS contains a duplicate name or key ({name!r}).")
        keys[key] = name
        names.add(name)
    return keys


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

    # --- AI advisor (Phase 14; "mock" = deterministic, offline) ---------
    ai_provider: str = "mock"  # mock | openai-compatible
    ai_base_url: str = ""  # e.g. https://api.openai.com/v1 (set with AI_API_KEY)
    ai_api_key: str = ""  # from environment / Secret Manager — never committed
    ai_model: str = ""

    # --- BigQuery billing export (Phase 8; empty = not configured) ------
    gcp_billing_project: str = ""
    gcp_billing_dataset: str = ""
    gcp_billing_table: str = ""
    gcp_billing_location: str = "US"
    gcp_billing_max_days: int = 92
    gcp_billing_max_rows: int = 100_000
    # --- Cloud Monitoring usage metrics (Phase 9; empty = not configured) --
    gcp_monitoring_project: str = ""
    gcp_monitoring_max_days: int = 30
    gcp_monitoring_max_age_days: int = 7
    # Billing data freshness: max acceptable age of the newest data day (§41)
    freshness_max_hours: int = 48

    # --- write-endpoint authentication ---------------------------------
    # `name:key,name:key`. The name becomes the audit-log actor. Empty = every
    # write endpoint refuses (fail closed). Generate keys: openssl rand -hex 24
    api_keys: str = ""

    @field_validator("api_keys")
    @classmethod
    def _validate_api_keys(cls, value: str) -> str:
        parse_api_keys(value)
        return value

    @property
    def api_key_identities(self) -> dict[str, str]:
        """Configured credentials as {key: identity name}."""
        return parse_api_keys(self.api_keys)

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
