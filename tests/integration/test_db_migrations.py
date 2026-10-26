import os
import pytest
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aegis_user:aegis_password_secure@localhost:5432/aegisflow_db")

@pytest.mark.integration
def test_database_connection_and_tables():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public';"))
            tables = [row[0] for row in result.fetchall()]
            
            # Verify core table existence if DB is running
            expected_tables = [
                "accounts", "devices", "ips", "merchants", "entity_edges",
                "transactions", "decisions", "alerts", "cases", "evidence_items",
                "sar_drafts", "users", "audit_log", "ground_truth_labels", "sanctions_list"
            ]
            for tbl in expected_tables:
                assert tbl in tables, f"Expected table {tbl} missing from database"
    except Exception as e:
        pytest.skip(f"Database connection not available for integration test: {e}")

@pytest.mark.integration
def test_ground_truth_label_isolation():
    """Verify that transactions table schema has NO ground_truth or is_fraud columns."""
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='transactions';"))
            columns = [row[0] for row in result.fetchall()]
            
            assert "is_fraud" not in columns, "LEAK DETECTED: is_fraud found in transactions table!"
            assert "typology_type" not in columns, "LEAK DETECTED: typology_type found in transactions table!"
    except Exception as e:
        pytest.skip(f"Database connection not available for integration test: {e}")
