import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

class FraudRingGenerator:
    def __init__(self, accounts: List[Dict[str, Any]], devices: List[Dict[str, Any]], ips: List[Dict[str, Any]], seed: int = 42):
        random.seed(seed)
        self.accounts = accounts
        self.devices = devices
        self.ips = ips

    def inject_shared_device_ring(self, ring_size: int = 6, base_timestamp: datetime = None) -> Dict[str, Any]:
        """Injects a fraud ring where multiple accounts operate from a single shared device."""
        if base_timestamp is None:
            base_timestamp = datetime.now(timezone.utc)

        ring_accounts = random.sample(self.accounts, min(ring_size, len(self.accounts)))
        shared_device = random.choice(self.devices)
        shared_ip = random.choice(self.ips)

        ring_transactions = []
        new_edges = []

        # Create entity graph edges linking all ring accounts to the shared device & IP
        for acct in ring_accounts:
            new_edges.append({
                "id": f"edge_ring_{uuid.uuid4().hex[:10]}",
                "source_id": acct["id"],
                "source_type": "account",
                "target_id": shared_device["id"],
                "target_type": "device",
                "edge_type": "SHARED_DEVICE",
                "weight": 2.0
            })
            new_edges.append({
                "id": f"edge_ring_{uuid.uuid4().hex[:10]}",
                "source_id": acct["id"],
                "source_type": "account",
                "target_id": shared_ip["id"],
                "target_type": "ip",
                "edge_type": "SHARED_IP",
                "weight": 2.0
            })

        # Generate high-velocity coordinated fraudulent transactions within 30 minutes
        for i, acct in enumerate(ring_accounts):
            tx_time = base_timestamp + timedelta(minutes=i * 3, seconds=random.randint(0, 30))
            amount = round(random.uniform(1500.00, 4900.00), 2)
            
            # Target counterparty or merchant
            target_acct = random.choice([a for a in self.accounts if a["id"] not in [r["id"] for r in ring_accounts]])

            tx = {
                "id": f"tx_ring_{uuid.uuid4().hex[:12]}",
                "timestamp": tx_time,
                "source_account_id": acct["id"],
                "target_account_id": target_acct["id"],
                "amount": amount,
                "currency": "USD",
                "channel": "mobile_app",
                "device_id": shared_device["id"],
                "ip_id": shared_ip["id"],
                "merchant_id": None,
                "status": "completed",
                "is_fraud": True,
                "typology_type": "fraud_ring",
                "injected_pattern": f"shared_device_ring_{shared_device['id']}"
            }
            ring_transactions.append(tx)

        return {
            "transactions": ring_transactions,
            "edges": new_edges,
            "ring_accounts": [a["id"] for a in ring_accounts],
            "shared_device_id": shared_device["id"],
            "shared_ip_id": shared_ip["id"]
        }
