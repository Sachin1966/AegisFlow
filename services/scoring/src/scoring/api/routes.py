from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional

from scoring.schemas import ScoreRequest, DecisionResponse, ThresholdConfig, ThresholdUpdateRequest
from scoring.model_service import ScoringModelService
from scoring.decision import DecisionEngine
from scoring.shadow import ShadowLogger
from aegis_ml.training.registry import ModelRegistry
from aegis_ml.monitoring.drift import DriftMonitor

router = APIRouter(prefix="/api/v1", tags=["Scoring & ModelOps"])

# These instances are injected or managed by the app
import os

def get_model_service():
    import scoring.main as sm
    if sm.model_service is None:
        models_dir = os.getenv("MODELS_DIR", "ml/models")
        sm.model_service = ScoringModelService(models_dir=models_dir)
    return sm.model_service

def get_decision_engine():
    from scoring.main import decision_engine
    return decision_engine

def get_shadow_logger():
    from scoring.main import shadow_logger
    return shadow_logger

def get_model_registry():
    from scoring.main import model_registry
    return model_registry

def get_drift_monitor():
    from scoring.main import drift_monitor
    return drift_monitor

@router.post("/score", response_model=DecisionResponse)
def score_transaction(
    req: ScoreRequest,
    model_svc: ScoringModelService = Depends(get_model_service),
    dec_engine: DecisionEngine = Depends(get_decision_engine),
    shadow_log: ShadowLogger = Depends(get_shadow_logger)
):
    result = model_svc.score_transaction(
        tx=req.transaction,
        features=req.features,
        degraded=req.degraded or False
    )

    # Re-evaluate decision using active dynamic thresholds from decision_engine
    rule_override = "DECLINE" if any("SANCTIONS" in r or "IMPOSSIBLE_TRAVEL" in r for r in result["rule_hits"]) else None
    dynamic_decision, final_prob = dec_engine.evaluate_decision(
        calibrated_prob=result["probability"],
        rule_override=rule_override
    )
    result["decision"] = dynamic_decision
    result["probability"] = final_prob

    # Track shadow prediction
    shadow_log.record_shadow_score(
        tx_id=req.transaction.get("id", "tx_unknown"),
        champion_prob=result["probability"],
        champion_decision=result["decision"],
        challenger_prob=result.get("challenger_probability")
    )

    return result

@router.get("/thresholds")
def get_thresholds(dec_engine: DecisionEngine = Depends(get_decision_engine)):
    return dec_engine.get_thresholds()

@router.put("/thresholds")
def update_thresholds(req: ThresholdUpdateRequest, dec_engine: DecisionEngine = Depends(get_decision_engine)):
    try:
        return dec_engine.update_thresholds(
            review_t=req.review_threshold,
            decline_t=req.decline_threshold,
            updated_by=req.updated_by or "risk_manager",
            reason=req.reason or "Threshold update"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/thresholds/rollback")
def rollback_thresholds(actor: str = "risk_manager", dec_engine: DecisionEngine = Depends(get_decision_engine)):
    try:
        return dec_engine.rollback_thresholds(actor=actor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/models")
def get_models(
    registry: ModelRegistry = Depends(get_model_registry),
    shadow_log: ShadowLogger = Depends(get_shadow_logger)
):
    status = registry.get_status()
    shadow_metrics = shadow_log.get_shadow_metrics()
    status["shadow_metrics"] = shadow_metrics
    return status

@router.post("/models/promote")
def promote_challenger(
    payload: Dict[str, Any] = None,
    registry: ModelRegistry = Depends(get_model_registry)
):
    payload = payload or {}
    actor = payload.get("actor", "risk_lead")
    rationale = payload.get("rationale", "Challenger beat baseline on recall@1%FPR with reduced latency")
    return registry.promote_challenger(actor=actor, rationale=rationale)

@router.post("/models/rollback")
def rollback_model(
    payload: Dict[str, Any] = None,
    registry: ModelRegistry = Depends(get_model_registry)
):
    payload = payload or {}
    actor = payload.get("actor", "risk_lead")
    rationale = payload.get("rationale", "Emergency rollback to previous stable champion")
    return registry.rollback(actor=actor, rationale=rationale)

@router.get("/drift")
def get_drift_report(drift_mon: DriftMonitor = Depends(get_drift_monitor)):
    return drift_mon.compute_feature_drift(current_df=None)
