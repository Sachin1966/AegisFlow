from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ScoreRequest(BaseModel):
    transaction: Dict[str, Any]
    features: Dict[str, float]
    degraded: Optional[bool] = False

class ReasonCode(BaseModel):
    code: str
    feature: str
    value: float
    impact: float
    description: str

class DecisionResponse(BaseModel):
    transaction_id: Optional[str] = None
    decision: str
    probability: float
    raw_probability: float
    challenger_probability: Optional[float] = None
    rule_hits: List[str]
    reason_codes: List[ReasonCode]
    latency_ms: float
    model_version: str
    degraded: bool

class ThresholdConfig(BaseModel):
    review_threshold: float = Field(..., ge=0.0, le=1.0)
    decline_threshold: float = Field(..., ge=0.0, le=1.0)
    fn_cost_usd: float = 500.0
    fp_cost_usd: float = 15.0
    updated_at: str
    updated_by: str
    rollback_available: bool = False

class ThresholdUpdateRequest(BaseModel):
    review_threshold: float = Field(..., ge=0.0, le=1.0)
    decline_threshold: float = Field(..., ge=0.0, le=1.0)
    reason: Optional[str] = "Manual threshold adjustment"
    updated_by: Optional[str] = "risk_manager"
