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
COPY services/casework ./services/casework

RUN pip install --no-cache-dir fastapi uvicorn psycopg2-binary sqlalchemy requests pydantic PyJWT passlib[bcrypt]

ENV PYTHONPATH=/app/services/casework/src:/app/ml/src:/app

EXPOSE 8003

CMD ["uvicorn", "casework.main:app", "--host", "0.0.0.0", "--port", "8003"]
