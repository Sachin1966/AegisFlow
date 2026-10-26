import os
import sys
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from hashlib import pbkdf2_hmac

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aegis_user:aegis_password_secure@localhost:5432/aegisflow_db")

def hash_password(password: str) -> str:
    salt = b"aegis_static_salt_for_dev_seed"
    key = pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return key.hex()

def seed_database():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        print("Seeding initial AegisFlow Users...")
        users = [
            ("usr_admin", "admin", "admin@aegisflow.com", hash_password("AdminPass123!"), "admin"),
            ("usr_fraud1", "fraud_analyst1", "fraud1@aegisflow.com", hash_password("AnalystPass123!"), "fraud_analyst"),
            ("usr_aml1", "aml_analyst1", "aml1@aegisflow.com", hash_password("AnalystPass123!"), "aml_analyst"),
            ("usr_mgr1", "manager1", "manager1@aegisflow.com", hash_password("ManagerPass123!"), "manager"),
        ]
        for uid, username, email, pwd_hash, role in users:
            conn.execute(
                text("""
                    INSERT INTO users (id, username, email, hashed_password, role, created_at)
                    VALUES (:id, :username, :email, :pwd, :role, :now)
                    ON CONFLICT (username) DO NOTHING
                """),
                {"id": uid, "username": username, "email": email, "pwd": pwd_hash, "role": role, "now": datetime.now(timezone.utc)}
            )

        print("Seeding Sanctions List...")
        sanctions = [
            ("sanc_001", "Global Trade Corp Shell", "company", "RU"),
            ("sanc_002", "Viktor Petrov", "individual", "RU"),
            ("sanc_003", "Apex Offshore Holdings", "company", "CY"),
            ("sanc_004", "North Star Financial Ltd", "bank", "KP"),
        ]
        for sid, name, etype, country in sanctions:
            conn.execute(
                text("""
                    INSERT INTO sanctions_list (id, entity_name, entity_type, country, listed_at)
                    VALUES (:id, :name, :etype, :country, :now)
                    ON CONFLICT (id) DO NOTHING
                """),
                {"id": sid, "name": name, "etype": etype, "country": country, "now": datetime.now(timezone.utc)}
            )

        print("Seeding Base Accounts, Devices, IPs, Merchants...")
        # Base Account
        conn.execute(
            text("""
                INSERT INTO accounts (id, holder_name_encrypted, account_type, risk_tier, status)
                VALUES ('acct_base_001', 'EncryptedName_JohnDoe', 'personal', 'low', 'active')
                ON CONFLICT (id) DO NOTHING
            """)
        )
        conn.execute(
            text("""
                INSERT INTO devices (id, device_fingerprint, os, ip_address)
                VALUES ('dev_base_001', 'fp_998877665544', 'iOS', '192.168.1.100')
                ON CONFLICT (id) DO NOTHING
            """)
        )
        conn.execute(
            text("""
                INSERT INTO ips (id, ip_address, country, is_vpn)
                VALUES ('ip_base_001', '192.168.1.100', 'US', false)
                ON CONFLICT (id) DO NOTHING
            """)
        )
        conn.execute(
            text("""
                INSERT INTO merchants (id, name, mcc, risk_score)
                VALUES ('merch_base_001', 'Global Electronics Store', '5732', 0.1)
                ON CONFLICT (id) DO NOTHING
            """)
        )

        print("AegisFlow Database Seeding Completed Successfully!")

if __name__ == "__main__":
    seed_database()
