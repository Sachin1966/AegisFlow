# ADR 0001: Single Source of Truth Feature Definitions

## Status
Accepted

## Context
In real-time fraud detection systems, training-serving skew is a primary cause of model performance decay. If offline model training features (calculated from historical parquet/SQL batches) differ in definition, aggregation windows, or default value handling from online feature store reads (calculated in real-time from Redis sliding windows), the online model predictions degrade severely.

## Decision
We establish a single source of truth for feature definitions located at `ml/features/definitions.py`. Every feature metric specifies:
- Feature name
- Entity context (`account`, `device`, `ip`, `merchant`)
- Time window (e.g. 1m, 1h, 24h, 7d)
- Aggregation type (`count`, `sum`, `avg`, `std`, `unique_count`)
- Fallback/default value

Both offline feature extraction tools and online Redis update/read handlers derive their calculations strictly from these definitions.

## Consequences
- Prevents training-serving skew completely.
- Unit parity tests verify that offline calculation outputs match online Redis retrieval outputs given identical event streams.
