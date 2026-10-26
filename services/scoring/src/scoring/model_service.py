import os
import time
import json
import joblib
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List

from aegis_ml.features.definitions import get_feature_names, get_default_feature_vector
from aegis_ml.training.train_fraud import FastSHAPExplainer
from scoring.rules import DeterministicRulesEngine

logger = logging.getLogger("aegis_scoring_model_service")

class ScoringModelService:
    """
    Real-Time Scoring Model Service for AegisFlow.
    Orchestrates Rules Engine, XGBoost Champion, LightGBM Challenger (shadow),
    Isotonic Calibration, SHAP Reason Codes, and Degraded Fallback Mode.
    """
    def __init__(self, models_dir: str = "ml/models"):
        self.models_dir = models_dir
        self.feature_names = get_feature_names()
        self.rules_engine = DeterministicRulesEngine()
        
        self.champion = None
        self.challenger = None
        self.calibrator = None
        self.explainer = None
        self.version = "xgboost_v1.0"

        self._load_models()

    def _load_models(self):
        champ_path = os.path.join(self.models_dir, "champion_xgboost.joblib")
        chall_path = os.path.join(self.models_dir, "challenger_lightgbm.joblib")
        calib_path = os.path.join(self.models_dir, "calibrator.joblib")
        expl_path = os.path.join(self.models_dir, "explainer.joblib")

        if os.path.exists(champ_path):
            try:
                self.champion = joblib.load(champ_path)
                logger.info(f"Loaded XGBoost Champion Model from {champ_path}")
            except Exception as e:
                logger.error(f"Failed to load Champion model ({e})")

        if os.path.exists(chall_path):
            try:
                self.challenger = joblib.load(chall_path)
                logger.info(f"Loaded Challenger Model from {chall_path}")
            except Exception as e:
                logger.warning(f"Failed to load Challenger model ({e})")

        if os.path.exists(calib_path):
            try:
                self.calibrator = joblib.load(calib_path)
                logger.info("Loaded Isotonic Calibrator.")
            except Exception as e:
                logger.warning(f"Failed to load Calibrator ({e})")

        if os.path.exists(expl_path):
            try:
                self.explainer = joblib.load(expl_path)
                logger.info("Loaded SHAP Explainer.")
            except Exception as e:
                logger.warning(f"Failed to load SHAP Explainer ({e})")

        if self.explainer is None and self.champion is not None:
            self.explainer = FastSHAPExplainer(self.champion, self.feature_names)

    def score_transaction(self, tx: Dict[str, Any], features: Dict[str, float], degraded: bool = False) -> Dict[str, Any]:
        """
        Executes real-time scoring pipeline under strict latency constraints (target < 15ms).
        Returns decision dictionary with SHAP explanation reason codes.
        """
        start_time = time.time()

        # 1. Deterministic Rules Engine Evaluation
        rule_hits, rule_override, rule_prob = self.rules_engine.evaluate_rules(tx, features)

        # 2. ML Champion Model Inference
        raw_prob = 0.10
        calibrated_prob = 0.10

        if self.champion is not None:
            try:
                # Prepare single row DataFrame with exact feature order
                df_feat = pd.DataFrame([[features.get(col, 0.0) for col in self.feature_names]], columns=self.feature_names)
                raw_prob = float(self.champion.predict_proba(df_feat)[0, 1])

                if self.calibrator is not None:
                    calibrated_prob = float(self.calibrator.transform([raw_prob])[0])
                else:
                    calibrated_prob = raw_prob
            except Exception as e:
                logger.error(f"Error during champion model inference ({e})")
                degraded = True
                calibrated_prob = 0.50

        # 3. Challenger Model Shadow Inference (non-blocking)
        challenger_prob = None
        if self.challenger is not None:
            try:
                df_feat = pd.DataFrame([[features.get(col, 0.0) for col in self.feature_names]], columns=self.feature_names)
                challenger_prob = float(self.challenger.predict_proba(df_feat)[0, 1])
            except Exception:
                pass

        # 4. Final Probability & Decision Synthesis
        final_prob = calibrated_prob
        if rule_override is not None:
            final_prob = max(calibrated_prob, rule_prob)

        if rule_override == "DECLINE" or final_prob >= 0.85:
            decision = "DECLINE"
        elif rule_override == "REVIEW" or final_prob >= 0.65:
            decision = "REVIEW"
        else:
            decision = "APPROVE"

        # 5. SHAP Reason Codes Generation
        reason_codes = []
        if self.explainer is not None:
            try:
                top_reasons = self.explainer.get_top_reasons(features, top_k=5)
                for r in top_reasons:
                    fname = r["feature"]
                    val = r["value"]
                    score = r["impact_score"]
                    reason_codes.append({
                        "code": f"REASON_{fname.upper()}",
                        "feature": fname,
                        "value": val,
                        "impact": score,
                        "description": f"High risk contribution from {fname} (value: {val:.2f})"
                    })
            except Exception as e:
                logger.warning(f"SHAP reason code generation error ({e})")

        latency_ms = round((time.time() - start_time) * 1000.0, 2)

        return {
            "transaction_id": tx.get("id"),
            "decision": decision,
            "probability": round(final_prob, 4),
            "raw_probability": round(raw_prob, 4),
            "challenger_probability": round(challenger_prob, 4) if challenger_prob is not None else None,
            "rule_hits": rule_hits,
            "reason_codes": reason_codes,
            "latency_ms": latency_ms,
            "model_version": self.version,
            "degraded": degraded
        }
