FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY ml/pyproject.toml ./ml/
COPY generator/pyproject.toml ./generator/

COPY ml ./ml
COPY services/ingestion ./services/ingestion

RUN pip install --no-cache-dir fastapi uvicorn redis psycopg2-binary sqlalchemy requests pydantic

ENV PYTHONPATH=/app/services/ingestion/src:/app/ml/src:/app

EXPOSE 8001

CMD ["uvicorn", "ingestion.main:app", "--host", "0.0.0.0", "--port", "8001"]
