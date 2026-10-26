import pytest
from fastapi.testclient import TestClient

from scoring.main import app as scoring_app
from casework.main import app as casework_app
from investigator.main import app as investigator_app

@pytest.fixture
def scoring_client():
    return TestClient(scoring_app)

@pytest.fixture
def casework_client():
    return TestClient(casework_app)

@pytest.fixture
def investigator_client():
    return TestClient(investigator_app)

def test_scoring_api_contract(scoring_client):
    req_body = {
        "transaction": {
            "id": "tx_contract_test",
            "source_account_id": "ACCT-TEST",
            "amount": 9500.0,
            "currency": "USD"
        },
        "features": {
            "tx_count_1h": 4.0,
            "amt_sum_1h": 28000.0,
            "distance_to_known_fraud": 2.0
        },
        "degraded": False
    }
    res = scoring_client.post("/api/v1/score", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert "decision" in data
    assert data["decision"] in ("APPROVE", "REVIEW", "DECLINE")
    assert "probability" in data
    assert "reason_codes" in data
    assert len(data["reason_codes"]) <= 5
    assert "latency_ms" in data

def test_threshold_management_and_rollback(scoring_client):
    # 1. Read initial thresholds
    res_get = scoring_client.get("/api/v1/thresholds")
    assert res_get.status_code == 200
    orig_rev = res_get.json()["review_threshold"]
    orig_dec = res_get.json()["decline_threshold"]

    # 2. Update thresholds
    res_put = scoring_client.put("/api/v1/thresholds", json={
        "review_threshold": 0.60,
        "decline_threshold": 0.80,
        "reason": "Test threshold tightening",
        "updated_by": "test_risk_manager"
    })
    assert res_put.status_code == 200
    assert res_put.json()["review_threshold"] == 0.60
    assert res_put.json()["decline_threshold"] == 0.80
    assert res_put.json()["rollback_available"] is True

    # 3. Rollback
    res_rb = scoring_client.post("/api/v1/thresholds/rollback?actor=test_risk_manager")
    assert res_rb.status_code == 200
    assert res_rb.json()["review_threshold"] == orig_rev
    assert res_rb.json()["decline_threshold"] == orig_dec

def test_casework_sar_fincen_export(casework_client):
    # Test JSON export
    res_json = casework_client.get("/api/v1/sar/CASE-2026-001/export/fincen?format=json")
    assert res_json.status_code == 200
    data = res_json.json()
    assert "FinCEN_BSA_E_Filing" in data
    assert data["FinCEN_BSA_E_Filing"]["CaseReference"] == "CASE-2026-001"

    # Test XML export
    res_xml = casework_client.get("/api/v1/sar/CASE-2026-001/export/fincen?format=xml")
    assert res_xml.status_code == 200
    assert "application/xml" in res_xml.headers["content-type"]
    assert "<FinCEN_SAR_Batch" in res_xml.text

def test_mcp_server_contract(investigator_client):
    # List tools
    res_tools = investigator_client.get("/mcp/tools")
    assert res_tools.status_code == 200
    tools = res_tools.json()["tools"]
    tool_names = [t["name"] for t in tools]
    assert "khop_neighborhood" in tool_names
    assert "typology_scan" in tool_names
    assert "adverse_media_search" in tool_names

    # Call tool
    res_call = investigator_client.post("/mcp/call", json={
        "tool_name": "typology_scan",
        "arguments": {"account_id": "ACCT-7842"}
    })
    assert res_call.status_code == 200
    res_data = res_call.json()["result"]
    assert res_data["smurfing"]["detected"] is True
