import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from scoring.main import app as scoring_app
from casework.main import app as casework_app
from investigator.main import app as investigator_app

def test_full_lifecycle_fraud_to_sar_export():
    """
    End-to-End Test:
    1. Score high-risk transaction with SHAP reason codes
    2. Promote/correlate alert into AML case
    3. Run 6-agent LangGraph investigation pipeline
    4. Verify QA reviewer claim verification
    5. Manager approves SAR draft with audit trail
    6. Export FinCEN-compliant SAR package
    7. Submit disposition to feedback loop for ML retraining
    """
    scoring_client = TestClient(scoring_app)
    casework_client = TestClient(casework_app)
    investigator_client = TestClient(investigator_app)

    # Step 1: Real-Time Scoring
    tx_payload = {
        "transaction": {
            "id": "tx_e2e_smurf_01",
            "source_account_id": "ACCT-7842",
            "target_account_id": "ACCT-9011",
            "amount": 9850.00,
            "currency": "USD",
            "channel": "mobile_app",
            "device_id": "DEV-9812"
        },
        "features": {
            "tx_count_1h": 5.0,
            "amt_sum_1h": 48200.0,
            "amt_deviation_zscore": 3.8,
            "distance_to_known_fraud": 2.0,
            "acct_count_per_device_24h": 6.0
        },
        "degraded": False
    }

    score_res = scoring_client.post("/api/v1/score", json=tx_payload)
    assert score_res.status_code == 200
    score_data = score_res.json()
    assert score_data["decision"] in ("REVIEW", "DECLINE")
    assert len(score_data["reason_codes"]) >= 1
    assert score_data["latency_ms"] < 100.0

    # Step 2: Correlate Alert & Promote to Case
    promote_res = casework_client.post("/api/v1/alerts/promote", json={
        "alert_id": "ALT-E2E-001",
        "title": "E2E Suspected Structuring Ring ACCT-7842",
        "severity": "critical",
        "amount": 9850.00,
        "source_account": "ACCT-7842",
        "assigned_analyst": "analyst.sarah"
    })
    assert promote_res.status_code == 200
    case_obj = promote_res.json()["case"]
    case_id = case_obj["case_id"]
    assert case_obj["priority"] == "critical"

    # Step 3: Run Multi-Agent Investigation
    inv_res = investigator_client.post("/api/v1/investigate", json={
        "case_id": case_id,
        "target_account_id": "ACCT-7842"
    })
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["status"] == "COMPLETED"
    assert inv_data["total_agent_turns"] == 6

    # Verify Agent Trajectory
    agent_names = [step["agent"] for step in inv_data["steps_log"]]
    assert "Supervisor" in agent_names
    assert "LinkAnalyst" in agent_names
    assert "PatternAnalyst" in agent_names
    assert "AdverseMediaResearcher" in agent_names
    assert "NarrativeWriter" in agent_names
    assert "QAReviewer" in agent_names

    # Step 4: SAR Draft & Evidence Integrity
    sar_draft = inv_data["sar_draft"]
    assert sar_draft["qa_review_status"] == "PASSED"
    assert sar_draft["requires_human_signoff"] is True
    assert len(sar_draft["evidence_citations"]) >= 3

    # Step 5: Manager SAR Approval
    approval_res = casework_client.post(f"/api/v1/sar/CASE-2026-001/approve", json={
        "reviewer_rationale": "Audited evidence pack and confirmed 2-hop sanctioned connection. Filing authorized.",
        "reviewer_name": "Chief Compliance Officer"
    })
    assert approval_res.status_code == 200
    assert approval_res.json()["status"] == "APPROVED"
    assert "audit_ref" in approval_res.json()

    # Step 6: Export FinCEN Structured SAR
    fincen_res = casework_client.get(f"/api/v1/sar/CASE-2026-001/export/fincen?format=json")
    assert fincen_res.status_code == 200
    fincen_data = fincen_res.json()
    assert "FinCEN_BSA_E_Filing" in fincen_data
    assert fincen_data["FinCEN_BSA_E_Filing"]["AnalystSignoff"]["Decision"] == "APPROVED"

    # Step 7: Disposition Case & Feed Back Label
    disp_res = casework_client.post(f"/api/v1/cases/{case_id}/disposition", json={
        "disposition": "sar_filed",
        "rationale": "High confidence laundering ring confirmed via multi-agent evidence.",
        "analyst_name": "analyst.sarah"
    })
    assert disp_res.status_code == 200
    assert disp_res.json()["case"]["status"] == "closed"
