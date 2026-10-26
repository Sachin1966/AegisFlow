import numpy as np
import pandas as pd
from typing import Dict, Any, List

def evaluate_cohort_fairness(df: pd.DataFrame, group_col: str, pred_col: str = "decision", favorable_outcome: str = "APPROVE") -> Dict[str, Any]:
    """
    Evaluates disparate impact ratio and approval parity across sensitive cohorts
    (e.g., channel, geography, merchant category) to meet regulatory non-discrimination standards.
    Standard: Disparate Impact Ratio >= 0.80 (Four-Fifths Rule).
    """
    if group_col not in df.columns or pred_col not in df.columns:
        return {"status": "SKIPPED", "reason": f"Column {group_col} or {pred_col} not found"}

    cohort_stats = {}
    favorable_rates = {}

    for cohort, group in df.groupby(group_col):
        total = len(group)
        favorable_count = (group[pred_col] == favorable_outcome).sum()
        favorable_rate = float(favorable_count / total) if total > 0 else 0.0
        favorable_rates[str(cohort)] = favorable_rate
        cohort_stats[str(cohort)] = {
            "total_transactions": total,
            "favorable_count": int(favorable_count),
            "approval_rate": round(favorable_rate, 4)
        }

    # Highest favorable rate serves as baseline
    if not favorable_rates:
        return {"status": "NO_DATA"}

    max_cohort = max(favorable_rates, key=favorable_rates.get)
    max_rate = favorable_rates[max_cohort]

    disparate_impact_ratios = {}
    passed_audit = True

    for cohort, rate in favorable_rates.items():
        ratio = round(rate / max_rate, 4) if max_rate > 0 else 1.0
        disparate_impact_ratios[cohort] = ratio
        if ratio < 0.80:
            passed_audit = False

    return {
        "group_column": group_col,
        "baseline_cohort": max_cohort,
        "cohort_approval_rates": cohort_stats,
        "disparate_impact_ratios": disparate_impact_ratios,
        "four_fifths_rule_compliant": passed_audit,
        "audit_verdict": "PASS" if passed_audit else "REVIEW_REQUIRED"
    }
