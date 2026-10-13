# syntax=docker/dockerfile:1.7
# Cloud Cost Lab API — multi-stage, small, pinned, non-root (CLAUDE.md §50).
#
# Build from the REPOSITORY ROOT (the context includes data/mock):
#   DOCKER_BUILDKIT=1 docker build -f apps/api/Dockerfile -t cloud-cost-lab-api .
#
# Stages:
#   builder  installs the package + dependencies into a virtualenv. The pip
#            download/wheel cache is a BuildKit cache mount, so it speeds up
#            rebuilds but is never stored in an image layer.
#   runtime  copies only the finished virtualenv and the files the container
#            needs; no pip cache, no build metadata, no compilers.
#
# Both stages use the same pinned base so the virtualenv's interpreter symlink
# stays valid. The base image supports linux/amd64 and linux/arm64, and every
# dependency in pyproject.toml ships a wheel for both (no compiler is needed).

ARG PYTHON_IMAGE=python:3.13.1-slim-bookworm

# --------------------------------------------------------------------------
# Stage 1: builder
# --------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS builder

# PIP_NO_CACHE_DIR is deliberately NOT set here: the cache mount below is the
# cache, and it lives outside the image.
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /build
# --without-pip: the venv only needs the installed packages; pip itself runs
# from the base image's interpreter (pip --python), which keeps ~13 MB of pip
# out of the copied runtime venv.
RUN python -m venv --without-pip "$VIRTUAL_ENV"

# Only the files pip needs (pyproject's readme + the package source), so edits
# to alembic/, entrypoint.sh or data/mock do not invalidate this stage.
COPY apps/api/pyproject.toml apps/api/README.md ./
COPY apps/api/src ./src
RUN --mount=type=cache,target=/root/.cache/pip \
    pip --python "$VIRTUAL_ENV/bin/python" install .

# --------------------------------------------------------------------------
# Stage 2: runtime
# --------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --uid 10001 appuser \
    && mkdir /app \
    && chown appuser:appuser /app
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Application files are owned by the runtime user. The demo dataset ships with
# the image so the container works standalone (DEMO_MODE=true).
COPY --chown=appuser:appuser apps/api/alembic.ini ./
COPY --chown=appuser:appuser apps/api/alembic ./alembic
COPY --chown=appuser:appuser --chmod=0755 apps/api/entrypoint.sh ./
COPY --chown=appuser:appuser data/mock ./data/mock

USER appuser
EXPOSE 8000

# curl is not installed in slim images; use the stdlib for the healthcheck.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status==200 else 1)"

# entrypoint.sh: alembic upgrade head -> python -m costlab.seed -> exec "$@"
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "costlab.main:app", "--host", "0.0.0.0", "--port", "8000"]
