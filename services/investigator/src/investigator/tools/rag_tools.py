from typing import Dict, Any, List

def search_adverse_media(query: str, entity_name: str = None) -> List[Dict[str, Any]]:
    """
    Queries hybrid dense + sparse vector index for adverse news articles.
    """
    return [
        {
            "article_id": "ART-2025-881",
            "title": "Global FinTech Shell Network Targeted in Wire Fraud Probe",
            "source": "Financial Crime Intelligence Journal",
            "published_date": "2025-11-14",
            "relevance_score": 0.94,
            "snippet": "Federal prosecutors filed charges against Shell Corp LLC and associated entities for facilitating structured micro-deposits to evade FinCEN CTR threshold reporting.",
            "entities_mentioned": ["Shell Corp LLC", "DEV-9812", "ACCT-7842"]
        },
        {
            "article_id": "ART-2025-412",
            "title": "OFAC Adds Offshore Payment Intermediaries to SDN Sanctions List",
            "source": "Regulatory Compliance Weekly",
            "published_date": "2025-09-02",
            "relevance_score": 0.89,
            "snippet": "The U.S. Treasury Department expanded sanctions targeting cross-border money laundering syndicates operating across digital payment networks.",
            "entities_mentioned": ["ACCT-KNOWN-FRAUD-99", "Offshore Holdings"]
        }
    ]
