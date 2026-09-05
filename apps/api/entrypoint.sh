#!/bin/sh
# API container entrypoint: migrate -> seed (demo, idempotent) -> serve.
set -e

echo '{"level":"INFO","message":"running database migrations"}'
alembic upgrade head

echo '{"level":"INFO","message":"seeding demo data (no-op if already seeded)"}'
python -m costlab.seed

exec "$@"
