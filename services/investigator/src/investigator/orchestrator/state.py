from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class RingFinding(BaseModel):
    target_account: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    connected_component_size: int
    shortest_path_to_known_fraud: List[str]
    distance_to_known_fraud: int
    confidence: float = 0.95

class PatternFinding(BaseModel):
    target_account: str
    matched_typologies: List[str]
    typology_details: Dict[str, Any]
    sub_threshold_amount_total: float
    pass_through_ratio: float
    confidence: float = 0.92

class MediaFinding(BaseModel):
    query: str
    articles: List[Dict[str, Any]]
    key_allegations: List[str]
    confidence: float = 0.94

class SARSection(BaseModel):
    title: str
    content: str
    citations: List[str]

class SARDraft(BaseModel):
    case_id: str
    version: int = 1
    subject_entity: str
    suspicious_activity_amount: float
    detected_typologies: List[str]
    narrative_sections: List[SARSection]
    full_narrative_md: str
    evidence_citations: List[Dict[str, Any]]
    requires_human_signoff: bool = True

class QAVerdict(BaseModel):
    status: str # PASSED, REVISION_REQUIRED
    coverage_score: float # 0.0 to 1.0 (faithfulness)
    unbacked_claims: List[str] = []
    feedback: str
    attempts: int = 1

class CaseState(BaseModel):
    case_id: str
    target_account_id: str
    current_agent: str = "Supervisor"
    steps_log: List[Dict[str, Any]] = []
    
    # Specialist outputs
    ring_finding: Optional[RingFinding] = None
    pattern_finding: Optional[PatternFinding] = None
    media_finding: Optional[MediaFinding] = None
    sar_draft: Optional[SARDraft] = None
    qa_verdict: Optional[QAVerdict] = None
    
    # Workflow metadata
    turns_count: int = 0
    max_turns: int = 12
    completed: bool = False
    error: Optional[str] = None
