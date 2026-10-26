# AegisFlow Operations Runbook

## Deployment & Execution

### 1. Local Environment Setup
```bash
cp .env.example .env
make install
```

### 2. Infrastructure Containers
```bash
docker-compose up -d postgres redis qdrant mlflow
```

### 3. Database Initialization
```bash
make db-migrate
make db-seed
```

### 4. Synthetic Data Generation
```bash
# Seed initial population of entities
python -m txgen.main seed-entities

# Generate batch synthetic dataset with injected fraud rings and typologies
python -m txgen.main generate-batch --count 10000 --fraud-ratio 0.05
```

### 5. Running Tests
```bash
make test
```

## Degraded Mode Operational Guidelines
If Redis becomes unavailable:
- The scoring service automatically triggers `degraded=true`.
- Default profile aggregate values are populated.
- Conservative rules are enforced (forcing manual REVIEW on high amount transactions).
- System remains fully operational without crashing.
