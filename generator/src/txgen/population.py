import random
import uuid
from typing import List, Dict, Any
from faker import Faker
from sqlalchemy import create_engine, text

fake = Faker()

class EntityPopulation:
    def __init__(self, seed: int = 42):
        Faker.seed(seed)
        random.seed(seed)
        self.accounts: List[Dict[str, Any]] = []
        self.devices: List[Dict[str, Any]] = []
        self.ips: List[Dict[str, Any]] = []
        self.merchants: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, Any]] = []

    def seed_entities(self, num_accounts: int = 1000, num_devices: int = 500, num_ips: int = 400, num_merchants: int = 200):
        print(f"Generating population: {num_accounts} accounts, {num_devices} devices, {num_ips} IPs, {num_merchants} merchants...")
        
        # 1. Devices
        for _ in range(num_devices):
            dev_id = f"dev_{uuid.uuid4().hex[:12]}"
            fp = f"fp_{uuid.uuid4().hex[:16]}"
            device = {
                "id": dev_id,
                "device_fingerprint": fp,
                "os": random.choice(["iOS", "Android", "Windows", "MacOS", "Linux"]),
                "ip_address": fake.ipv4()
            }
            self.devices.append(device)

        # 2. IPs
        for _ in range(num_ips):
            ip_id = f"ip_{uuid.uuid4().hex[:12]}"
            ip_obj = {
                "id": ip_id,
                "ip_address": fake.ipv4(),
                "country": fake.country_code(),
                "is_vpn": random.random() < 0.08
            }
            self.ips.append(ip_obj)

        # 3. Merchants
        mcc_codes = ["5732", "5411", "5812", "5999", "4814", "7995"] # 7995 = Gambling (high risk)
        for _ in range(num_merchants):
            mch_id = f"merch_{uuid.uuid4().hex[:12]}"
            mcc = random.choice(mcc_codes)
            risk = 0.8 if mcc == "7995" else round(random.uniform(0.01, 0.2), 2)
            merchant = {
                "id": mch_id,
                "name": fake.company(),
                "mcc": mcc,
                "risk_score": risk
            }
            self.merchants.append(merchant)

        # 4. Accounts & Entity Edges
        for i in range(num_accounts):
            acct_id = f"acct_{uuid.uuid4().hex[:12]}"
            # Encrypted name mock
            enc_name = f"Encrypted_{fake.name().replace(' ', '_')}"
            tier = "high" if random.random() < 0.05 else ("medium" if random.random() < 0.2 else "low")
            acct = {
                "id": acct_id,
                "holder_name_encrypted": enc_name,
                "account_type": random.choice(["personal", "business", "payroll"]),
                "risk_tier": tier,
                "status": "active"
            }
            self.accounts.append(acct)

            # Assign primary device and primary IP
            primary_dev = random.choice(self.devices)
            primary_ip = random.choice(self.ips)

            # Add edges
            self.edges.append({
                "id": f"edge_{uuid.uuid4().hex[:12]}",
                "source_id": acct_id,
                "source_type": "account",
                "target_id": primary_dev["id"],
                "target_type": "device",
                "edge_type": "USED_DEVICE",
                "weight": 1.0
            })
            self.edges.append({
                "id": f"edge_{uuid.uuid4().hex[:12]}",
                "source_id": acct_id,
                "source_type": "account",
                "target_id": primary_ip["id"],
                "target_type": "ip",
                "edge_type": "USED_IP",
                "weight": 1.0
            })

    def persist_to_db(self, db_url: str):
        print(f"Persisting population to database at {db_url}...")
        engine = create_engine(db_url)
        with engine.begin() as conn:
            # Insert Devices
            for dev in self.devices:
                conn.execute(
                    text("INSERT INTO devices (id, device_fingerprint, os, ip_address) VALUES (:id, :fp, :os, :ip) ON CONFLICT (id) DO NOTHING"),
                    {"id": dev["id"], "fp": dev["device_fingerprint"], "os": dev["os"], "ip": dev["ip_address"]}
                )

            # Insert IPs
            for ip_obj in self.ips:
                conn.execute(
                    text("INSERT INTO ips (id, ip_address, country, is_vpn) VALUES (:id, :ip, :country, :vpn) ON CONFLICT (id) DO NOTHING"),
                    {"id": ip_obj["id"], "ip": ip_obj["ip_address"], "country": ip_obj["country"], "vpn": ip_obj["is_vpn"]}
                )

            # Insert Merchants
            for merch in self.merchants:
                conn.execute(
                    text("INSERT INTO merchants (id, name, mcc, risk_score) VALUES (:id, :name, :mcc, :risk) ON CONFLICT (id) DO NOTHING"),
                    {"id": merch["id"], "name": merch["name"], "mcc": merch["mcc"], "risk": merch["risk_score"]}
                )

            # Insert Accounts
            for acct in self.accounts:
                conn.execute(
                    text("INSERT INTO accounts (id, holder_name_encrypted, account_type, risk_tier, status) VALUES (:id, :name, :type, :tier, :status) ON CONFLICT (id) DO NOTHING"),
                    {"id": acct["id"], "name": acct["holder_name_encrypted"], "type": acct["account_type"], "tier": acct["risk_tier"], "status": acct["status"]}
                )

            # Insert Edges
            for edge in self.edges:
                conn.execute(
                    text("""
                        INSERT INTO entity_edges (id, source_id, source_type, target_id, target_type, edge_type, weight)
                        VALUES (:id, :src, :src_t, :tgt, :tgt_t, :e_type, :w)
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {"id": edge["id"], "src": edge["source_id"], "src_t": edge["source_type"], "tgt": edge["target_id"], "tgt_t": edge["target_type"], "e_type": edge["edge_type"], "w": edge["weight"]}
                )
        print("Population persisted successfully!")
