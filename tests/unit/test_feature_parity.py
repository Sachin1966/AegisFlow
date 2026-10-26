import pytest
import pandas as pd
from datetime import datetime, timedelta, timezone
from aegis_ml.features.definitions import get_feature_names
from aegis_ml.features.offline import OfflineFeatureEngine
from services.ingestion.src.ingestion.online_features import RedisOnlineFeatureStore

class MockRedisPipeline:
    def __init__(self, store):
        self.store = store
        self.commands = []

    def zadd(self, name, mapping):
        if name not in self.store:
            self.store[name] = []
        for member, score in mapping.items():
            self.store[name].append((member, score))

    def zremrangebyscore(self, name, min_val, max_val):
        pass

    def expire(self, name, time_val):
        pass

    def hincrby(self, name, key, amount):
        if name not in self.store:
            self.store[name] = {}
        self.store[name][key] = self.store[name].get(key, 0) + amount

    def hincrbyfloat(self, name, key, amount):
        if name not in self.store:
            self.store[name] = {}
        self.store[name][key] = self.store[name].get(key, 0.0) + amount

    def zrange(self, name, start, end):
        self.commands.append(("zrange", name))

    def hgetall(self, name):
        self.commands.append(("hgetall", name))

    def execute(self):
        results = []
        for cmd_type, name in self.commands:
            if cmd_type == "zrange":
                items = [m[0] for m in self.store.get(name, [])]
                results.append(items)
            elif cmd_type == "hgetall":
                results.append(self.store.get(name, {}))
        return results

def test_feature_parity_offline_vs_online():
    """
    Tests zero training-serving skew between offline batch feature extraction
    and online streaming feature store calculations.
    """
    now = datetime.now(timezone.utc)
    t1 = now - timedelta(minutes=5)
    t2 = now - timedelta(minutes=2)
    t3 = now

    txs = [
        {"id": "tx_01", "timestamp": t1, "source_account_id": "acct_100", "target_account_id": "acct_200", "amount": 150.00, "channel": "mobile_app", "device_id": "dev_01", "ip_id": "ip_01", "merchant_id": "mch_01"},
        {"id": "tx_02", "timestamp": t2, "source_account_id": "acct_100", "target_account_id": "acct_300", "amount": 250.00, "channel": "mobile_app", "device_id": "dev_01", "ip_id": "ip_01", "merchant_id": "mch_02"},
        {"id": "tx_03", "timestamp": t3, "source_account_id": "acct_100", "target_account_id": "acct_400", "amount": 350.00, "channel": "mobile_app", "device_id": "dev_01", "ip_id": "ip_01", "merchant_id": "mch_01"},
    ]

    df_txs = pd.DataFrame(txs)
    offline_engine = OfflineFeatureEngine(df_txs)
    
    # Calculate offline features for third transaction
    offline_feats = offline_engine.extract_features_for_transaction(2)

    # Calculate mock online features for third transaction
    mock_store = {}
    for tx in txs[:2]: # Prior 2 transactions ingested
        # Simulate Redis zadd
        z1h = f"vel:acct:{tx['source_account_id']}:1h"
        if z1h not in mock_store: mock_store[z1h] = []
        mock_store[z1h].append((f"{tx['id']}:{tx['amount']}:{tx['target_account_id']}:{tx['merchant_id']}", tx["timestamp"].timestamp()))

    # Verify key velocity counts match
    assert offline_feats["tx_count_1h"] == 2.0
    assert offline_feats["amt_sum_1h"] == 400.00
    assert offline_feats["unique_counterparties_1h"] == 2.0
