import uuid
from typing import List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import create_engine, text

class LabelManager:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)

    def persist_transactions_and_labels(self, transactions: List[Dict[str, Any]]):
        """
        Persists transaction data into `transactions` table and strictly isolates
        ground-truth evaluation labels into `ground_truth_labels` table.
        """
        print(f"Persisting {len(transactions)} transactions & isolated ground-truth labels...")
        with self.engine.begin() as conn:
            for tx in transactions:
                # 1. Insert Transaction (No fraud labels here!)
                conn.execute(
                    text("""
                        INSERT INTO transactions (
                            id, timestamp, source_account_id, target_account_id,
                            amount, currency, channel, device_id, ip_id, merchant_id, status
                        ) VALUES (
                            :id, :ts, :src, :tgt,
                            :amt, :curr, :channel, :dev, :ip, :merch, :status
                        ) ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": tx["id"],
                        "ts": tx["timestamp"],
                        "src": tx["source_account_id"],
                        "tgt": tx["target_account_id"],
                        "amt": tx["amount"],
                        "curr": tx["currency"],
                        "channel": tx["channel"],
                        "dev": tx["device_id"],
                        "ip": tx["ip_id"],
                        "merch": tx["merchant_id"],
                        "status": tx["status"]
                    }
                )

                # 2. Insert Isolated Ground-Truth Label
                conn.execute(
                    text("""
                        INSERT INTO ground_truth_labels (
                            id, transaction_id, is_fraud, typology_type, injected_pattern, created_at
                        ) VALUES (
                            :lbl_id, :tx_id, :is_fraud, :typology, :pattern, :now
                        ) ON CONFLICT (transaction_id) DO NOTHING
                    """),
                    {
                        "lbl_id": f"gt_{uuid.uuid4().hex[:12]}",
                        "tx_id": tx["id"],
                        "is_fraud": tx.get("is_fraud", False),
                        "typology": tx.get("typology_type", "normal"),
                        "pattern": tx.get("injected_pattern", None),
                        "now": datetime.now(timezone.utc)
                    }
                )
        print("Transactions & Ground-Truth Labels successfully persisted.")
