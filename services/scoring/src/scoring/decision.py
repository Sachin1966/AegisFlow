import time
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone

logger = logging.getLogger("aegis_scoring_decision")

class DecisionEngine:
    """
    Cost-Sensitive Decision Engine.
    Combines calibrated model probabilities, deterministic rule overrides,
    and business cost matrix thresholds to render final transaction decisions:
    - APPROVE
    - REVIEW
    - DECLINE
    """
    def __init__(self, review_threshold: float = 0.65, decline_threshold: float = 0.85):
        self.review_threshold = review_threshold
        self.decline_threshold = decline_threshold
        self.fn_cost_usd = 500.0 # Expected loss of missing a fraudulent transaction
        self.fp_cost_usd = 15.0  # Operational & customer friction cost of false decline
        self.history = []
        self.last_config = None
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.updated_by = "system_default"

    def evaluate_decision(
        self,
        calibrated_prob: float,
        rule_override: Optional[str] = None,
        rule_prob: Optional[float] = None
    ) -> Tuple[str, float]:
        """
        Determines final decision:
        - If deterministic rule forces decline (e.g. Sanctions hit), returns DECLINE immediately.
        - Otherwise evaluates calibrated probability against active thresholds.
        """
        final_prob = calibrated_prob
        if rule_prob is not None:
            final_prob = max(calibrated_prob, rule_prob)

        if rule_override == "DECLINE" or final_prob >= self.decline_threshold:
            decision = "DECLINE"
        elif rule_override == "REVIEW" or final_prob >= self.review_threshold:
            decision = "REVIEW"
        else:
            decision = "APPROVE"

        return decision, round(final_prob, 4)

    def get_thresholds(self) -> Dict[str, Any]:
        return {
            "review_threshold": self.review_threshold,
            "decline_threshold": self.decline_threshold,
            "fn_cost_usd": self.fn_cost_usd,
            "fp_cost_usd": self.fp_cost_usd,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
            "rollback_available": self.last_config is not None
        }

    def update_thresholds(self, review_t: float, decline_t: float, updated_by: str = "risk_manager", reason: str = "") -> Dict[str, Any]:
        if decline_t <= review_t:
            raise ValueError("Decline threshold must be strictly greater than Review threshold")

        # Save previous config for instant 1-click rollback
        self.last_config = {
            "review_threshold": self.review_threshold,
            "decline_threshold": self.decline_threshold,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by
        }

        self.review_threshold = review_t
        self.decline_threshold = decline_t
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.updated_by = updated_by

        self.history.append({
            "action": "UPDATE_THRESHOLDS",
            "review_threshold": review_t,
            "decline_threshold": decline_t,
            "updated_by": updated_by,
            "reason": reason,
            "timestamp": self.updated_at
        })

        logger.info(f"Thresholds updated to Review={review_t}, Decline={decline_t} by {updated_by}")
        return self.get_thresholds()

    def rollback_thresholds(self, actor: str = "risk_manager") -> Dict[str, Any]:
        if not self.last_config:
            raise ValueError("No prior threshold configuration available to rollback")

        target = dict(self.last_config)
        self.last_config = None
        self.review_threshold = target["review_threshold"]
        self.decline_threshold = target["decline_threshold"]
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.updated_by = f"{actor} (ROLLBACK)"

        self.history.append({
            "action": "ROLLBACK_THRESHOLDS",
            "restored_config": target,
            "actor": actor,
            "timestamp": self.updated_at
        })

        logger.warning(f"Thresholds rolled back to Review={self.review_threshold}, Decline={self.decline_threshold}")
        return self.get_thresholds()
