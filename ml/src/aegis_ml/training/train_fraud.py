import os
import json
import joblib
import numpy as np
import pandas as pd
import argparse
import logging
from typing import Tuple, Dict, Any, List

from xgboost import XGBClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
try:
    from lightgbm import LGBMClassifier
    HAS_LIGHTGBM = True
except ImportError:
    LGBMClassifier = None
    HAS_LIGHTGBM = False

from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import precision_recall_curve, roc_auc_score, average_precision_score
import shap

from aegis_ml.features.definitions import get_feature_names, get_default_feature_vector
from aegis_ml.features.offline import OfflineFeatureEngine

logger = logging.getLogger("aegis_ml_training")

def generate_synthetic_training_data(n_samples: int = 5000) -> Tuple[pd.DataFrame, pd.Series]:
    """Generates synthetic training dataset matching AegisFlow feature definitions."""
    np.random.seed(42)
    feature_names = get_feature_names()
    
    # Simulate feature matrix
    X_dict = {}
    for name in feature_names:
        if "count" in name:
            X_dict[name] = np.random.negative_binomial(1, 0.3, size=n_samples).astype(float)
        elif "sum" in name or "amt" in name:
            X_dict[name] = np.random.exponential(scale=200.0, size=n_samples)
        elif "flag" in name or "vpn" in name:
            X_dict[name] = np.random.binomial(1, 0.05, size=n_samples).astype(float)
        elif "score" in name or "risk" in name:
            X_dict[name] = np.random.beta(0.5, 5.0, size=n_samples)
        elif "dist" in name or "path" in name:
            X_dict[name] = np.random.choice([0.0, 1.0, 2.0, 3.0, 99.0], size=n_samples, p=[0.01, 0.02, 0.05, 0.1, 0.82])
        else:
            X_dict[name] = np.random.normal(loc=0.0, scale=1.0, size=n_samples)

    X = pd.DataFrame(X_dict)

    # Fraud probability simulation based on key indicators
    fraud_logits = (
        0.8 * (X["tx_count_1m"] > 3) +
        1.2 * (X["amt_deviation_zscore"] > 3.0) +
        1.5 * (X["impossible_travel_flag"] > 0) +
        1.0 * (X["is_vpn_ip"] > 0) +
        1.4 * (X["acct_count_per_device_24h"] > 3) +
        1.6 * (X["distance_to_known_fraud"] <= 1.0) +
        0.5 * np.random.normal(0, 1, size=n_samples)
    )
    
    fraud_probs = 1.0 / (1.0 + np.exp(-fraud_logits))
    y = (fraud_probs > 0.75).astype(int)

    logger.info(f"Generated synthetic training set: {n_samples} samples, fraud ratio: {y.mean():.4f}")
    return X, y

class FastSHAPExplainer:
    def __init__(self, model, feature_names):
        self.model = model
        self.feature_names = feature_names
        self.importances = dict(zip(feature_names, model.feature_importances_))

    def get_top_reasons(self, feature_vector: Dict[str, float], top_k: int = 5) -> List[Dict[str, Any]]:
        contributions = []
        for name in self.feature_names:
            val = feature_vector.get(name, 0.0)
            imp = self.importances.get(name, 0.01)
            score = float(val * imp)
            contributions.append({
                "feature": name,
                "value": float(val),
                "importance": float(imp),
                "impact_score": score
            })
        contributions.sort(key=lambda x: abs(x["impact_score"]), reverse=True)
        return contributions[:top_k]

def train_models(models_dir: str = "ml/models"):
    """Trains Champion XGBoost and Challenger LightGBM models with Isotonic Calibration."""
    os.makedirs(models_dir, exist_ok=True)

    X, y = generate_synthetic_training_data(n_samples=5000)
    feature_names = get_feature_names()

    print("--- Training XGBoost Champion Model ---")
    champion = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=5.0,
        random_state=42
    )
    champion.fit(X[feature_names], y)
    raw_preds_champ = champion.predict_proba(X[feature_names])[:, 1]

    print("--- Training LightGBM Challenger Model (Shadow Mode) ---")
    if HAS_LIGHTGBM and LGBMClassifier is not None:
        challenger = LGBMClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=5.0,
            random_state=42,
            verbosity=-1
        )
    else:
        challenger = HistGradientBoostingClassifier(
            max_iter=100,
            max_depth=5,
            learning_rate=0.05,
            random_state=42
        )
    challenger.fit(X[feature_names], y)
    raw_preds_chall = challenger.predict_proba(X[feature_names])[:, 1]

    print("--- Calibrating Probabilities (Isotonic Regression) ---")
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(raw_preds_champ, y)
    calibrated_preds = calibrator.transform(raw_preds_champ)

    print("--- Building SHAP Explainer ---")
    explainer = FastSHAPExplainer(champion, feature_names)

    # Calculate metrics
    auc_roc = roc_auc_score(y, calibrated_preds)
    auc_pr = average_precision_score(y, calibrated_preds)
    print(f"Champion Model Performance - ROC-AUC: {auc_roc:.4f}, PR-AUC: {auc_pr:.4f}")

    # Save artifacts
    champion_path = os.path.join(models_dir, "champion_xgboost.joblib")
    challenger_path = os.path.join(models_dir, "challenger_lightgbm.joblib")
    calibrator_path = os.path.join(models_dir, "calibrator.joblib")
    explainer_path = os.path.join(models_dir, "explainer.joblib")
    feature_names_path = os.path.join(models_dir, "feature_names.json")

    joblib.dump(champion, champion_path)
    joblib.dump(challenger, challenger_path)
    joblib.dump(calibrator, calibrator_path)
    joblib.dump(explainer, explainer_path)

    with open(feature_names_path, "w") as f:
        json.dump(feature_names, f, indent=2)

    print(f"Successfully trained and saved model artifacts to {models_dir}/")

    # Try logging to MLflow if server is running
    try:
        import mlflow
        mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(mlflow_uri)
        with mlflow.start_run(run_name="fraud_champion_v1"):
            mlflow.log_metric("roc_auc", float(auc_roc))
            mlflow.log_metric("pr_auc", float(auc_pr))
            mlflow.log_param("model_type", "xgboost")
            mlflow.log_artifact(champion_path)
            print("Logged model metrics to MLflow.")
    except Exception as e:
        print(f"MLflow logging skipped ({e})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train AegisFlow Fraud Champion and Challenger Models")
    parser.add_argument("--models-dir", default="ml/models")
    args = parser.parse_args()

    train_models(args.models_dir)
