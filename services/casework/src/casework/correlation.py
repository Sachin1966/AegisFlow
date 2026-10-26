import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone

class AlertCorrelationEngine:
    """
    Groups related alerts (same account, shared device, or fraud ring)
    into unified investigation cases with priority and SLA metrics.
    """
    def __init__(self):
        # Maps entity identifiers (account_id, device_id) to active case_ids
        self.entity_to_case_map: Dict[str, str] = {}

    def correlate_alert(self, alert: Dict[str, Any], existing_cases: List[Dict[str, Any]]) -> Tuple[str, bool]:
        """
        Determines whether alert belongs to an existing open case or creates a new case.
        Returns (case_id, is_new_case).
        """
        src = alert.get("source_account")
        dev = alert.get("device_id")

        matched_case_id = None
        if src and src in self.entity_to_case_map:
            matched_case_id = self.entity_to_case_map[src]
        elif dev and dev in self.entity_to_case_map:
            matched_case_id = self.entity_to_case_map[dev]

        # Verify if existing case is still open
        if matched_case_id:
            case_obj = next((c for c in existing_cases if c.get("case_id") == matched_case_id), None)
            if case_obj and case_obj.get("status") not in ("closed", "archived"):
                case_obj["alerts_count"] = case_obj.get("alerts_count", 0) + 1
                return matched_case_id, False

        # Open new case
        new_case_id = f"CASE-2026-{len(existing_cases) + 1:03d}"
        if src:
            self.entity_to_case_map[src] = new_case_id
        if dev:
            self.entity_to_case_map[dev] = new_case_id

        return new_case_id, True

def calculate_case_priority_and_sla(severity: str, amount: float, typology: str = "") -> Tuple[str, float, str]:
    """
    Calculates priority label (critical, high, medium, low), priority score (0.0 to 1.0),
    and SLA due timestamp.
    """
    now = datetime.now(timezone.utc)
    base_score = 0.50

    if severity == "critical" or "RING" in typology.upper() or amount > 50000.0:
        priority = "critical"
        score = 0.95
        sla_due = now + timedelta(hours=24)
    elif severity == "high" or amount > 10000.0 or "SMURFING" in typology.upper():
        priority = "high"
        score = 0.80
        sla_due = now + timedelta(hours=48)
    elif severity == "medium":
        priority = "medium"
        score = 0.60
        sla_due = now + timedelta(hours=72)
    else:
        priority = "low"
        score = 0.35
        sla_due = now + timedelta(days=7)

    return priority, score, sla_due.isoformat()
