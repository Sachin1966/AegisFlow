import pytest
from fastapi.testclient import TestClient

from casework.main import app as casework_app
from investigator.main import app as investigator_app

@pytest.mark.unit
def test_casework_health():
    client = TestClient(casework_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "casework"

@pytest.mark.unit
def test_casework_alerts_and_cases():
    client = TestClient(casework_app)
    res_alerts = client.get("/api/v1/alerts")
    assert res_alerts.status_code == 200
    assert "alerts" in res_alerts.json()

    res_cases = client.get("/api/v1/cases")
    assert res_cases.status_code == 200
    assert "cases" in res_cases.json()

@pytest.mark.unit
def test_investigator_health():
    client = TestClient(investigator_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "investigator"

@pytest.mark.unit
def test_investigator_workflow():
    client = TestClient(investigator_app)
    res = client.post("/api/v1/investigate", json={"case_id": "TEST-CASE-001", "target_account_id": "ACCT-7842"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert len(data["steps_log"]) == 6
    assert data["sar_draft"]["requires_human_signoff"] is True

@pytest.mark.unit
def test_report_models_endpoint():
    client = TestClient(investigator_app)
    res = client.get("/api/v1/reports/models")
    assert res.status_code == 200
    data = res.json()
    assert "ollama_available" in data
    assert "models" in data
    assert "providers" in data

@pytest.mark.unit
def test_ai_report_generation_and_valid_contents():
    client = TestClient(investigator_app)
    payload = {
        "case_id": "TEST-CASE-001",
        "target_account_id": "ACCT-7842",
        "report_type": "fincen_sar",
        "audience_tone": "formal_regulatory",
        "llm_provider": "template" # test deterministic template or ollama fallback
    }
    res = client.post("/api/v1/reports/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "report_id" in data
    assert "report_markdown" in data
    assert "cryptographic_hash" in data
    md = data["report_markdown"]
    # Check valid contents
    assert "ACCT-7842" in md
    assert "DEV-9812" in md
    assert "$76,400.00" in md
    assert "[Citation: EV-01]" in md
    assert "[Citation: EV-02]" in md
    assert "[Citation: EV-03]" in md
    assert "[Citation: EV-04]" in md
    assert "[Citation: EV-05]" in md
    assert "Part II: Suspicious Activity Pattern & Chronological Flow of Funds" in md
    assert data["qa_verification"]["qa_status"] == "PASSED"
    assert data["qa_verification"]["faithfulness_score"] == 100.0

@pytest.mark.unit
def test_ai_report_refinement():
    client = TestClient(investigator_app)
    payload = {
        "case_id": "TEST-CASE-001",
        "current_report_md": "# SAR Draft\nSubject: ACCT-7842\n[Citation: EV-01]\n[Citation: EV-02]\n[Citation: EV-03]\n[Citation: EV-04]\n[Citation: EV-05]",
        "user_instruction": "Add sanctions analysis for OFAC entity ACCT-99 via Shell Corp LLC."
    }
    res = client.post("/api/v1/reports/refine", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "REFINED"
    assert "ACCT-KNOWN-FRAUD-99" in data["refined_markdown"] or "sanction" in data["refined_markdown"].lower()
    assert data["qa_verification"]["qa_status"] == "PASSED"

