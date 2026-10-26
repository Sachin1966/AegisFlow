import os
import sys
import time
import uuid
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "services/ingestion/src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "services/scoring/src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "services/casework/src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "services/investigator/src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "ml/src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "generator/src")))

from scoring.main import app as scoring_app, model_service, decision_engine, shadow_logger, model_registry, drift_monitor
from casework.main import app as casework_app, IN_MEMORY_ALERTS, IN_MEMORY_CASES, IN_MEMORY_SAR_DRAFTS, audit_writer, feedback_loop
from investigator.main import app as investigator_app, run_agentic_workflow, mcp_server, run_evaluation_suite
from ingestion.online_features import RedisOnlineFeatureStore

logger = logging.getLogger("aegisflow_unified")
logging.basicConfig(level=logging.INFO)

# Unified Gateway FastAPI Application
app = FastAPI(
    title="AegisFlow | Real-Time Payment Fraud Scoring & Agentic AML Investigation Platform",
    description="Unified API Gateway uniting sub-100ms ML fraud scoring with 6-agent LangGraph AML investigation workbench.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory streaming feed cache for live decisions UI
LIVE_DECISIONS_STREAM = []
STREAMING_ACTIVE = True
redis_feature_store = RedisOnlineFeatureStore()

# Include sub-app routes
app.mount("/sub/scoring", scoring_app)
app.mount("/sub/casework", casework_app)
app.mount("/sub/investigator", investigator_app)

# --- Gateway Endpoints ---
@app.get("/health")
def unified_health():
    return {
        "status": "healthy",
        "platform": "AegisFlow Unified Production Server",
        "services": {
            "ingestion": "ready",
            "scoring": "ready (Champion: " + model_registry.state["champion"]["version"] + ")",
            "casework": "ready",
            "investigator": "ready (LangGraph 6-Agent + MCP)",
        },
        "streaming_active": STREAMING_ACTIVE,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Forward /api/v1/transactions
@app.post("/api/v1/transactions")
async def ingest_transaction_gateway(request: Request):
    tx_dict = await request.json()
    start_time = time.time()
    if "id" not in tx_dict or not tx_dict["id"]:
        tx_dict["id"] = f"tx_{uuid.uuid4().hex[:10]}"
    if "timestamp" not in tx_dict or not tx_dict["timestamp"]:
        tx_dict["timestamp"] = datetime.now(timezone.utc).isoformat()

    # 1. Update online feature store
    redis_feature_store.update_online_features(tx_dict)
    features, degraded = redis_feature_store.get_online_features(
        acct_id=tx_dict.get("source_account_id", "ACCT-DEFAULT"),
        dev_id=tx_dict.get("device_id"),
        ip_id=tx_dict.get("ip_id"),
        merch_id=tx_dict.get("merchant_id")
    )

    # 2. Score via Model Service
    score_res = model_service.score_transaction(tx=tx_dict, features=features, degraded=degraded)
    
    # 3. Dynamic Thresholds
    rule_override = "DECLINE" if any("SANCTIONS" in r or "IMPOSSIBLE_TRAVEL" in r for r in score_res.get("rule_hits", [])) else None
    decision, prob = decision_engine.evaluate_decision(score_res["probability"], rule_override=rule_override)
    score_res["decision"] = decision
    score_res["probability"] = prob

    total_latency = round((time.time() - start_time) * 1000, 2)
    score_res["latency_ms"] = total_latency

    # 4. Record in live stream
    stream_entry = {
        "transaction_id": tx_dict["id"],
        "timestamp": tx_dict["timestamp"],
        "source_account": tx_dict.get("source_account_id"),
        "target_account": tx_dict.get("target_account_id"),
        "amount": tx_dict.get("amount", 0.0),
        "currency": tx_dict.get("currency", "USD"),
        "channel": tx_dict.get("channel", "mobile_app"),
        "decision": decision,
        "probability": prob,
        "reason_codes": score_res.get("reason_codes", []),
        "rule_hits": score_res.get("rule_hits", []),
        "latency_ms": total_latency,
        "degraded": degraded
    }
    LIVE_DECISIONS_STREAM.insert(0, stream_entry)
    if len(LIVE_DECISIONS_STREAM) > 100:
        LIVE_DECISIONS_STREAM.pop()

    # 5. Create alert if REVIEW or DECLINE
    if decision in ("REVIEW", "DECLINE"):
        new_alert = {
            "id": f"alt_{uuid.uuid4().hex[:8]}",
            "alert_id": f"ALT-{uuid.uuid4().hex[:6].upper()}",
            "transaction_id": tx_dict["id"],
            "alert_type": f"FRAUD_MODEL_{decision}",
            "severity": "critical" if decision == "DECLINE" else "high",
            "case_id": "CASE-2026-001" if tx_dict.get("source_account_id") == "ACCT-7842" else None,
            "source_account": tx_dict.get("source_account_id"),
            "target_account": tx_dict.get("target_account_id"),
            "device_id": tx_dict.get("device_id"),
            "amount": tx_dict.get("amount", 0.0),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        IN_MEMORY_ALERTS.insert(0, new_alert)

    return score_res

@app.get("/api/v1/transactions/live")
def get_live_transactions():
    return {"transactions": LIVE_DECISIONS_STREAM[:50], "total": len(LIVE_DECISIONS_STREAM)}

# Forward Scoring endpoints
@app.post("/api/v1/score")
async def score_gateway(request: Request):
    data = await request.json()
    from scoring.api.routes import score_transaction
    from scoring.schemas import ScoreRequest
    req = ScoreRequest(**data)
    return score_transaction(req, model_service, decision_engine, shadow_logger)

@app.get("/api/v1/thresholds")
def get_thresholds_gateway():
    return decision_engine.get_thresholds()

@app.put("/api/v1/thresholds")
async def update_thresholds_gateway(request: Request):
    data = await request.json()
    from scoring.schemas import ThresholdUpdateRequest
    req = ThresholdUpdateRequest(**data)
    return decision_engine.update_thresholds(
        review_t=req.review_threshold,
        decline_t=req.decline_threshold,
        updated_by=req.updated_by or "risk_manager",
        reason=req.reason or "Threshold update"
    )

@app.post("/api/v1/thresholds/rollback")
def rollback_thresholds_gateway(actor: str = "risk_manager"):
    return decision_engine.rollback_thresholds(actor=actor)

@app.get("/api/v1/models")
def get_models_gateway():
    status = model_registry.get_status()
    status["shadow_metrics"] = shadow_logger.get_shadow_metrics()
    return status

@app.post("/api/v1/models/promote")
async def promote_model_gateway(request: Request):
    data = await request.json() if request.headers.get("content-length") else {}
    actor = data.get("actor", "risk_lead")
    rationale = data.get("rationale", "Promoted candidate challenger based on lift")
    return model_registry.promote_challenger(actor=actor, rationale=rationale)

@app.post("/api/v1/models/rollback")
async def rollback_model_gateway(request: Request):
    data = await request.json() if request.headers.get("content-length") else {}
    actor = data.get("actor", "risk_lead")
    rationale = data.get("rationale", "Emergency rollback to prior champion")
    return model_registry.rollback(actor=actor, rationale=rationale)

@app.get("/api/v1/drift")
def get_drift_gateway():
    return drift_monitor.compute_feature_drift(current_df=None)

# Forward Casework endpoints
@app.post("/api/v1/auth/login")
async def login_gateway(request: Request):
    from casework.main import login, LoginRequest
    data = await request.json()
    return login(LoginRequest(**data))

@app.get("/api/v1/stats/summary")
def get_stats_gateway():
    from casework.main import get_summary_stats
    return get_summary_stats()

@app.get("/api/v1/alerts")
def get_alerts_gateway(severity: Optional[str] = None):
    from casework.main import list_alerts
    return list_alerts(severity=severity)

@app.post("/api/v1/alerts/promote")
async def promote_alert_gateway(request: Request):
    from casework.main import promote_alert
    data = await request.json()
    return promote_alert(data)

@app.get("/api/v1/cases")
def get_cases_gateway(status: Optional[str] = None, assigned: Optional[str] = None, sort: Optional[str] = "sla"):
    from casework.main import list_cases
    return list_cases(status=status, assigned=assigned, sort=sort)

@app.get("/api/v1/cases/{case_id}")
def get_case_gateway(case_id: str):
    from casework.main import get_case_detail
    return get_case_detail(case_id)

@app.patch("/api/v1/cases/{case_id}/status")
async def update_case_status_gateway(case_id: str, request: Request):
    from casework.main import update_case_status
    data = await request.json()
    return update_case_status(case_id, data)

@app.get("/api/v1/cases/{case_id}/graph")
def get_case_graph_gateway(case_id: str, hops: int = 2):
    from casework.main import get_case_entity_graph
    return get_case_entity_graph(case_id, hops=hops)

@app.post("/api/v1/cases/{case_id}/disposition")
async def record_case_disposition_gateway(case_id: str, request: Request):
    from casework.main import record_case_disposition, CaseDispositionRequest
    data = await request.json()
    return record_case_disposition(case_id, CaseDispositionRequest(**data))

@app.post("/api/v1/cases/{case_id}/signoff")
async def signoff_case_gateway(case_id: str, request: Request):
    from casework.main import signoff_case
    data = await request.json()
    return signoff_case(case_id, data)

@app.get("/api/v1/sar/{case_id}/draft")
def get_sar_draft_gateway(case_id: str):
    from casework.main import get_sar_draft
    return get_sar_draft(case_id)

@app.put("/api/v1/sar/{case_id}/draft")
async def update_sar_draft_gateway(case_id: str, request: Request):
    from casework.main import update_sar_draft, SARDraftUpdateRequest
    data = await request.json()
    return update_sar_draft(case_id, SARDraftUpdateRequest(**data))

@app.post("/api/v1/sar/{case_id}/approve")
async def approve_sar_gateway(case_id: str, request: Request):
    from casework.main import approve_sar_draft, SARApprovalRequest
    data = await request.json()
    return approve_sar_draft(case_id, SARApprovalRequest(**data))

@app.get("/api/v1/sar/{case_id}/export/fincen")
def export_fincen_gateway(case_id: str, format: str = "json"):
    from casework.main import export_sar_fincen
    return export_sar_fincen(case_id, format=format)

@app.get("/api/v1/audit-logs")
def get_audit_logs_gateway():
    from casework.main import get_audit_logs
    return get_audit_logs()

# Forward Investigator & MCP endpoints
@app.post("/api/v1/investigate")
async def run_investigate_gateway(request: Request):
    data = await request.json()
    return run_agentic_workflow(data.get("case_id", "CASE-2026-001"), data.get("target_account_id", "ACCT-7842"))

@app.post("/api/v1/cases/{case_id}/investigate")
async def run_case_investigate_gateway(case_id: str, request: Request):
    data = await request.json() if request.headers.get("content-length") else {}
    return run_agentic_workflow(case_id, data.get("target_account_id", "ACCT-7842"))

@app.get("/api/v1/investigate/{case_id}")
def get_investigation_gateway(case_id: str):
    from investigator.main import get_investigation_result
    return get_investigation_result(case_id)

@app.get("/mcp/tools")
def get_mcp_tools_gateway():
    return {"tools": mcp_server.list_tools()}

@app.post("/mcp/call")
async def call_mcp_gateway(request: Request):
    data = await request.json()
    res = mcp_server.call_tool(data.get("tool_name"), data.get("arguments", {}))
    return {"tool_name": data.get("tool_name"), "result": res}

@app.post("/api/v1/evaluate")
def run_eval_gateway():
    return run_evaluation_suite()

# GenAI Report Studio Gateway Endpoints
@app.get("/api/v1/reports/models")
def get_report_models_gateway():
    from investigator.main import get_report_models
    return get_report_models()

@app.post("/api/v1/reports/generate")
async def generate_ai_report_gateway(request: Request):
    from investigator.main import generate_ai_report
    from investigator.report_generator import ReportGenerationRequest
    data = await request.json()
    return generate_ai_report(ReportGenerationRequest(**data))

@app.post("/api/v1/reports/refine")
async def refine_ai_report_gateway(request: Request):
    from investigator.main import refine_ai_report
    from investigator.report_generator import ReportRefinementRequest
    data = await request.json()
    return refine_ai_report(ReportRefinementRequest(**data))

@app.post("/api/v1/reports/verify")
async def verify_ai_report_gateway(request: Request):
    from investigator.main import verify_ai_report
    from investigator.report_generator import ReportVerificationRequest
    data = await request.json()
    return verify_ai_report(ReportVerificationRequest(**data))

@app.get("/api/v1/reports/{case_id}")
def get_saved_reports_gateway(case_id: str):
    from investigator.main import get_saved_reports
    return get_saved_reports(case_id)

@app.post("/api/v1/reports/{case_id}/save")
async def save_case_report_gateway(case_id: str, request: Request):
    from investigator.main import save_case_report
    data = await request.json()
    return save_case_report(case_id, data)

# Background Synthetic Transaction Streamer
def synthetic_streamer_daemon():
    import random
    time.sleep(2)
    accounts = [f"ACCT-{i}" for i in range(1000, 1050)]
    devices = [f"DEV-{i}" for i in range(100, 120)]
    merchants = [f"MERCH-{i}" for i in range(500, 520)]

    while True:
        try:
            is_risk = random.random() < 0.12 # 12% probability of generating suspicious or structuring pattern
            if is_risk:
                tx_id = f"tx_ring_{uuid.uuid4().hex[:8]}"
                amount = round(random.uniform(9100.0, 9950.0), 2)
                src = "ACCT-7842" if random.random() < 0.6 else random.choice(accounts)
                dev = "DEV-9812"
            else:
                tx_id = f"tx_norm_{uuid.uuid4().hex[:8]}"
                amount = round(random.uniform(12.0, 380.0), 2)
                src = random.choice(accounts)
                dev = random.choice(devices)

            tx_payload = {
                "id": tx_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_account_id": src,
                "target_account_id": random.choice(accounts),
                "amount": amount,
                "currency": "USD",
                "channel": random.choice(["mobile_app", "web_portal", "pos"]),
                "device_id": dev,
                "ip_id": f"IP-192.168.1.{random.randint(10, 99)}",
                "merchant_id": random.choice(merchants)
            }

            # Update features & score
            redis_feature_store.update_online_features(tx_payload)
            feats, degraded = redis_feature_store.get_online_features(
                acct_id=src,
                dev_id=dev,
                ip_id=tx_payload["ip_id"],
                merch_id=tx_payload["merchant_id"]
            )
            score_res = model_service.score_transaction(tx=tx_payload, features=feats, degraded=degraded)
            decision, prob = decision_engine.evaluate_decision(score_res["probability"])

            entry = {
                "transaction_id": tx_id,
                "timestamp": tx_payload["timestamp"],
                "source_account": src,
                "target_account": tx_payload["target_account_id"],
                "amount": amount,
                "currency": "USD",
                "channel": tx_payload["channel"],
                "decision": decision,
                "probability": prob,
                "reason_codes": score_res.get("reason_codes", []),
                "rule_hits": score_res.get("rule_hits", []),
                "latency_ms": score_res.get("latency_ms", 12.0),
                "degraded": degraded
            }
            LIVE_DECISIONS_STREAM.insert(0, entry)
            if len(LIVE_DECISIONS_STREAM) > 100:
                LIVE_DECISIONS_STREAM.pop()

            # Record shadow prediction
            shadow_logger.record_shadow_score(
                tx_id=tx_id,
                champion_prob=prob,
                champion_decision=decision,
                challenger_prob=score_res.get("challenger_probability")
            )

            # Rest between transactions
            time.sleep(random.uniform(1.2, 2.5))
        except Exception as e:
            logger.warning(f"Streamer cycle error: {e}")
            time.sleep(3)

# Serve Frontend static files
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.on_event("startup")
def startup_unified():
    global model_service
    models_dir = os.getenv("MODELS_DIR", "ml/models")
    from scoring.model_service import ScoringModelService
    import scoring.main as sm
    model_service = ScoringModelService(models_dir=models_dir)
    sm.model_service = model_service
    
    # Start background synthetic stream thread
    streamer_thread = threading.Thread(target=synthetic_streamer_daemon, daemon=True)
    streamer_thread.start()
    logger.info("AegisFlow Unified Production Server initialized with live background synthetic streaming.")

if __name__ == "__main__":
    uvicorn.run("run_server:app", host="0.0.0.0", port=8000, reload=False)
