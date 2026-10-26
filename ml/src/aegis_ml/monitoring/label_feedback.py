import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger("aegis_ml_feedback")

class LabelFeedbackLoop:
    """
    Closes the human-in-the-loop ML cycle:
    Analyst case dispositions (fraud / not_fraud) flow back as verified ground-truth
    labels for scheduled model retraining.
    """
    def __init__(self, feedback_store_path: str = "data/disposition_labels.jsonl"):
        self.feedback_store_path = feedback_store_path
        os.makedirs(os.path.dirname(self.feedback_store_path), exist_ok=True)

    def record_disposition(self, case_id: str, account_id: str, disposition: str, rationale: str, analyst: str) -> Dict[str, Any]:
        """
        Records human analyst disposition:
        - 'fraud' / 'sar_filed' -> label 1
        - 'not_fraud' -> label 0
        """
        binary_label = 1 if disposition in ("fraud", "sar_filed") else 0
        record = {
            "case_id": case_id,
            "account_id": account_id,
            "disposition": disposition,
            "binary_label": binary_label,
            "rationale": rationale,
            "analyst": analyst,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }

        with open(self.feedback_store_path, "a") as f:
            f.write(json.dumps(record) + "\n")

        logger.info(f"Recorded analyst disposition label for case {case_id}: label={binary_label}")
        return record

    def get_labeled_batch(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Reads recent feedback labels for dataset assembly."""
        if not os.path.exists(self.feedback_store_path):
            return []

        labels = []
        with open(self.feedback_store_path, "r") as f:
            for line in f:
                if line.strip():
                    labels.append(json.loads(line.strip()))
        return labels[-limit:]
