FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
COPY ml/ ./ml/
COPY services/scoring/ ./services/scoring/

RUN pip install --no-cache-dir -e ./ml -e ./services/scoring/

ENV PYTHONPATH="/app/ml/src:/app/services/scoring/src:."
EXPOSE 8002

CMD ["uvicorn", "scoring.main:app", "--host", "0.0.0.0", "--port", "8002"]
