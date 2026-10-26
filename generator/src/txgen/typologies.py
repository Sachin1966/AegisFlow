import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

class TypologyGenerator:
    def __init__(self, accounts: List[Dict[str, Any]], devices: List[Dict[str, Any]], ips: List[Dict[str, Any]], seed: int = 42):
        random.seed(seed)
        self.accounts = accounts
        self.devices = devices
        self.ips = ips

    def inject_smurfing(self, fan_in_count: int = 5, base_timestamp: datetime = None) -> List[Dict[str, Any]]:
        """
        Smurfing / Structuring:
        Multiple sub-threshold deposits ($9,100 - $9,800) into fan-in accounts,
        consolidated immediately into a single master beneficiary account.
        """
        if base_timestamp is None:
            base_timestamp = datetime.now(timezone.utc)

        master_acct = random.choice(self.accounts)
        smurf_sources = random.sample([a for a in self.accounts if a["id"] != master_acct["id"]], fan_in_count)
        
        transactions = []
        dev = random.choice(self.devices)
        ip = random.choice(self.ips)

        # Phase 1: Sub-threshold cash deposits into smurf accounts
        for i, src in enumerate(smurf_sources):
            amount = round(random.uniform(9100.00, 9850.00), 2)
            tx_time = base_timestamp + timedelta(minutes=i * 10)
            
            # Incoming deposit to smurf source
            transactions.append({
                "id": f"tx_smurf_in_{uuid.uuid4().hex[:10]}",
                "timestamp": tx_time,
                "source_account_id": src["id"],
                "target_account_id": None, # Deposit
                "amount": amount,
                "currency": "USD",
                "channel": "atm",
                "device_id": dev["id"],
                "ip_id": ip["id"],
                "merchant_id": None,
                "status": "completed",
                "is_fraud": True,
                "typology_type": "smurfing",
                "injected_pattern": f"smurfing_deposit_{master_acct['id']}"
            })

            # Phase 2: Rapid fan-in consolidation to master account
            consolidation_time = tx_time + timedelta(minutes=15)
            transactions.append({
                "id": f"tx_smurf_out_{uuid.uuid4().hex[:10]}",
                "timestamp": consolidation_time,
                "source_account_id": src["id"],
                "target_account_id": master_acct["id"],
                "amount": amount - 50.00, # Small fee deduction
                "currency": "USD",
                "channel": "wire_transfer",
                "device_id": dev["id"],
                "ip_id": ip["id"],
                "merchant_id": None,
                "status": "completed",
                "is_fraud": True,
                "typology_type": "smurfing",
                "injected_pattern": f"smurfing_consolidation_{master_acct['id']}"
            })

        return transactions

    def inject_layering(self, hop_count: int = 4, base_timestamp: datetime = None) -> List[Dict[str, Any]]:
        """
        Layering:
        Rapid sequence of transfers through intermediary accounts (A -> B -> C -> D)
        to obfuscate origin of funds.
        """
        if base_timestamp is None:
            base_timestamp = datetime.now(timezone.utc)

        chain_accts = random.sample(self.accounts, min(hop_count + 1, len(self.accounts)))
        start_amount = round(random.uniform(45000.00, 80000.00), 2)
        transactions = []
        
        dev = random.choice(self.devices)
        ip = random.choice(self.ips)

        current_time = base_timestamp
        current_amount = start_amount

        for i in range(len(chain_accts) - 1):
            src = chain_accts[i]
            tgt = chain_accts[i + 1]

            tx = {
                "id": f"tx_layer_{uuid.uuid4().hex[:10]}",
                "timestamp": current_time,
                "source_account_id": src["id"],
                "target_account_id": tgt["id"],
                "amount": current_amount,
                "currency": "USD",
                "channel": "wire_transfer",
                "device_id": dev["id"],
                "ip_id": ip["id"],
                "merchant_id": None,
                "status": "completed",
                "is_fraud": True,
                "typology_type": "layering",
                "injected_pattern": f"layering_chain_hop_{i+1}"
            }
            transactions.append(tx)

            # Advance time by 5–12 minutes and slightly diminish amount (wire fees)
            current_time += timedelta(minutes=random.randint(5, 12))
            current_amount = round(current_amount * random.uniform(0.97, 0.99), 2)

        return transactions

    def inject_round_tripping(self, loop_length: int = 3, base_timestamp: datetime = None) -> List[Dict[str, Any]]:
        """
        Round-Tripping:
        Circular flow of funds (A -> B -> C -> A) returning to original account.
        """
        if base_timestamp is None:
            base_timestamp = datetime.now(timezone.utc)

        loop_accts = random.sample(self.accounts, min(loop_length, len(self.accounts)))
        # Append origin to close loop
        loop_accts.append(loop_accts[0])
        
        amount = round(random.uniform(25000.00, 50000.00), 2)
        transactions = []

        dev = random.choice(self.devices)
        ip = random.choice(self.ips)
        current_time = base_timestamp

        for i in range(len(loop_accts) - 1):
            src = loop_accts[i]
            tgt = loop_accts[i + 1]

            tx = {
                "id": f"tx_round_{uuid.uuid4().hex[:10]}",
                "timestamp": current_time,
                "source_account_id": src["id"],
                "target_account_id": tgt["id"],
                "amount": amount,
                "currency": "USD",
                "channel": "web_portal",
                "device_id": dev["id"],
                "ip_id": ip["id"],
                "merchant_id": None,
                "status": "completed",
                "is_fraud": True,
                "typology_type": "round_tripping",
                "injected_pattern": f"round_trip_loop_step_{i+1}"
            }
            transactions.append(tx)
            current_time += timedelta(minutes=15)

        return transactions
