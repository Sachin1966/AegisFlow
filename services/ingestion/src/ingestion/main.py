import os
import time
import logging
import uuid
import requests
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import sqlalchemy as sa

try:
    from ingestion.online_features import RedisOnlineFeatureStore
except ImportError:
    from online_features import RedisOnlineFeatureStore

logger = logging.getLogger("aegis_ingestion")
logging.basicConfig(level=logging.INFO)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AegisFlow Transaction Ingestion Microservice",
    description="Real-Time Payment Transaction Ingestion Engine with Redis Online Feature Store & Scoring Orchestration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SCORING_SERVICE_URL = os.getenv("SCORING_SERVICE_URL", "http://localhost:8002")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aegis_user:aegis_password_secure@localhost:5432/aegisflow_db")

# Initialize Redis feature store
redis_store = RedisOnlineFeatureStore()

# Database engine setup (lazy / fault-tolerant)
db_engine = None
try:
    db_engine = sa.create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 2})
except Exception as e:
    logger.warning(f"Failed to initialize database engine: {e}")

class TransactionIngestRequest(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: f"tx_{uuid.uuid4().hex[:12]}")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    source_account_id: str
    target_account_id: Optional[str] = None
    amount: float
    currency: str = "USD"
    channel: str = "mobile_app"
    device_id: Optional[str] = None
    ip_id: Optional[str] = None
    merchant_id: Optional[str] = None

class IngestionResponse(BaseModel):
    transaction_id: str
    decision: str
    probability: float
    rule_hits: list
    reason_codes: list
    degraded: bool
    latency_ms: float

def save_transaction_to_db(tx_dict: Dict[str, Any], decision_dict: Dict[str, Any]):
    """Background task to persist transaction & decision to PostgreSQL database if available."""
    if not db_engine:
        return
    try:
        with db_engine.begin() as conn:
            # Insert Transaction
            conn.execute(
                sa.text("""
                    INSERT INTO transactions (id, timestamp, source_account_id, target_account_id, amount, currency, channel, device_id, ip_id, merchant_id, status)
                    VALUES (:id, :timestamp, :source_account_id, :target_account_id, :amount, :currency, :channel, :device_id, :ip_id, :merchant_id, 'completed')
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": tx_dict["id"],
                    "timestamp": tx_dict["timestamp"],
                    "source_account_id": tx_dict["source_account_id"],
                    "target_account_id": tx_dict.get("target_account_id"),
                    "amount": tx_dict["amount"],
                    "currency": tx_dict.get("currency", "USD"),
                    "channel": tx_dict.get("channel", "mobile_app"),
                    "device_id": tx_dict.get("device_id"),
                    "ip_id": tx_dict.get("ip_id"),
                    "merchant_id": tx_dict.get("merchant_id"),
                }
            )

            # Insert Decision
            conn.execute(
                sa.text("""
                    INSERT INTO decisions (id, transaction_id, decision, probability, rule_hits, reason_codes, latency_ms, model_version, degraded)
                    VALUES (:id, :transaction_id, :decision, :probability, :rule_hits, :reason_codes, :latency_ms, :model_version, :degraded)
                    ON CONFLICT (transaction_id) DO NOTHING
                """),
                {
                    "id": f"dec_{uuid.uuid4().hex[:12]}",
                    "transaction_id": tx_dict["id"],
                    "decision": decision_dict.get("decision", "APPROVE"),
                    "probability": float(decision_dict.get("probability", 0.0)),
                    "rule_hits": sa.dialects.postgresql.json.dumps(decision_dict.get("rule_hits", [])) if hasattr(sa.dialects.postgresql, "json") else str(decision_dict.get("rule_hits", [])),
                    "reason_codes": sa.dialects.postgresql.json.dumps(decision_dict.get("reason_codes", [])) if hasattr(sa.dialects.postgresql, "json") else str(decision_dict.get("reason_codes", [])),
                    "latency_ms": float(decision_dict.get("latency_ms", 0.0)),
                    "model_version": decision_dict.get("model_version", "v1.0.0"),
                    "degraded": bool(decision_dict.get("degraded", False))
                }
            )

            # Create alert if decision is REVIEW or DECLINE
            dec_str = decision_dict.get("decision", "APPROVE")
            if dec_str in ("REVIEW", "DECLINE"):
                conn.execute(
                    sa.text("""
                        INSERT INTO alerts (id, alert_id, transaction_id, alert_type, severity)
                        VALUES (:id, :alert_id, :transaction_id, :alert_type, :severity)
                        ON CONFLICT (alert_id) DO NOTHING
                    """),
                    {
                        "id": f"alt_{uuid.uuid4().hex[:12]}",
                        "alert_id": f"ALT-{uuid.uuid4().hex[:8].upper()}",
                        "transaction_id": tx_dict["id"],
                        "alert_type": f"FRAUD_SCORE_{dec_str}",
                        "severity": "high" if dec_str == "DECLINE" else "medium"
                    }
                )
    except Exception as e:
        logger.warning(f"Could not persist transaction to PostgreSQL ({e}). Continuing.")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ingestion",
        "redis_connected": redis_store is not None,
        "version": "1.0.0"
    }

@app.post("/api/v1/transactions", response_model=IngestionResponse)
def ingest_transaction(req: TransactionIngestRequest, background_tasks: BackgroundTasks = None):
    start_time = time.time()
    tx_dict = req.model_dump()
    if tx_dict["timestamp"] is None:
        tx_dict["timestamp"] = datetime.utcnow()

    # 1. Update online sliding-window velocity features in Redis
    redis_store.update_online_features(tx_dict)

    # 2. Retrieve compiled feature vector for scoring
    features, degraded = redis_store.get_online_features(
        acct_id=tx_dict["source_account_id"],
        dev_id=tx_dict.get("device_id"),
        ip_id=tx_dict.get("ip_id"),
        merch_id=tx_dict.get("merchant_id")
    )

    # 3. Request Fraud Score from Scoring Microservice
    decision_data = None
    try:
        resp = requests.post(
            f"{SCORING_SERVICE_URL}/api/v1/score",
            json={
                "transaction": tx_dict,
                "features": features,
                "degraded": degraded
            },
            timeout=2.0
        )
        if resp.status_code == 200:
            decision_data = resp.json()
    except Exception as e:
        logger.warning(f"Scoring service call failed ({e}). Returning baseline decision.")

    if not decision_data:
        # Local fallback evaluation if scoring microservice is offline
        decision_data = {
            "decision": "DECLINE" if tx_dict["amount"] > 100000 else "APPROVE",
            "probability": 0.95 if tx_dict["amount"] > 100000 else 0.05,
            "rule_hits": ["HIGH_AMOUNT_FALLBACK"] if tx_dict["amount"] > 100000 else [],
            "reason_codes": [{"code": "AMOUNT_EXCEEDS_THRESHOLD", "importance": 0.9}] if tx_dict["amount"] > 100000 else [],
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "model_version": "fallback_v1",
            "degraded": True
        }

    total_latency_ms = round((time.time() - start_time) * 1000, 2)
    decision_data["latency_ms"] = total_latency_ms

    # Save asynchronously/background
    save_transaction_to_db(tx_dict, decision_data)

    return IngestionResponse(
        transaction_id=tx_dict["id"],
        decision=decision_data.get("decision", "APPROVE"),
        probability=float(decision_data.get("probability", 0.0)),
        rule_hits=decision_data.get("rule_hits", []),
        reason_codes=decision_data.get("reason_codes", []),
        degraded=bool(decision_data.get("degraded", False)),
        latency_ms=total_latency_ms
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ingestion.main:app", host="0.0.0.0", port=8001, reload=True)
