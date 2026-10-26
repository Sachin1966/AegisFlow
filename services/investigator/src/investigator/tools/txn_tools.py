from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

def get_transaction_timeline(account_id: str, days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Retrieves chronological transaction timeline for subject entity
    with velocity and structuring indicators.
    """
    now = datetime.now(timezone.utc)
    base_events = [
        {
            "tx_id": "tx_7812a01",
            "timestamp": (now - timedelta(hours=48)).isoformat(),
            "amount": 9850.00,
            "currency": "USD",
            "channel": "mobile_app",
            "source": account_id,
            "counterparty": "ACCT-9011",
            "type": "deposit",
            "is_sub_threshold": True,
            "flag": "CTR_SUB_THRESHOLD"
        },
        {
            "tx_id": "tx_7812a02",
            "timestamp": (now - timedelta(hours=42)).isoformat(),
            "amount": 9600.00,
            "currency": "USD",
            "channel": "mobile_app",
            "source": account_id,
            "counterparty": "ACCT-9012",
            "type": "deposit",
            "is_sub_threshold": True,
            "flag": "CTR_SUB_THRESHOLD"
        },
        {
            "tx_id": "tx_7812a03",
            "timestamp": (now - timedelta(hours=36)).isoformat(),
            "amount": 9750.00,
            "currency": "USD",
            "channel": "mobile_app",
            "source": account_id,
            "counterparty": "ACCT-9013",
            "type": "deposit",
            "is_sub_threshold": True,
            "flag": "CTR_SUB_THRESHOLD"
        },
        {
            "tx_id": "tx_7812a04",
            "timestamp": (now - timedelta(hours=28)).isoformat(),
            "amount": 9900.00,
            "currency": "USD",
            "channel": "mobile_app",
            "source": account_id,
            "counterparty": "ACCT-9014",
            "type": "deposit",
            "is_sub_threshold": True,
            "flag": "CTR_SUB_THRESHOLD"
        },
        {
            "tx_id": "tx_7812a05",
            "timestamp": (now - timedelta(hours=14)).isoformat(),
            "amount": 39200.00,
            "currency": "USD",
            "channel": "wire_transfer",
            "source": account_id,
            "counterparty": "ACCT-COUNTERPART-1",
            "type": "consolidation_wire",
            "is_sub_threshold": False,
            "flag": "IMMEDIATE_LAYERING_OUTFLOW"
        }
    ]
    return base_events

def get_velocity_summary(account_id: str) -> Dict[str, Any]:
    """Computes summary velocity aggregates over sliding windows."""
    return {
        "account_id": account_id,
        "count_1h": 3,
        "amount_sum_1h": 29200.0,
        "count_24h": 8,
        "amount_sum_24h": 76400.0,
        "unique_devices_24h": 1,
        "unique_ips_24h": 2,
        "pass_through_ratio_24h": 0.98
    }
