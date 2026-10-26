import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("aegis_scoring_rules")

class DeterministicRulesEngine:
    """
    Deterministic Override Rules Engine for AegisFlow.
    Evaluates hard safety policies and compliance overrides (e.g. Sanctions, Impossible Travel)
    prior to or alongside machine learning score evaluation.
    """
    def __init__(self, sanctions_list: List[str] = None):
        self.sanctions_list = set(s.upper() for s in (sanctions_list or [
            "VLADIMIR PETROV",
            "OFAC_BLOCKED_ENTITY_99",
            "SANCTIONED_BANK_X",
            "GLOBAL_SHADOW_TRADING"
        ]))

    def evaluate_rules(self, tx: Dict[str, Any], features: Dict[str, float]) -> Tuple[List[str], str, float]:
        """
        Evaluates deterministic rules.
        Returns: (rule_hits, force_decision_override, override_probability)
        - force_decision_override can be 'DECLINE', 'REVIEW', or None.
        """
        rule_hits = []
        override_decision = None
        override_prob = 0.0

        # 1. Sanctions Policy Match (Hard DECLINE)
        source_name = str(tx.get("source_name", "")).upper()
        target_name = str(tx.get("target_name", "")).upper()
        merchant_name = str(tx.get("merchant_name", "")).upper()

        if any(s in source_name or s in target_name or s in merchant_name for s in self.sanctions_list):
            rule_hits.append("RULE_SANCTIONS_MATCH")
            override_decision = "DECLINE"
            override_prob = 1.0

        # 2. Impossible Travel Velocity Flag (Hard DECLINE or REVIEW)
        if features.get("impossible_travel_flag", 0.0) > 0:
            rule_hits.append("RULE_IMPOSSIBLE_TRAVEL")
            if override_decision != "DECLINE":
                override_decision = "DECLINE"
                override_prob = 0.95

        # 3. High Velocity Burst (High count in 1m)
        if features.get("tx_count_1m", 0.0) >= 5:
            rule_hits.append("RULE_HIGH_VELOCITY_BURST_1M")
            if not override_decision:
                override_decision = "REVIEW"
                override_prob = 0.80

        # 4. Shared Device Mass Account Ring
        if features.get("acct_count_per_device_24h", 1.0) >= 4:
            rule_hits.append("RULE_SHARED_DEVICE_FRAUD_RING")
            if not override_decision:
                override_decision = "REVIEW"
                override_prob = 0.82

        # 5. Shortest Path to Known Fraud <= 1 (Direct Neighbor of Known Fraud)
        if features.get("shortest_path_to_known_fraud", 99.0) <= 1.0:
            rule_hits.append("RULE_DIRECT_FRAUD_NEIGHBOR")
            if not override_decision:
                override_decision = "REVIEW"
                override_prob = 0.78

        return rule_hits, override_decision, override_prob
