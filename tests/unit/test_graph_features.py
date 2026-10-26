import pytest
import networkx as nx
from aegis_ml.features.graph_features import EntityGraphEngine

def test_entity_graph_engine_metrics():
    engine = EntityGraphEngine(db_url="sqlite:///:memory:", redis_url="redis://localhost:6379/0")
    
    # Manually populate graph
    g = engine.graph
    g.add_node("acct_01", type="account", is_fraud=False)
    g.add_node("acct_02", type="account", is_fraud=False)
    g.add_node("acct_03", type="account", is_fraud=True) # Fraud node!
    g.add_node("dev_01", type="device")

    g.add_edge("acct_01", "dev_01", edge_type="USED_DEVICE")
    g.add_edge("acct_02", "dev_01", edge_type="USED_DEVICE")
    g.add_edge("acct_02", "acct_03", edge_type="TRANSACTED_WITH")

    metrics = engine.compute_and_cache_metrics()

    assert "acct_01" in metrics
    assert "acct_02" in metrics
    assert "acct_03" in metrics

    # Component size = 4 (acct_01, dev_01, acct_02, acct_03)
    assert metrics["acct_01"]["connected_component_size"] == 4.0
    
    # Distance from acct_02 to fraud acct_03 = 1.0 hop
    assert metrics["acct_02"]["shortest_path_to_known_fraud"] == 1.0

    # Distance from acct_01 to fraud acct_03 = 3.0 hops (acct_01 -> dev_01 -> acct_02 -> acct_03)
    assert metrics["acct_01"]["shortest_path_to_known_fraud"] == 3.0

    # Test K-hop neighborhood extraction
    khop = engine.get_k_hop_neighborhood("acct_01", k=2)
    assert len(khop["nodes"]) == 3
    assert len(khop["edges"]) == 2
