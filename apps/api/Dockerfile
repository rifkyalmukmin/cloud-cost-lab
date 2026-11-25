FROM python:3.11.9-slim AS base

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt alembic.ini ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic ./alembic
COPY app/ ./app/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
