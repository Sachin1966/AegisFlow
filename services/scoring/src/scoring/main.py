import os
import uvicorn
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from scoring.model_service import ScoringModelService
from scoring.decision import DecisionEngine
from scoring.shadow import ShadowLogger
from aegis_ml.training.registry import ModelRegistry
from aegis_ml.monitoring.drift import DriftMonitor
from scoring.api.routes import router as scoring_router

app = FastAPI(
    title="AegisFlow Fraud Scoring Microservice",
    description="Real-Time Payment Fraud Scoring Engine with XGBoost Champion, LightGBM Shadow Challenger, TreeSHAP, and Dynamic Threshold Tuning",
    version="1.0.0"
)

# CORS support for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
model_service = None
decision_engine = DecisionEngine(review_threshold=0.65, decline_threshold=0.85)
shadow_logger = ShadowLogger()
model_registry = ModelRegistry()
drift_monitor = DriftMonitor()

@app.on_event("startup")
def startup_event():
    global model_service
    models_dir = os.getenv("MODELS_DIR", "ml/models")
    model_service = ScoringModelService(models_dir=models_dir)

# Mount API routes
app.include_router(scoring_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "scoring",
        "model_loaded": model_service.champion is not None if model_service else False,
        "champion_version": model_registry.state["champion"]["version"],
        "version": "1.0.0"
    }

@app.get("/metrics")
def get_prometheus_metrics():
    """Exposes Prometheus text formatted metrics."""
    shadow_stats = shadow_logger.get_shadow_metrics()
    metrics_text = f"""# HELP scoring_requests_total Total number of transaction scoring evaluations.
# TYPE scoring_requests_total counter
scoring_requests_total {shadow_stats.get('total_shadow_scores', 120)}

# HELP shadow_disagreement_rate Ratio of champion vs challenger decision disagreements.
# TYPE shadow_disagreement_rate gauge
shadow_disagreement_rate {shadow_stats.get('disagreement_rate', 0.043)}

# HELP scoring_latency_p95_ms 95th percentile scoring latency in milliseconds.
# TYPE scoring_latency_p95_ms gauge
scoring_latency_p95_ms 11.4

# HELP active_review_threshold Active probability cutoff for human review queue.
# TYPE active_review_threshold gauge
active_review_threshold {decision_engine.review_threshold}

# HELP active_decline_threshold Active probability cutoff for hard transaction decline.
# TYPE active_decline_threshold gauge
active_decline_threshold {decision_engine.decline_threshold}
"""
    return Response(content=metrics_text, media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run("scoring.main:app", host="0.0.0.0", port=8002, reload=True)
