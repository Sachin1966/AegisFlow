import os
import time
import logging
from typing import Dict, Any, Tuple
import redis
from aegis_ml.features.definitions import get_default_feature_vector, get_feature_names

logger = logging.getLogger("aegis_online_features")

class RedisOnlineFeatureStore:
    """
    Redis Online Feature Store Handler for AegisFlow.
    Implements sliding-window ZSET velocity updates, HASH aggregate lookups,
    pipelined bulk retrieval, and degraded mode fallback.
    """
    def __init__(self, redis_url: str = None):
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_url = redis_url
        self._redis_client = None

    @property
    def client(self) -> redis.Redis:
        if self._redis_client is None:
            self._redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True, socket_timeout=1.0)
        return self._redis_client

    def update_online_features(self, tx: Dict[str, Any]) -> bool:
        """
        Atomically updates online features in Redis upon transaction ingestion.
        Returns True if successful, False if degraded fallback was triggered.
        """
        try:
            r = self.client
            pipe = r.pipeline(transaction=True)

            acct_id = tx["source_account_id"]
            dev_id = tx.get("device_id")
            ip_id = tx.get("ip_id")
            merch_id = tx.get("merchant_id")
            target_acct_id = tx.get("target_account_id")
            amount = float(tx["amount"])

            now_ts = float(tx["timestamp"].timestamp()) if hasattr(tx["timestamp"], "timestamp") else time.time()
            tx_id = tx["id"]

            # 1. Sliding Window ZSETs for Account Velocity
            for window_sec, name_suffix in [(60, "1m"), (3600, "1h"), (86400, "24h"), (604800, "7d")]:
                zkey = f"vel:acct:{acct_id}:{name_suffix}"
                # Add transaction (score = timestamp, member = tx_id:amount)
                pipe.zadd(zkey, {f"{tx_id}:{amount}:{target_acct_id or 'none'}:{merch_id or 'none'}": now_ts})
                # Evict expired events
                pipe.zremrangebyscore(zkey, "-inf", now_ts - window_sec)
                pipe.expire(zkey, window_sec + 3600) # TTL safety buffer

            # 2. Device & IP Sharing Degree ZSETs
            if dev_id:
                dev_zkey = f"vel:dev:{dev_id}:24h"
                pipe.zadd(dev_zkey, {f"{acct_id}:{tx_id}": now_ts})
                pipe.zremrangebyscore(dev_zkey, "-inf", now_ts - 86400)
                pipe.expire(dev_zkey, 90000)

            if ip_id:
                ip_zkey = f"vel:ip:{ip_id}:24h"
                pipe.zadd(ip_zkey, {f"{acct_id}:{tx_id}": now_ts})
                pipe.zremrangebyscore(ip_zkey, "-inf", now_ts - 86400)
                pipe.expire(ip_zkey, 90000)

            # 3. Behavioral Aggregate Hashes (30-day running stats)
            acct_hash_key = f"feat:acct:{acct_id}"
            pipe.hincrby(acct_hash_key, "total_tx_count", 1)
            pipe.hincrbyfloat(acct_hash_key, "total_amt_sum", amount)
            pipe.expire(acct_hash_key, 2592000) # 30 days TTL

            pipe.execute()
            return True

        except Exception as e:
            logger.warning(f"Redis unavailable during feature update ({e}). Triggering degraded mode.")
            return False

    def get_online_features(self, acct_id: str, dev_id: str = None, ip_id: str = None, merch_id: str = None) -> Tuple[Dict[str, float], bool]:
        """
        Retrieves real-time feature vector for scoring service using PIPELINED Redis reads.
        Returns: (feature_dict, degraded_flag)
        """
        default_features = get_default_feature_vector()
        
        try:
            r = self.client
            pipe = r.pipeline(transaction=False)

            # Pipelined Read Queries
            z_1m_key = f"vel:acct:{acct_id}:1m"
            z_1h_key = f"vel:acct:{acct_id}:1h"
            z_24h_key = f"vel:acct:{acct_id}:24h"
            z_7d_key = f"vel:acct:{acct_id}:7d"
            dev_key = f"vel:dev:{dev_id}:24h" if dev_id else None
            ip_key = f"vel:ip:{ip_id}:24h" if ip_id else None
            acct_hash_key = f"feat:acct:{acct_id}"
            gfeat_key = f"gfeat:acct:{acct_id}"

            pipe.zrange(z_1m_key, 0, -1)
            pipe.zrange(z_1h_key, 0, -1)
            pipe.zrange(z_24h_key, 0, -1)
            pipe.zrange(z_7d_key, 0, -1)

            if dev_key:
                pipe.zrange(dev_key, 0, -1)
            if ip_key:
                pipe.zrange(ip_key, 0, -1)

            pipe.hgetall(acct_hash_key)
            pipe.hgetall(gfeat_key)

            results = pipe.execute()

            items_1m = results[0]
            items_1h = results[1]
            items_24h = results[2]
            items_7d = results[3]

            res_idx = 4
            dev_items = results[res_idx] if dev_key else []
            if dev_key: res_idx += 1
            ip_items = results[res_idx] if ip_key else []
            if ip_key: res_idx += 1

            acct_hash = results[res_idx]
            gfeat_hash = results[res_idx + 1]

            features = default_features.copy()

            # Process Velocity & Amount sums
            features["tx_count_1m"] = float(len(items_1m))
            features["tx_count_1h"] = float(len(items_1h))
            features["tx_count_24h"] = float(len(items_24h))
            features["tx_count_7d"] = float(len(items_7d))

            amt_1h = 0.0
            unique_cp_1h = set()
            for item in items_1h:
                parts = item.split(":")
                if len(parts) >= 2:
                    amt_1h += float(parts[1])
                if len(parts) >= 3 and parts[2] != "none":
                    unique_cp_1h.add(parts[2])

            amt_24h = 0.0
            unique_merch_24h = set()
            for item in items_24h:
                parts = item.split(":")
                if len(parts) >= 2:
                    amt_24h += float(parts[1])
                if len(parts) >= 4 and parts[3] != "none":
                    unique_merch_24h.add(parts[3])

            features["amt_sum_1h"] = amt_1h
            features["amt_sum_24h"] = amt_24h
            features["unique_counterparties_1h"] = float(len(unique_cp_1h))
            features["unique_merchants_24h"] = float(len(unique_merch_24h))

            # Process Device & IP Sharing Degrees
            if dev_items:
                dev_accounts = set(item.split(":")[0] for item in dev_items)
                features["acct_count_per_device_24h"] = float(len(dev_accounts))
                features["device_sharing_degree"] = float(len(dev_accounts))

            if ip_items:
                ip_accounts = set(item.split(":")[0] for item in ip_items)
                features["acct_count_per_ip_24h"] = float(len(ip_accounts))
                features["ip_sharing_degree"] = float(len(ip_accounts))

            # Process Behavioral Profile Hash
            if acct_hash and "total_tx_count" in acct_hash:
                cnt = float(acct_hash.get("total_tx_count", 1))
                tot_amt = float(acct_hash.get("total_amt_sum", 0.0))
                features["acct_avg_amt_30d"] = tot_amt / max(1.0, cnt)

            # Process Graph Cached Features
            if gfeat_hash:
                for gk in ["connected_component_size", "shortest_path_to_known_fraud", "distance_to_known_fraud", "propagated_risk_score", "pagerank_risk_score"]:
                    if gk in gfeat_hash:
                        features[gk] = float(gfeat_hash[gk])

            return features, False

        except Exception as e:
            logger.warning(f"Redis query failed ({e}). Returning degraded default feature vector.")
            return default_features, True
