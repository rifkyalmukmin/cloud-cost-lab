from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "development"
    demo_mode: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True
    database_url: str = "postgresql://cloudcost:cloudcost@localhost:5432/cloudcost"
    log_level: str = "INFO"
    log_format: str = "json"

    # GCP Billing (only needed when DEMO_MODE=false)
    gcp_billing_project: Optional[str] = None
    gcp_billing_dataset: Optional[str] = None
    gcp_billing_table: Optional[str] = None


settings = Settings()
