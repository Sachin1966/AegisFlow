import os
import argparse
import pandas as pd
import numpy as np
from typing import Tuple

def prepare_ieee_dataset(raw_dir: str, processed_dir: str, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    ETL Pipeline for IEEE-CIS Fraud Detection dataset.
    Strictly performs time-based train/test splitting on 'TransactionDT' to prevent temporal leakage.
    """
    os.makedirs(processed_dir, exist_ok=True)
    identity_path = os.path.join(raw_dir, "train_identity.csv")
    transaction_path = os.path.join(raw_dir, "train_transaction.csv")

    if os.path.exists(transaction_path):
        print(f"Loading IEEE-CIS raw files from {raw_dir}...")
        df_trans = pd.read_csv(transaction_path)
        if os.path.exists(identity_path):
            df_id = pd.read_csv(identity_path)
            df = pd.merge(df_trans, df_id, on="TransactionID", how="left")
        else:
            df = df_trans
    else:
        print(f"Raw IEEE-CIS files not found at {raw_dir}. Creating benchmark synthetic IEEE-CIS structure...")
        np.random.seed(42)
        n_samples = 10000
        df = pd.DataFrame({
            "TransactionID": np.arange(1000000, 1000000 + n_samples),
            "isFraud": np.random.binomial(1, p=0.035, size=n_samples),
            "TransactionDT": np.sort(np.random.randint(86400, 86400 * 180, size=n_samples)), # 180 days timestamp
            "TransactionAmt": np.round(np.random.lognormal(mean=4.0, sigma=1.0, size=n_samples), 2),
            "ProductCD": np.random.choice(["W", "C", "R", "H", "S"], size=n_samples),
            "card1": np.random.randint(1000, 15000, size=n_samples),
            "card2": np.random.randint(100, 600, size=n_samples),
            "card4": np.random.choice(["visa", "mastercard", "discover", "american express"], size=n_samples),
            "card6": np.random.choice(["debit", "credit"], size=n_samples),
            "addr1": np.random.randint(100, 500, size=n_samples),
            "P_emaildomain": np.random.choice(["gmail.com", "yahoo.com", "anonymous.com", "hotmail.com"], size=n_samples),
            "C1": np.random.poisson(lam=1.5, size=n_samples),
            "C2": np.random.poisson(lam=2.0, size=n_samples),
            "D1": np.random.randint(0, 500, size=n_samples),
            "V1": np.random.binomial(1, p=0.9, size=n_samples),
            "V2": np.random.binomial(1, p=0.9, size=n_samples),
        })

    # Strict Time-Based Split (Do NOT shuffle!)
    df = df.sort_values(by="TransactionDT").reset_index(drop=True)
    split_idx = int(len(df) * (1.0 - test_size))
    
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    train_path = os.path.join(processed_dir, "train.parquet")
    test_path = os.path.join(processed_dir, "test.parquet")

    train_df.to_parquet(train_path, index=False)
    test_df.to_parquet(test_path, index=False)

    print(f"ETL Complete: Saved {len(train_df)} train samples to {train_path}")
    print(f"ETL Complete: Saved {len(test_df)} test samples to {test_path}")

    return train_df, test_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IEEE-CIS Fraud Dataset ETL")
    parser.add_argument("--raw-dir", default="data/raw/ieee-cis")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    prepare_ieee_dataset(args.raw_dir, args.processed_dir, args.test_size)
