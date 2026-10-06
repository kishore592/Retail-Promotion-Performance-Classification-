from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

class RiskBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class ValidationDecision(str, Enum):
    PASS = "PASS"
    RETRY = "RETRY"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCK = "BLOCK"

class ChatRequest(BaseModel):
    session_id: str
    user_id: str = "demo-user"
    query: str = Field(min_length=3, max_length=10000)

class TriageResult(BaseModel):
    intent: str
    category: str
    priority: str
    entities: dict[str, Any] = {}
    missing_information: list[str] = []
    confidence: float = Field(ge=0, le=1)
    recommended_route: str

class Promotion(BaseModel):
    promotion_id: str
    category: str
    product_id: str
    discount_pct: float = Field(ge=0, le=100)
    duration_days: int = Field(gt=0)
    expected_units: int = Field(gt=0)
    expected_margin_pct: float
    channel: str = "ONLINE"

class Finding(BaseModel):
    issue_type: str
    evidence: list[str]
    policy_reference: list[str]
    recommended_action: str
    confidence: float = Field(ge=0, le=1)
    requires_human_review: bool

class RiskClassification(BaseModel):
    risk_band: RiskBand
    probability_high_risk: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    reasons: list[str]
    recommended_action: str

class ValidationResult(BaseModel):
    decision: ValidationDecision
    checks: list[str]
    issues: list[str] = []

class ApprovalRequest(BaseModel):
    decision: str
    comment: str = ""

class AgentState(BaseModel):
    session_id: str
    user_id: str
    user_query: str
    conversation_history: list[dict[str, str]] = []
    intent: TriageResult | None = None
    promotion: Promotion | None = None
    retrieved_data: dict[str, Any] = {}
    retrieved_documents: list[dict[str, Any]] = []
    investigation_result: Finding | None = None
    classification: RiskClassification | None = None
    proposed_actions: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    confidence: float = 0.0
    validation_result: ValidationResult | None = None
    human_approval: dict[str, Any] | None = None
    errors: list[str] = []
    retry_count: int = 0
    workflow_id: str = ""
    final_response: str = ""
