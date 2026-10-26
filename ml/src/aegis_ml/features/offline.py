import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Any
from aegis_ml.features.definitions import FEATURE_DEFINITIONS, get_feature_names, get_default_feature_vector

class OfflineFeatureEngine:
    """
    Offline Feature Generator for AegisFlow model training datasets.
    Computes point-in-time correct features from historical transaction DataFrames.
    """
    def __init__(self, df_transactions: pd.DataFrame):
        # Ensure DataFrame is sorted chronologically by timestamp
        self.df = df_transactions.sort_values(by="timestamp").reset_index(drop=True).copy()
        if "timestamp" in self.df.columns and not pd.api.types.is_datetime64_any_dtype(self.df["timestamp"]):
            self.df["timestamp"] = pd.to_datetime(self.df["timestamp"], utc=True)

    def extract_features_for_transaction(self, idx: int) -> Dict[str, float]:
        """
        Extracts point-in-time correct features for transaction at index `idx`.
        Only looks at transactions with index < `idx` (strictly prior events).
        """
        current_row = self.df.iloc[idx]
        current_time = current_row["timestamp"]
        source_acct = current_row["source_account_id"]
        dev_id = current_row.get("device_id")
        ip_id = current_row.get("ip_id")
        amount = current_row["amount"]

        # Filter strictly prior transactions
        prior_df = self.df.iloc[:idx]

        features = get_default_feature_vector()

        if prior_df.empty:
            return features

        # Account Prior History
        acct_prior = prior_df[prior_df["source_account_id"] == source_acct]

        # 1. Velocity Features
        for window_sec, name_suffix in [(60, "1m"), (3600, "1h"), (86400, "24h"), (604800, "7d")]:
            cutoff_time = current_time - pd.Timedelta(seconds=window_sec)
            window_df = acct_prior[acct_prior["timestamp"] >= cutoff_time]
            
            features[f"tx_count_{name_suffix}"] = float(len(window_df))
            if name_suffix in ["1h", "24h"]:
                features[f"amt_sum_{name_suffix}"] = float(window_df["amount"].sum()) if not window_df.empty else 0.0

        # Unique counterparties / merchants in windows
        cutoff_1h = current_time - pd.Timedelta(seconds=3600)
        cutoff_24h = current_time - pd.Timedelta(seconds=86400)
        
        window_1h = acct_prior[acct_prior["timestamp"] >= cutoff_1h]
        window_24h = acct_prior[acct_prior["timestamp"] >= cutoff_24h]

        if not window_1h.empty and "target_account_id" in window_1h.columns:
            features["unique_counterparties_1h"] = float(window_1h["target_account_id"].dropna().nunique())
        if not window_24h.empty and "merchant_id" in window_24h.columns:
            features["unique_merchants_24h"] = float(window_24h["merchant_id"].dropna().nunique())

        # 2. Behavioral Features
        cutoff_30d = current_time - pd.Timedelta(days=30)
        window_30d = acct_prior[acct_prior["timestamp"] >= cutoff_30d]
        if not window_30d.empty:
            mean_amt = float(window_30d["amount"].mean())
            std_amt = float(window_30d["amount"].std()) if len(window_30d) > 1 else 1.0
            if std_amt == 0.0 or np.isnan(std_amt):
                std_amt = 1.0
            features["acct_avg_amt_30d"] = mean_amt
            features["amt_deviation_zscore"] = float((amount - mean_amt) / std_amt)

        # 3. Device & IP Features
        if dev_id and "device_id" in prior_df.columns:
            dev_prior_24h = prior_df[(prior_df["device_id"] == dev_id) & (prior_df["timestamp"] >= cutoff_24h)]
            features["acct_count_per_device_24h"] = float(dev_prior_24h["source_account_id"].nunique()) if not dev_prior_24h.empty else 1.0

        if ip_id and "ip_id" in prior_df.columns:
            ip_prior_24h = prior_df[(prior_df["ip_id"] == ip_id) & (prior_df["timestamp"] >= cutoff_24h)]
            features["acct_count_per_ip_24h"] = float(ip_prior_24h["source_account_id"].nunique()) if not ip_prior_24h.empty else 1.0

        return features

    def compute_all_feature_matrix(self) -> pd.DataFrame:
        """Computes feature matrix for all rows in DataFrame."""
        print(f"Computing point-in-time offline features for {len(self.df)} transactions...")
        feature_rows = []
        for i in range(len(self.df)):
            feats = self.extract_features_for_transaction(i)
            feature_rows.append(feats)
        return pd.DataFrame(feature_rows)
