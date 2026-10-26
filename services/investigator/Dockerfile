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
COPY services/investigator ./services/investigator

RUN pip install --no-cache-dir fastapi uvicorn psycopg2-binary sqlalchemy requests pydantic qdrant-client sentence-transformers networkx langgraph langchain langchain-community langchain-openai

ENV PYTHONPATH=/app/services/investigator/src:/app/ml/src:/app

EXPOSE 8004

CMD ["uvicorn", "investigator.main:app", "--host", "0.0.0.0", "--port", "8004"]
