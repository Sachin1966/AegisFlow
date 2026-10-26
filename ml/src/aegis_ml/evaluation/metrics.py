import json
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    f1_score
)

def compute_model_metrics(y_true: np.ndarray, y_prob: np.ndarray, review_threshold: float = 0.65, decline_threshold: float = 0.85) -> Dict[str, Any]:
    """
    Computes comprehensive evaluation metrics, PR-AUC, ROC-AUC,
    and decision breakdown under specified review/decline thresholds.
    """
    roc_auc = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.5
    pr_auc = float(average_precision_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.0

    # Categorize Decisions
    decisions = []
    for prob in y_prob:
        if prob >= decline_threshold:
            decisions.append("DECLINE")
        elif prob >= review_threshold:
            decisions.append("REVIEW")
        else:
            decisions.append("APPROVE")

    dec_counts = pd.Series(decisions).value_counts().to_dict()

    y_pred_binary = (y_prob >= review_threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred_binary).tolist()

    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "review_threshold": review_threshold,
        "decline_threshold": decline_threshold,
        "decision_counts": dec_counts,
        "confusion_matrix": cm,
        "total_evaluated": len(y_true)
    }

def find_optimal_thresholds(y_true: np.ndarray, y_prob: np.ndarray, fn_cost: float = 500.0, fp_cost: float = 15.0) -> Tuple[float, float]:
    """
    Calculates cost-optimal decision thresholds minimizing financial loss.
    Loss = FN * fn_cost + FP * fp_cost.
    """
    thresholds = np.linspace(0.1, 0.95, 86)
    min_cost = float("inf")
    best_review = 0.65
    best_decline = 0.85

    for t_rev in thresholds:
        for t_dec in thresholds:
            if t_dec <= t_rev:
                continue
            
            # Predict
            preds = (y_prob >= t_rev).astype(int)
            fn = np.sum((y_true == 1) & (preds == 0))
            fp = np.sum((y_true == 0) & (preds == 1))
            
            total_cost = fn * fn_cost + fp * fp_cost
            if total_cost < min_cost:
                min_cost = total_cost
                best_review = float(t_rev)
                best_decline = float(t_dec)

    return round(best_review, 2), round(best_decline, 2)

if __name__ == "__main__":
    y_true = np.random.binomial(1, 0.05, 1000)
    y_prob = np.random.beta(0.5, 5.0, 1000)
    metrics = compute_model_metrics(y_true, y_prob)
    print("Evaluation Metrics Sample:", json.dumps(metrics, indent=2))
