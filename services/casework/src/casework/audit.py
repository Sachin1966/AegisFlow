import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger("aegis_casework_audit")

class ImmutableAuditWriter:
    """
    Append-only tamper-evident audit writer implementing the Outbox pattern.
    Every sensitive action (decisions, threshold updates, SAR approvals, dispositions)
    receives an immutable entry with SHA-256 hash chaining.
    """
    def __init__(self):
        self._entries: List[Dict[str, Any]] = []
        self._last_hash = "GENESIS_BLOCK_000000000000000000000000"

    def record_event(self, event_type: str, actor: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        ts = datetime.now(timezone.utc).isoformat()
        index = len(self._entries) + 1

        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        entry_hash = hashlib.sha256(
            f"{index}:{self._last_hash}:{event_type}:{actor}:{ts}:{payload_bytes}".encode("utf-8")
        ).hexdigest()

        entry = {
            "index": index,
            "event_type": event_type,
            "actor": actor,
            "payload": payload,
            "timestamp": ts,
            "prev_hash": self._last_hash,
            "entry_hash": entry_hash
        }

        self._entries.append(entry)
        self._last_hash = entry_hash
        logger.info(f"Audit event recorded: [{event_type}] by [{actor}] (hash: {entry_hash[:8]}...)")
        return entry

    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        return list(reversed(self._entries[-limit:]))

    def verify_integrity(self) -> bool:
        """Verifies hash chain validity across all audit records."""
        prev = "GENESIS_BLOCK_000000000000000000000000"
        for entry in self._entries:
            if entry["prev_hash"] != prev:
                return False
            payload_bytes = json.dumps(entry["payload"], sort_keys=True).encode("utf-8")
            expected_hash = hashlib.sha256(
                f"{entry['index']}:{entry['prev_hash']}:{entry['event_type']}:{entry['actor']}:{entry['timestamp']}:{payload_bytes}".encode("utf-8")
            ).hexdigest()
            if entry["entry_hash"] != expected_hash:
                return False
            prev = entry["entry_hash"]
        return True
