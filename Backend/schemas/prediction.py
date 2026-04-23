"""
app/schemas/prediction.py
-------------------------
Pydantic schemas for prediction endpoints.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str = "Job queued for background processing."


# ── Requests ──────────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        examples=["Congratulations! You have won £1000. Call 09061701939 NOW!"],
        description="Raw SMS message text to classify.",
    )

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank or whitespace-only.")
        return v.strip()


class BatchPredictRequest(BaseModel):
    texts: List[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=[["Free prize!", "See you at 7 for dinner"]],
        description="List of SMS messages (max 100 per request).",
    )

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

class PredictionOut(BaseModel):
    id:             uuid.UUID
    text:           str
    prediction:     int     = Field(..., description="0 = HAM, 1 = SPAM")
    probability:    float   = Field(..., description="P(spam) in [0, 1]")
    threshold_used: float
    is_spam:        bool
    verdict:        str     = Field(..., description='"SPAM", "HAM", or "UNCERTAIN"')
    confidence:     Optional[float] = Field(None, description="Distance from threshold (0-1)")
    latency_ms:     float
    model_version:  str
    predicted_at:   datetime

    model_config = {"from_attributes": True}


class BatchPredictionOut(BaseModel):
    total:     int
    spam:      int
    ham:       int
    uncertain: int = 0
    results:   List[PredictionOut]


# ── CSV Batch Upload ──────────────────────────────────────────────────────────

class CSVRowResult(BaseModel):
    row:        int
    message:    str
    verdict:    Optional[str]  = None   # "SPAM" | "HAM" | "UNCERTAIN"
    probability: Optional[float] = None
    confidence:  Optional[float] = None
    is_spam:     Optional[bool]  = None
    error:        Optional[str]  = None   # set if row failed
    skipped:      bool            = False  # empty/blank row


class BatchCSVResponse(BaseModel):
    total_rows:     int
    processed:      int
    skipped:        int
    errors:         int
    spam_count:     int
    ham_count:      int
    uncertain_count: int
    results:        List[CSVRowResult]
    download_token: Optional[str] = None  # future: streaming token


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

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    total:   int
    page:    int
    size:    int
    items:   List[HistoryItem]


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
