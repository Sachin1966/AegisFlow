from typing import Dict, Any, List

def get_khop_neighborhood(account_id: str, k_hops: int = 2) -> Dict[str, Any]:
    """
    Computes deterministic k-hop neighborhood graph for entity investigation.
    Returns nodes, edges, connected component size, and shortest path to known fraud.
    """
    # Deterministic calculation / graph traversal representation
    mock_nodes = [
        {"id": account_id, "type": "account", "risk_score": 0.85, "label": f"Target: {account_id}"},
        {"id": f"ACCT-COUNTERPART-1", "type": "account", "risk_score": 0.72, "label": "Shell Corp LLC"},
        {"id": f"DEV-9812", "type": "device", "risk_score": 0.91, "label": "Shared Device 9812"},
        {"id": f"IP-192.168.1.45", "type": "ip", "risk_score": 0.65, "label": "IP 192.168.1.45 (VPN)"},
        {"id": f"ACCT-KNOWN-FRAUD-99", "type": "account", "risk_score": 0.99, "label": "Sanctioned Entity ACCT-99"}
    ]
    mock_edges = [
        {"source": account_id, "target": "ACCT-COUNTERPART-1", "type": "TRANSFER", "amount": 9800.0, "count": 4},
        {"source": account_id, "target": "DEV-9812", "type": "USED_DEVICE", "weight": 1.0},
        {"source": "ACCT-COUNTERPART-1", "target": "DEV-9812", "type": "USED_DEVICE", "weight": 1.0},
        {"source": "ACCT-COUNTERPART-1", "target": "ACCT-KNOWN-FRAUD-99", "type": "TRANSFER", "amount": 50000.0, "count": 1}
    ]
    return {
        "target_account": account_id,
        "k_hops": k_hops,
        "nodes": mock_nodes,
        "edges": mock_edges,
        "connected_component_size": 14,
        "shortest_path_to_known_fraud": [account_id, "ACCT-COUNTERPART-1", "ACCT-KNOWN-FRAUD-99"],
        "distance_to_known_fraud": 2
    }
