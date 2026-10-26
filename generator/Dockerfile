FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY generator/ /app/generator/
COPY db/ /app/db/

RUN pip install --no-cache-dir -e /app/generator

ENTRYPOINT ["txgen"]
CMD ["stream", "--rate", "5"]
