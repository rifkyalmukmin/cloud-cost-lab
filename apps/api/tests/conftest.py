"""Test suite for the Cloud Cost Lab API (Phase 1).

Tests run against a dedicated PostgreSQL database (`cloud_cost_lab_test`):
migrations are applied and the deterministic mock dataset is seeded once per
session. Requires the docker compose Postgres to be running:
    docker compose up -d postgres && pytest
"""

from __future__ import annotations

import os
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
API_DIR = TESTS_DIR.parent
# apps/api/tests -> repo root (two levels above the API package).
REPO_ROOT = API_DIR.parent.parent

MOCK_DATA_DIR = REPO_ROOT / "data" / "mock"


def _load_repo_root_env() -> None:
    """Load the repository-root .env (if any) before costlab settings are read,
    so tests use the same database host/port as local development regardless
    of the directory pytest is started from."""
    env_file = REPO_ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_repo_root_env()
# The default mock_data_dir is CWD-relative ("data/mock"); anchor it to the
# repository so pytest works from any directory (e.g. apps/api).
os.environ.setdefault("MOCK_DATA_DIR", str(MOCK_DATA_DIR))

import pytest  # noqa: E402
from alembic import command as alembic_command  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import Engine, make_url  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from costlab.config import get_settings  # noqa: E402
from costlab.db.session import get_session  # noqa: E402
from costlab.ingestion.loader import ingest_snapshot  # noqa: E402
from costlab.main import create_app  # noqa: E402
from costlab.providers import build_providers  # noqa: E402

MOCK_DATA_DIR = REPO_ROOT / "data" / "mock"


@pytest.fixture(scope="session")
def test_engine() -> Engine:
    """Create the dedicated test database, apply migrations, seed mock data."""
    settings = get_settings()
    url = make_url(settings.sync_test_database_url)
    admin_url = url.set(database="postgres")

    admin_engine = create_engine(admin_url)
    with admin_engine.connect() as conn:
        autocommit = conn.execution_options(isolation_level="AUTOCOMMIT")
        autocommit.execute(text(f'DROP DATABASE IF EXISTS "{url.database}"'))
        autocommit.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin_engine.dispose()

    alembic_cfg = AlembicConfig(str(API_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(API_DIR / "alembic"))
    # NOTE: str(url) masks the password as "***" in SQLAlchemy 2.x — render explicitly.
    alembic_cfg.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    alembic_command.upgrade(alembic_cfg, "head")

    # create_engine accepts the URL object directly; str(url) would mask the password.
    engine = create_engine(url)
    providers = build_providers(settings)
    snapshot = providers.billing.load_snapshot()
    usage_records = providers.usage.load_usage()
    with Session(engine) as session:
        ingest_snapshot(session, snapshot, usage_records, replace_facts=False)
        session.commit()

    yield engine

    engine.dispose()
    admin_engine = create_engine(admin_url)
    with admin_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text(f'DROP DATABASE IF EXISTS "{url.database}"')
        )
    admin_engine.dispose()


@pytest.fixture(scope="session")
def session_factory(test_engine: Engine) -> sessionmaker:
    return sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture()
def db_session(session_factory: sessionmaker):
    """Direct database session for analytics unit tests (read-only usage)."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def app(session_factory: sessionmaker):
    application = create_app()

    def override_get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_session] = override_get_session
    return application


@pytest.fixture()
def client(app) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
