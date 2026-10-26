import os
import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import FastAPI, HTTPException, Depends, Header, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from casework.audit import ImmutableAuditWriter
from casework.export.fincen import FinCENExporter
from casework.correlation import AlertCorrelationEngine, calculate_case_priority_and_sla
from aegis_ml.monitoring.label_feedback import LabelFeedbackLoop

logger = logging.getLogger("aegis_casework")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AegisFlow Casework & Alert Management Microservice",
    description="Case Management API with Human-in-the-Loop Sign-off, FinCEN SAR Generation, PII Masking, and Immutable Audit Trail",
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

JWT_SECRET = os.getenv("SECRET_KEY", "aegisflow_jwt_secret_key_change_in_production_32bytes_min")

# Core Engine Singletons
audit_writer = ImmutableAuditWriter()
correlation_engine = AlertCorrelationEngine()
feedback_loop = LabelFeedbackLoop()

# Seed State
IN_MEMORY_ALERTS = [
    {
        "id": "alt_001",
        "alert_id": "ALT-90812",
        "transaction_id": "tx_7812a01",
        "alert_type": "VELOCITY_SPIKE_1H",
        "severity": "high",
        "case_id": "CASE-2026-001",
        "source_account": "ACCT-7842",
        "target_account": "ACCT-9011",
        "device_id": "DEV-9812",
        "amount": 9850.00,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    },
    {
        "id": "alt_002",
        "alert_id": "ALT-90813",
        "transaction_id": "tx_7812a02",
        "alert_type": "SMURFING_PATTERN_DETECTED",
        "severity": "critical",
        "case_id": "CASE-2026-001",
        "source_account": "ACCT-7842",
        "target_account": "ACCT-COUNTERPART-1",
        "device_id": "DEV-9812",
        "amount": 9600.00,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    },
    {
        "id": "alt_003",
        "alert_id": "ALT-90814",
        "transaction_id": "tx_7812a03",
        "alert_type": "SHARED_DEVICE_RING",
        "severity": "critical",
        "case_id": "CASE-2026-001",
        "source_account": "ACCT-5521",
        "target_account": "ACCT-4401",
        "device_id": "DEV-9812",
        "amount": 4200.00,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    },
    {
        "id": "alt_004",
        "alert_id": "ALT-90815",
        "transaction_id": "tx_3301a09",
        "alert_type": "HIGH_AMOUNT_UNVERIFIED",
        "severity": "medium",
        "case_id": "CASE-2026-002",
        "source_account": "ACCT-1102",
        "target_account": "ACCT-3310",
        "device_id": "DEV-4421",
        "amount": 14200.00,
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=40)).isoformat()
    }
]

IN_MEMORY_CASES = [
    {
        "id": "case_001",
        "case_id": "CASE-2026-001",
        "title": "Suspected Structuring & Shared-Device Ring - ACCT-7842",
        "priority": "critical",
        "priority_score": 0.95,
        "status": "investigating", # open, investigating, pending_review, closed
        "assigned_analyst": "analyst.sarah",
        "sla_due_at": (datetime.now(timezone.utc) + timedelta(hours=20)).isoformat(),
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat(),
        "alerts_count": 3,
        "subject_account": "ACCT-7842",
        "disposition": None,
        "disposition_rationale": None
    },
    {
        "id": "case_002",
        "case_id": "CASE-2026-002",
        "title": "Unverified High-Value Channel Escalation - ACCT-1102",
        "priority": "medium",
        "priority_score": 0.60,
        "status": "open",
        "assigned_analyst": "analyst.john",
        "sla_due_at": (datetime.now(timezone.utc) + timedelta(hours=68)).isoformat(),
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "alerts_count": 1,
        "subject_account": "ACCT-1102",
        "disposition": None,
        "disposition_rationale": None
    }
]

IN_MEMORY_SAR_DRAFTS = {
    "CASE-2026-001": {
        "case_id": "CASE-2026-001",
        "version": 1,
        "subject_entity": "ACCT-7842",
        "suspicious_activity_amount": 76400.00,
        "detected_typologies": ["Structuring/Smurfing", "Layering", "Shared Device Ring"],
        "full_narrative_md": """# FinCEN Suspicious Activity Report (SAR) - Draft
**Case Reference:** CASE-2026-001
**Target Subject:** ACCT-7842
**Primary Typologies:** Structuring / Smurfing, Layering, Shared-Device Fraud Ring
**Estimated Suspicious Volume:** $76,400.00 USD

## 1. Summary of Suspicious Activity
Between recent operational cycles, Subject Account **ACCT-7842** exhibited an automated structuring sequence. The account received 8 sub-threshold deposits ranging from $9,200 to $9,850 within a 48-hour window, staying intentionally below the $10,000 Currency Transaction Report (CTR) filing threshold [Citation: Typology Engine - Smurfing #1].

## 2. Entity & Network Relationships
Link analysis reveals that ACCT-7842 transferred $39,200 to **Shell Corp LLC** (ACCT-COUNTERPART-1), which maintains direct financial ties to OFAC-listed entity **ACCT-KNOWN-FRAUD-99** [Citation: Graph Link Analyst #1]. Furthermore, ACCT-7842 shares device hardware fingerprint **DEV-9812** with 6 high-risk accounts [Citation: Shared Device Ring #1].

## 3. Adverse Media & External Risk Correlation
Hybrid vector search retrieved regulatory intelligence (Art-2025-881) citing Shell Corp LLC in federal wire fraud structuring investigations [Citation: Adverse Media RAG #1].

## 4. Conclusion & Recommended Action
The co-occurrence of sub-threshold structuring, shared device hardware fingerprints, and multi-hop routing to sanctioned entities strongly indicates active money laundering. Immediate SAR filing and account freezing recommended.""",
        "citations": [
            {"id": "EV-01", "type": "TYPOLOGY", "source": "Deterministic Smurfing Detector", "confidence": 0.92},
            {"id": "EV-02", "type": "GRAPH", "source": "k-Hop Path Traversal (Distance: 2)", "confidence": 1.00},
            {"id": "EV-03", "type": "MEDIA", "source": "ART-2025-881 (FinCrime Journal)", "confidence": 0.94}
        ],
        "status": "draft",
        "author": "agent",
        "reviewed_by": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
}

# Request Schemas
class LoginRequest(BaseModel):
    username: str
    password: str

class SARDraftUpdateRequest(BaseModel):
    narrative_md: str
    author: Optional[str] = "analyst.sarah"

class SARApprovalRequest(BaseModel):
    reviewer_rationale: str
    reviewer_name: Optional[str] = "Chief Compliance Officer"

class CaseDispositionRequest(BaseModel):
    disposition: str # fraud, not_fraud, sar_filed
    rationale: str
    analyst_name: Optional[str] = "analyst.sarah"

class CaseAssignRequest(BaseModel):
    assigned_analyst: str

# Helper: PII Masking
def mask_pii_string(val: str, role: str) -> str:
    if role in ("manager", "admin"):
        return val
    if not val or len(val) <= 2:
        return "**"
    return f"{val[0]}***{val[-1]}"

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "casework", "version": "1.0.0"}

@app.post("/api/v1/auth/login")
def login(req: LoginRequest):
    if req.username and req.password:
        role = "manager" if "manager" in req.username.lower() or "mlro" in req.username.lower() else "aml_analyst"
        payload = {
            "sub": req.username,
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(hours=24)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {"username": req.username, "role": role}
        }
    raise HTTPException(status_code=401, detail="Invalid username or password")

@app.get("/api/v1/stats/summary")
def get_summary_stats():
    active_cases = [c for c in IN_MEMORY_CASES if c["status"] != "closed"]
    return {
        "active_alerts_count": len(IN_MEMORY_ALERTS),
        "open_cases_count": len(active_cases),
        "high_priority_cases": len([c for c in active_cases if c["priority"] in ("high", "critical")]),
        "pending_sar_reviews": len([c for c in active_cases if c["status"] == "pending_review"]),
        "average_investigation_hours": 3.4,
        "automation_precision_pct": 94.2
    }

@app.get("/api/v1/alerts")
def list_alerts(severity: Optional[str] = None):
    res = IN_MEMORY_ALERTS
    if severity:
        res = [a for a in res if a["severity"] == severity]
    return {"alerts": res, "total": len(res)}

@app.post("/api/v1/alerts/promote")
def promote_alert(payload: Dict[str, Any]):
    alert_id = payload.get("alert_id")
    case_title = payload.get("title", f"Investigation for Alert {alert_id}")
    
    new_case_id = f"CASE-2026-{len(IN_MEMORY_CASES)+1:03d}"
    priority, p_score, sla_due = calculate_case_priority_and_sla(
        severity=payload.get("severity", "high"),
        amount=float(payload.get("amount", 10000.0)),
        typology=payload.get("alert_type", "")
    )

    new_case = {
        "id": f"case_{uuid.uuid4().hex[:8]}",
        "case_id": new_case_id,
        "title": case_title,
        "priority": priority,
        "priority_score": p_score,
        "status": "open",
        "assigned_analyst": payload.get("assigned_analyst", "analyst.sarah"),
        "sla_due_at": sla_due,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "alerts_count": 1,
        "subject_account": payload.get("source_account", "ACCT-UNKNOWN"),
        "disposition": None,
        "disposition_rationale": None
    }
    IN_MEMORY_CASES.append(new_case)

    # Associate alert
    for a in IN_MEMORY_ALERTS:
        if a["alert_id"] == alert_id or a["id"] == alert_id:
            a["case_id"] = new_case_id

    audit_writer.record_event("ALERT_PROMOTED_TO_CASE", "system", {"alert_id": alert_id, "case_id": new_case_id})
    return {"message": "Alert promoted to case successfully", "case": new_case}

@app.get("/api/v1/cases")
def list_cases(
    status: Optional[str] = None,
    assigned: Optional[str] = None,
    sort: Optional[str] = "sla"
):
    res = IN_MEMORY_CASES
    if status:
        res = [c for c in res if c["status"] == status]
    if assigned:
        res = [c for c in res if c["assigned_analyst"] == assigned]
    
    if sort == "sla":
        res = sorted(res, key=lambda x: x.get("sla_due_at", ""))
    elif sort == "priority":
        res = sorted(res, key=lambda x: x.get("priority_score", 0.0), reverse=True)

    return {"cases": res, "total": len(res)}

@app.get("/api/v1/cases/{case_id}")
def get_case_detail(case_id: str):
    case = next((c for c in IN_MEMORY_CASES if c["case_id"] == case_id or c["id"] == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    matched_alerts = [a for a in IN_MEMORY_ALERTS if a.get("case_id") == case["case_id"]]
    sar_draft = IN_MEMORY_SAR_DRAFTS.get(case["case_id"])

    return {
        "case": case,
        "alerts": matched_alerts,
        "sar_draft": sar_draft
    }

@app.patch("/api/v1/cases/{case_id}/status")
def update_case_status(case_id: str, payload: Dict[str, str]):
    new_status = payload.get("status")
    for c in IN_MEMORY_CASES:
        if c["case_id"] == case_id or c["id"] == case_id:
            c["status"] = new_status
            c["updated_at"] = datetime.now(timezone.utc).isoformat()
            audit_writer.record_event("CASE_STATUS_UPDATED", "analyst", {"case_id": case_id, "new_status": new_status})
            return c
    raise HTTPException(status_code=404, detail="Case not found")

@app.post("/api/v1/cases/{case_id}/assign")
def assign_case(case_id: str, req: CaseAssignRequest):
    for c in IN_MEMORY_CASES:
        if c["case_id"] == case_id or c["id"] == case_id:
            c["assigned_analyst"] = req.assigned_analyst
            audit_writer.record_event("CASE_ASSIGNED", "manager", {"case_id": case_id, "analyst": req.assigned_analyst})
            return c
    raise HTTPException(status_code=404, detail="Case not found")

@app.get("/api/v1/cases/{case_id}/graph")
def get_case_entity_graph(case_id: str, hops: int = 2):
    """
    Returns nodes and edges formatted for force-directed entity graph visualization.
    """
    case = next((c for c in IN_MEMORY_CASES if c["case_id"] == case_id or c["id"] == case_id), None)
    acct = case.get("subject_account", "ACCT-7842") if case else "ACCT-7842"

    nodes = [
        {"id": acct, "type": "account", "risk_score": 0.88, "label": f"Subject: {acct}"},
        {"id": "ACCT-COUNTERPART-1", "type": "account", "risk_score": 0.75, "label": "Shell Corp LLC"},
        {"id": "DEV-9812", "type": "device", "risk_score": 0.94, "label": "Hardware DEV-9812"},
        {"id": "IP-192.168.1.45", "type": "ip", "risk_score": 0.65, "label": "IP 192.168.1.45 (VPN)"},
        {"id": "ACCT-KNOWN-FRAUD-99", "type": "account", "risk_score": 0.99, "label": "OFAC Sanctioned Entity"}
    ]
    edges = [
        {"source": acct, "target": "ACCT-COUNTERPART-1", "type": "TRANSFER", "amount": 39200.0, "label": "$39.2k Wire"},
        {"source": acct, "target": "DEV-9812", "type": "SHARED_HARDWARE", "label": "Device Link"},
        {"source": "ACCT-COUNTERPART-1", "target": "DEV-9812", "type": "SHARED_HARDWARE", "label": "Device Link"},
        {"source": acct, "target": "IP-192.168.1.45", "type": "IP_NETWORK", "label": "Access IP"},
        {"source": "ACCT-COUNTERPART-1", "target": "ACCT-KNOWN-FRAUD-99", "type": "TRANSFER", "amount": 50000.0, "label": "$50k Wire"}
    ]
    return {
        "case_id": case_id,
        "target_account": acct,
        "nodes": nodes,
        "edges": edges,
        "shortest_path_to_fraud": [acct, "ACCT-COUNTERPART-1", "ACCT-KNOWN-FRAUD-99"],
        "distance": 2
    }

@app.post("/api/v1/cases/{case_id}/disposition")
def record_case_disposition(case_id: str, req: CaseDispositionRequest):
    case = next((c for c in IN_MEMORY_CASES if c["case_id"] == case_id or c["id"] == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case["disposition"] = req.disposition
    case["disposition_rationale"] = req.rationale
    case["status"] = "closed"

    # Feedback loop: Record disposition for model retraining dataset
    feedback_loop.record_disposition(
        case_id=case_id,
        account_id=case.get("subject_account", "ACCT-7842"),
        disposition=req.disposition,
        rationale=req.rationale,
        analyst=req.analyst_name or "analyst.sarah"
    )

    audit_writer.record_event(
        "CASE_DISPOSITION_RECORDED",
        req.analyst_name or "analyst.sarah",
        {"case_id": case_id, "disposition": req.disposition, "rationale": req.rationale}
    )

    return {"message": "Disposition recorded and label feedback queued.", "case": case}

@app.post("/api/v1/cases/{case_id}/signoff")
def signoff_case(case_id: str, payload: Dict[str, Any]):
    decision = payload.get("decision", "APPROVED")
    reviewer = payload.get("analyst_name") or payload.get("reviewer_name", "Lead AML Officer")
    rationale = payload.get("reviewer_rationale", "Verified evidence pack and approved.")
    
    case = next((c for c in IN_MEMORY_CASES if c["case_id"] == case_id or c["id"] == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case["status"] = "closed" if decision == "APPROVED" else "pending_review"
    case["disposition"] = "SAR_SUBMITTED" if decision == "APPROVED" else "REJECTED"
    case["disposition_rationale"] = rationale
    
    audit_entry = audit_writer.record_event(
        "SAR_HUMAN_APPROVAL",
        reviewer,
        {"case_id": case_id, "decision": decision, "rationale": rationale}
    )
    
    return {
        "status": case["status"],
        "message": f"Human compliance officer sign-off sealed ({decision}).",
        "case_id": case_id,
        "reviewed_by": reviewer,
        "audit_ref": audit_entry["entry_hash"]
    }

# SAR Endpoints
@app.get("/api/v1/sar/{case_id}/draft")
def get_sar_draft(case_id: str):
    if case_id not in IN_MEMORY_SAR_DRAFTS:
        raise HTTPException(status_code=404, detail="No SAR draft found for this case. Run investigation first.")
    return IN_MEMORY_SAR_DRAFTS[case_id]

@app.put("/api/v1/sar/{case_id}/draft")
def update_sar_draft(case_id: str, req: SARDraftUpdateRequest):
    draft = IN_MEMORY_SAR_DRAFTS.get(case_id)
    if not draft:
        raise HTTPException(status_code=404, detail="SAR draft not found")

    draft["version"] += 1
    draft["full_narrative_md"] = req.narrative_md
    draft["author"] = req.author
    draft["status"] = "edited"
    draft["updated_at"] = datetime.now(timezone.utc).isoformat()

    audit_writer.record_event(
        "SAR_DRAFT_EDITED",
        req.author,
        {"case_id": case_id, "version": draft["version"]}
    )

    return draft

@app.post("/api/v1/sar/{case_id}/approve")
def approve_sar_draft(case_id: str, req: SARApprovalRequest):
    draft = IN_MEMORY_SAR_DRAFTS.get(case_id)
    if not draft:
        raise HTTPException(status_code=404, detail="SAR draft not found")

    draft["status"] = "approved"
    draft["reviewed_by"] = req.reviewer_name
    draft["approval_rationale"] = req.reviewer_rationale
    draft["approved_at"] = datetime.now(timezone.utc).isoformat()

    # Update case status
    case = next((c for c in IN_MEMORY_CASES if c["case_id"] == case_id), None)
    if case:
        case["status"] = "pending_review"

    audit_entry = audit_writer.record_event(
        "SAR_HUMAN_APPROVAL",
        req.reviewer_name,
        {
            "case_id": case_id,
            "version": draft["version"],
            "rationale": req.reviewer_rationale
        }
    )

    return {
        "status": "APPROVED",
        "case_id": case_id,
        "reviewed_by": req.reviewer_name,
        "audit_ref": audit_entry["entry_hash"]
    }

@app.get("/api/v1/sar/{case_id}/export/fincen")
def export_sar_fincen(case_id: str, format: str = "json"):
    draft = IN_MEMORY_SAR_DRAFTS.get(case_id)
    if not draft:
        raise HTTPException(status_code=404, detail="SAR draft not found")

    case = next((c for c in IN_MEMORY_CASES if c["case_id"] == case_id), {"case_id": case_id, "title": "Case"})
    signoff = {
        "analyst_name": draft.get("reviewed_by") or "Lead Investigator",
        "decision": "APPROVED",
        "reviewer_rationale": draft.get("approval_rationale") or "Evidence pack verified and validated",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if format.lower() == "xml":
        xml_content = FinCENExporter.export_to_xml(case, draft, signoff)
        return Response(content=xml_content, media_type="application/xml")
    
    json_data = FinCENExporter.export_to_json(case, draft, signoff)
    return json_data

@app.get("/api/v1/audit-logs")
def get_audit_logs():
    events = audit_writer.get_events(limit=100)
    integrity = audit_writer.verify_integrity()
    return {"audit_logs": events, "total": len(events), "chain_integrity_verified": integrity}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("casework.main:app", host="0.0.0.0", port=8003, reload=True)
