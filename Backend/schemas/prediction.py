"""
app/schemas/prediction.py
-------------------------
Pydantic schemas for prediction endpoints — v8 hybrid intelligence.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str = "Job queued for background processing."


# ── Requests ──────────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000,
                      examples=["Congratulations! You have won £1000. Call NOW!"],
                      description="Raw SMS message text to classify.")

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank.")
        return v.strip()


class BatchPredictRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=100,
                             examples=[["Free prize!", "See you at 7"]],
                             description="List of SMS messages (max 100).")

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: List[str]) -> List[str]:
        cleaned = [t.strip() for t in v if t.strip()]
        if not cleaned:
            raise ValueError("texts must contain at least one non-blank message.")
        if len(cleaned) > 100:
            raise ValueError("Maximum batch size is 100 messages.")
        return cleaned


# ── Responses ─────────────────────────────────────────────────────────────────

class SpamScores(BaseModel):
    ai_spam:          float = Field(..., description="AI spam score (0-10)")
    traditional_spam: float = Field(..., description="Traditional spam score (0-10)")
    ham:              float = Field(..., description="Ham score (0-10)")


class HybridIntelligence(BaseModel):
    """Full 4-layer hybrid analysis output."""
    final_prediction:          str            = Field(..., description='"spam" | "ham"')
    final_confidence:          float          = Field(..., description="Confidence 0-100")
    threat_level:              str            = Field(..., description='"low"|"medium"|"high"|"critical"')
    ml_model_score:            float          = Field(..., description="ML ensemble score 0-100")
    groq_semantic_score:       float          = Field(..., description="Groq LLM score 0-100")
    heuristic_score:           float          = Field(..., description="Heuristic score 0-100")
    ai_generated_probability:  float          = Field(..., description="AI-gen probability 0-100")
    phishing_probability:      float          = Field(..., description="Phishing probability 0-100")
    detected_categories:       List[str]      = Field(default_factory=list)
    reasoning:                 str            = Field(..., description="LLM or heuristic reasoning")
    recommended_action:        str            = Field(..., description="What user should do")
    feature_importance:        List[Dict[str, Any]] = Field(default_factory=list)
    safe_for_user:             bool
    groq_available:            bool           = False


class PredictionOut(BaseModel):
    id:             uuid.UUID
    text:           str
    prediction:     int     = Field(..., description="0 = HAM, 1 = SPAM")
    probability:    float   = Field(..., description="Final hybrid probability [0,1]")
    threshold_used: float
    is_spam:        bool
    verdict:        str     = Field(..., description='"SPAM"|"HAM"|"UNCERTAIN"')
    confidence:     Optional[float] = None
    latency_ms:     float
    model_version:  str
    predicted_at:   datetime
    # Spam type
    spam_type:               Optional[str]   = None
    spam_type_confidence:    Optional[float] = None
    spam_type_explanation:   Optional[str]   = None
    spam_scores:             Optional[SpamScores] = None
    # Hybrid intelligence
    threat_level:             Optional[str]  = None
    ai_generated_probability: Optional[float] = None
    phishing_probability:     Optional[float] = None
    ml_model_score:           Optional[float] = None
    groq_semantic_score:      Optional[float] = None
    heuristic_score:          Optional[float] = None
    detected_categories:      Optional[List[str]] = None
    reasoning:                Optional[str]  = None
    recommended_action:       Optional[str]  = None
    feature_importance:       Optional[List[Dict[str, Any]]] = None
    safe_for_user:            Optional[bool] = None
    groq_available:           Optional[bool] = None

    model_config = {"from_attributes": True}


class BatchPredictionOut(BaseModel):
    total:     int
    spam:      int
    ham:       int
    uncertain: int = 0
    results:   List[PredictionOut]


# ── CSV Batch Upload ──────────────────────────────────────────────────────────

class CSVRowResult(BaseModel):
    row:                  int
    message:              str
    verdict:              Optional[str]   = None
    probability:          Optional[float] = None
    confidence:           Optional[float] = None
    is_spam:              Optional[bool]  = None
    spam_type:            Optional[str]   = None
    spam_type_confidence: Optional[float] = None
    threat_level:         Optional[str]   = None
    error:                Optional[str]   = None
    skipped:              bool = False


class BatchCSVResponse(BaseModel):
    total_rows:      int
    processed:       int
    skipped:         int
    errors:          int
    spam_count:      int
    ham_count:       int
    uncertain_count: int
    results:         List[CSVRowResult]
    download_token:  Optional[str] = None


# ── History ───────────────────────────────────────────────────────────────────

class HistoryItem(BaseModel):
    id:             uuid.UUID
    text:           str
    prediction:     int
    probability:    float
    threshold_used: float
    is_spam:        bool
    predicted_at:   datetime
    model_version:  str
    spam_type:               Optional[str]   = None
    spam_type_confidence:    Optional[float] = None
    spam_type_explanation:   Optional[str]   = None
    spam_scores:             Optional[SpamScores] = None
    threat_level:            Optional[str]   = None
    ai_generated_probability: Optional[float] = None
    phishing_probability:    Optional[float] = None
    detected_categories:     Optional[List[str]] = None
    reasoning:               Optional[str]   = None
    recommended_action:      Optional[str]   = None

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    total:  int
    page:   int
    size:   int
    items:  List[HistoryItem]


# ── Spam trends ────────────────────────────────────────────────────────────────

class TrendPoint(BaseModel):
    date:       str
    total:      int
    spam_count: int
    ham_count:  int
    spam_rate:  float


class SpamTrendsResponse(BaseModel):
    period:  str
    points:  List[TrendPoint]


# ── AI Spam Analysis (direct sync endpoint) ────────────────────────────────────

class AiSpamAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000,
                      description="Message to analyze with full 4-layer pipeline.")

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank.")
        return v.strip()


class AiSpamAnalysisResponse(BaseModel):
    text:                      str
    final_prediction:          str
    final_confidence:          float
    threat_level:              str
    ml_model_score:            float
    groq_semantic_score:       float
    heuristic_score:           float
    ai_generated_probability:  float
    phishing_probability:      float
    spam_type:                 str
    spam_type_confidence:      float
    spam_type_explanation:     str
    detected_categories:       List[str]
    reasoning:                 str
    recommended_action:        str
    feature_importance:        List[Dict[str, Any]]
    safe_for_user:             bool
    groq_available:            bool
    latency_ms:                float


# ── Threat Report ──────────────────────────────────────────────────────────────

class ThreatReportResponse(BaseModel):
    user_id:               str
    period_days:           int
    total_analyzed:        int
    spam_count:            int
    ham_count:             int
    threat_breakdown:      Dict[str, int]
    spam_type_breakdown:   Dict[str, int]
    ai_generated_count:    int
    phishing_count:        int
    top_detected_categories: List[Dict[str, Any]]
    overall_threat_level:  str
    risk_score:            float
    recent_threats:        List[HistoryItem] = []
