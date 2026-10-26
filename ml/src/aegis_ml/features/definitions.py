from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class FeatureSpec:
    name: str
    entity: str       # account, device, ip, merchant
    window_seconds: int  # 60, 3600, 86400, 604800, etc.
    aggregation: str  # count, sum, avg, std, unique_count, zscore, flag
    default_value: float
    description: str

# Master Feature Registry - SINGLE SOURCE OF TRUTH
FEATURE_DEFINITIONS: List[FeatureSpec] = [
    # --- Velocity Features ---
    FeatureSpec("tx_count_1m", "account", 60, "count", 0.0, "Transactions in last 1 minute"),
    FeatureSpec("tx_count_1h", "account", 3600, "count", 0.0, "Transactions in last 1 hour"),
    FeatureSpec("tx_count_24h", "account", 86400, "count", 0.0, "Transactions in last 24 hours"),
    FeatureSpec("tx_count_7d", "account", 604800, "count", 0.0, "Transactions in last 7 days"),
    FeatureSpec("amt_sum_1h", "account", 3600, "sum", 0.0, "Total amount spent in last 1 hour"),
    FeatureSpec("amt_sum_24h", "account", 86400, "sum", 0.0, "Total amount spent in last 24 hours"),
    FeatureSpec("unique_counterparties_1h", "account", 3600, "unique_count", 0.0, "Unique counterparties in last 1 hour"),
    FeatureSpec("unique_merchants_24h", "account", 86400, "unique_count", 0.0, "Unique merchants in last 24 hours"),

    # --- Behavioral Features ---
    FeatureSpec("acct_avg_amt_30d", "account", 2592000, "avg", 120.0, "30-day average transaction amount"),
    FeatureSpec("amt_deviation_zscore", "account", 2592000, "zscore", 0.0, "Transaction amount Z-score vs 30d mean"),
    FeatureSpec("tx_freq_24h", "account", 86400, "count", 0.0, "Daily transaction frequency"),
    FeatureSpec("time_of_day_anomaly", "account", 86400, "flag", 0.0, "Unusual hour of activity flag"),

    # --- Device & IP Features ---
    FeatureSpec("acct_count_per_device_24h", "device", 86400, "unique_count", 1.0, "Number of distinct accounts per device in 24h"),
    FeatureSpec("acct_count_per_ip_24h", "ip", 86400, "unique_count", 1.0, "Number of distinct accounts per IP in 24h"),
    FeatureSpec("device_sharing_degree", "device", 604800, "unique_count", 1.0, "7-day device sharing degree centrality"),
    FeatureSpec("ip_sharing_degree", "ip", 604800, "unique_count", 1.0, "7-day IP sharing degree centrality"),
    FeatureSpec("is_vpn_ip", "ip", 0, "flag", 0.0, "Flag indicating if IP address is a VPN/Proxy"),

    # --- Graph Features ---
    FeatureSpec("connected_component_size", "account", 0, "count", 1.0, "Size of entity graph connected component"),
    FeatureSpec("shortest_path_to_known_fraud", "account", 0, "count", 99.0, "Shortest path hop count to known fraudulent node"),
    FeatureSpec("distance_to_known_fraud", "account", 0, "count", 99.0, "Distance metric to closest fraudulent node"),
    FeatureSpec("propagated_risk_score", "account", 0, "avg", 0.0, "Graph propagated risk score (0.0 to 1.0)"),
    FeatureSpec("pagerank_risk_score", "account", 0, "avg", 0.001, "PageRank centrality risk score"),

    # --- Geo & Risk Features ---
    FeatureSpec("impossible_travel_flag", "account", 3600, "flag", 0.0, "Flag for physically impossible travel speed"),
    FeatureSpec("account_age_days", "account", 0, "count", 30.0, "Age of customer account in days"),
    FeatureSpec("merchant_risk_score", "merchant", 0, "avg", 0.1, "Merchant category risk score")
]

FEATURE_REGISTRY: Dict[str, FeatureSpec] = {spec.name: spec for spec in FEATURE_DEFINITIONS}

def get_feature_names() -> List[str]:
    """Returns list of all registered feature names in consistent order."""
    return [spec.name for spec in FEATURE_DEFINITIONS]

def get_default_feature_vector() -> Dict[str, float]:
    """Returns dictionary of default feature values for fallback/degraded mode."""
    return {spec.name: spec.default_value for spec in FEATURE_DEFINITIONS}
