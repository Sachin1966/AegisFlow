import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

class NormalBehaviorGenerator:
    def __init__(self, accounts: List[Dict[str, Any]], devices: List[Dict[str, Any]], ips: List[Dict[str, Any]], merchants: List[Dict[str, Any]], seed: int = 42):
        random.seed(seed)
        self.accounts = accounts
        self.devices = devices
        self.ips = ips
        self.merchants = merchants
        self.channels = ["mobile_app", "web_portal", "pos_terminal", "atm", "wire_transfer"]
        self.channel_weights = [0.45, 0.30, 0.15, 0.07, 0.03]

    def generate_transaction(self, base_timestamp: datetime = None) -> Dict[str, Any]:
        if base_timestamp is None:
            base_timestamp = datetime.now(timezone.utc)

        # Diurnal seasonality (peak during 08:00 - 22:00)
        hour_offset = random.choices(range(24), weights=[1,1,1,1,1,2,5,8,10,12,12,12,12,10,10,10,10,8,6,4,3,2,1,1])[0]
        minute_offset = random.randint(0, 59)
        second_offset = random.randint(0, 59)
        tx_time = base_timestamp.replace(hour=hour_offset, minute=minute_offset, second=second_offset)

        source_acct = random.choice(self.accounts)
        
        # 70% merchant transactions, 30% P2P transactions
        is_merchant = random.random() < 0.7
        target_acct_id = None
        merchant_id = None

        if is_merchant:
            merchant = random.choice(self.merchants)
            merchant_id = merchant["id"]
        else:
            # Pick distinct target account
            target_acct = random.choice([a for a in self.accounts if a["id"] != source_acct["id"]])
            target_acct_id = target_acct["id"]

        # Amount log-normal distribution for retail transactions
        amount = round(random.lognormvariate(mu=4.0, sigma=0.8), 2)
        amount = max(1.00, min(amount, 5000.00))

        channel = random.choices(self.channels, weights=self.channel_weights)[0]
        device = random.choice(self.devices)
        ip = random.choice(self.ips)

        tx_id = f"tx_{uuid.uuid4().hex[:14]}"

        return {
            "id": tx_id,
            "timestamp": tx_time,
            "source_account_id": source_acct["id"],
            "target_account_id": target_acct_id,
            "amount": amount,
            "currency": "USD",
            "channel": channel,
            "device_id": device["id"],
            "ip_id": ip["id"],
            "merchant_id": merchant_id,
            "status": "completed",
            "is_fraud": False,
            "typology_type": "normal",
            "injected_pattern": None
        }

    def generate_batch(self, count: int = 1000, start_time: datetime = None) -> List[Dict[str, Any]]:
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(days=7)

        transactions = []
        for i in range(count):
            day_offset = random.randint(0, 6)
            current_base = start_time + timedelta(days=day_offset)
            tx = self.generate_transaction(current_base)
            transactions.append(tx)

        # Sort chronologically
        transactions.sort(key=lambda x: x["timestamp"])
        return transactions
