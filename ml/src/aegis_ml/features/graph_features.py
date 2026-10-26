import os
import networkx as nx
import redis
from typing import Dict, Any, List, Set
from sqlalchemy import create_engine, text

class EntityGraphEngine:
    """
    NetworkX Entity Graph Processing Engine for AegisFlow.
    Calculates graph topology metrics, PageRank risk scores, shortest paths to known fraud,
    and caches results into Redis `gfeat:acct:{id}`.
    """
    def __init__(self, db_url: str = None, redis_url: str = None):
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "postgresql://aegis_user:aegis_password_secure@localhost:5432/aegisflow_db")
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        self.db_url = db_url
        self.redis_url = redis_url
        self.graph = nx.Graph()

    def build_graph_from_db(self):
        """Constructs NetworkX Graph from PostgreSQL entity_edges & transactions."""
        print("Building entity graph from PostgreSQL entity_edges & transactions...")
        self.graph.clear()
        engine = create_engine(self.db_url)
        
        with engine.connect() as conn:
            # 1. Load Entity Edges
            edge_rows = conn.execute(text("SELECT source_id, source_type, target_id, target_type, edge_type, weight FROM entity_edges")).fetchall()
            for src_id, src_t, tgt_id, tgt_t, e_type, weight in edge_rows:
                self.graph.add_node(src_id, type=src_t)
                self.graph.add_node(tgt_id, type=tgt_t)
                self.graph.add_edge(src_id, tgt_id, edge_type=e_type, weight=float(weight))

            # 2. Load Transaction edges between accounts
            tx_rows = conn.execute(text("SELECT source_account_id, target_account_id FROM transactions WHERE target_account_id IS NOT NULL")).fetchall()
            for src_acct, tgt_acct in tx_rows:
                self.graph.add_node(src_acct, type="account")
                self.graph.add_node(tgt_acct, type="account")
                self.graph.add_edge(src_acct, tgt_acct, edge_type="TRANSACTED_WITH", weight=1.0)

            # 3. Load Known Fraudulent Nodes from ground_truth_labels
            fraud_rows = conn.execute(text("""
                SELECT t.source_account_id 
                FROM transactions t 
                JOIN ground_truth_labels g ON t.id = g.transaction_id 
                WHERE g.is_fraud = true
            """)).fetchall()
            
            fraud_nodes: Set[str] = set(row[0] for row in fraud_rows)
            for n in self.graph.nodes():
                self.graph.nodes[n]["is_fraud"] = (n in fraud_nodes)

        print(f"Entity Graph Built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")


    def compute_and_cache_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        Computes component sizes, shortest paths to fraud, PageRank risk scores,
        and caches results in Redis under `gfeat:acct:{id}`.
        """
        if self.graph.number_of_nodes() == 0:
            self.build_graph_from_db()

        print("Computing Graph Metrics (Connected Components, PageRank, Shortest Path to Fraud)...")
        fraud_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("is_fraud", False)]

        # PageRank Risk Score
        try:
            pagerank_scores = nx.pagerank(self.graph, alpha=0.85)
        except Exception:
            pagerank_scores = {n: 0.001 for n in self.graph.nodes()}

        # Connected Components
        component_sizes = {}
        for comp in nx.connected_components(self.graph):
            c_size = len(comp)
            for node in comp:
                component_sizes[node] = c_size

        account_metrics = {}
        account_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "account" or str(n).startswith("acct_")]

        for acct_id in account_nodes:
            c_size = component_sizes.get(acct_id, 1)
            pr_score = pagerank_scores.get(acct_id, 0.001)

            # Shortest Path to Known Fraud
            min_dist = 99.0
            if fraud_nodes:
                for fn in fraud_nodes:
                    if fn == acct_id:
                        min_dist = 0.0
                        break
                    if nx.has_path(self.graph, acct_id, fn):
                        try:
                            path_len = nx.shortest_path_length(self.graph, acct_id, fn)
                            if path_len < min_dist:
                                min_dist = float(path_len)
                        except nx.NetworkXNoPath:
                            pass

            propagated_risk = round(1.0 / (min_dist + 1.0), 3) if min_dist < 99.0 else 0.0

            metrics = {
                "connected_component_size": float(c_size),
                "shortest_path_to_known_fraud": min_dist,
                "distance_to_known_fraud": min_dist,
                "propagated_risk_score": propagated_risk,
                "pagerank_risk_score": round(float(pr_score), 5)
            }
            account_metrics[acct_id] = metrics

        # Cache in Redis
        try:
            r = redis.Redis.from_url(self.redis_url, decode_responses=True)
            pipe = r.pipeline()
            for acct_id, metrics in account_metrics.items():
                gkey = f"gfeat:acct:{acct_id}"
                pipe.hset(gkey, mapping={k: str(v) for k, v in metrics.items()})
                pipe.expire(gkey, 86400) # Cache for 24h
            pipe.execute()
            print(f"Successfully cached graph metrics for {len(account_metrics)} accounts in Redis.")
        except Exception as e:
            print(f"Warning: Could not cache graph metrics in Redis ({e})")

        return account_metrics

    def get_k_hop_neighborhood(self, node_id: str, k: int = 2) -> Dict[str, Any]:
        """Returns k-hop sub-graph centered around `node_id` for visualization and Link Analyst tools."""
        if node_id not in self.graph:
            return {"nodes": [], "edges": []}

        sub_nodes = set([node_id])
        current_layer = set([node_id])
        for _ in range(k):
            next_layer = set()
            for n in current_layer:
                next_layer.update(self.graph.neighbors(n))
            sub_nodes.update(next_layer)
            current_layer = next_layer

        subgraph = self.graph.subgraph(sub_nodes)
        
        nodes_out = [{"id": n, "label": n, "type": self.graph.nodes[n].get("type", "unknown")} for n in subgraph.nodes()]
        edges_out = [{"source": u, "target": v, "type": subgraph.edges[u, v].get("edge_type", "CONNECTED")} for u, v in subgraph.edges()]

        return {"nodes": nodes_out, "edges": edges_out}
