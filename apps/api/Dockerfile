# Cloud Cost Lab API — small, pinned, non-root (CLAUDE.md §50).
# Build from the REPOSITORY ROOT (docker context includes data/mock):
#   docker build -f apps/api/Dockerfile -t cloud-cost-lab-api .
FROM python:3.13.1-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first so source changes do not bust the dependency layer.
COPY apps/api/pyproject.toml apps/api/README.md ./
COPY apps/api/src ./src
RUN pip install --no-cache-dir .

COPY apps/api/alembic.ini ./
COPY apps/api/alembic ./alembic
COPY apps/api/entrypoint.sh ./
# The demo dataset ships with the image so the container works standalone.
COPY data/mock ./data/mock
RUN chmod +x entrypoint.sh \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

# curl is not installed in slim images; use the stdlib for the healthcheck.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status==200 else 1)"

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "costlab.main:app", "--host", "0.0.0.0", "--port", "8000"]
