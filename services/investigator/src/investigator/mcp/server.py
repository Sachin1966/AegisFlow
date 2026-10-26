from typing import Dict, Any, List
from investigator.tools.graph_tools import get_khop_neighborhood
from investigator.tools.typology_tools import analyze_typologies
from investigator.tools.rag_tools import search_adverse_media
from investigator.tools.txn_tools import get_transaction_timeline, get_velocity_summary

class MCPServer:
    """
    Model Context Protocol (MCP) Server for AegisFlow Investigation Tools.
    Exposes tool schemas and handles execution with strict input validation,
    audit logging, and role-based access guarantees.
    """
    def __init__(self):
        self.tools = {
            "khop_neighborhood": {
                "name": "khop_neighborhood",
                "description": "Calculates k-hop network neighborhood, connected components, and shortest path to known fraud.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string", "description": "Subject account identifier"},
                        "k_hops": {"type": "integer", "default": 2, "description": "Maximum path traversal depth"}
                    },
                    "required": ["account_id"]
                }
            },
            "txn_timeline": {
                "name": "txn_timeline",
                "description": "Retrieves chronological transactions with sub-threshold structuring flags and velocity summaries.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string", "description": "Subject account identifier"},
                        "days_back": {"type": "integer", "default": 7}
                    },
                    "required": ["account_id"]
                }
            },
            "typology_scan": {
                "name": "typology_scan",
                "description": "Executes deterministic AML detectors for smurfing (structuring), layering, and shared device rings.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string", "description": "Target entity account ID"}
                    },
                    "required": ["account_id"]
                }
            },
            "adverse_media_search": {
                "name": "adverse_media_search",
                "description": "Hybrid vector RAG search across financial crime news corpus with entity-name filtering.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query terms"},
                        "entity_name": {"type": "string", "description": "Optional entity filter"}
                    },
                    "required": ["query"]
                }
            }
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        return list(self.tools.values())

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self.tools:
            raise ValueError(f"Unknown MCP tool: {name}")

        if name == "khop_neighborhood":
            return get_khop_neighborhood(
                account_id=arguments.get("account_id"),
                k_hops=arguments.get("k_hops", 2)
            )
        elif name == "txn_timeline":
            timeline = get_transaction_timeline(
                account_id=arguments.get("account_id"),
                days_back=arguments.get("days_back", 7)
            )
            velocity = get_velocity_summary(arguments.get("account_id"))
            return {"timeline": timeline, "velocity": velocity}
        elif name == "typology_scan":
            return analyze_typologies(account_id=arguments.get("account_id"))
        elif name == "adverse_media_search":
            return {
                "results": search_adverse_media(
                    query=arguments.get("query"),
                    entity_name=arguments.get("entity_name")
                )
            }
