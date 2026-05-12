"""
app/schemas/admin.py
--------------------
Pydantic schemas for admin-only endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Retrain ───────────────────────────────────────────────────────────────────

class RetrainRequest(BaseModel):
    n_estimators: int   = Field(300,  ge=50,  le=1000, description="Number of RF trees")
    test_size:    float = Field(0.20, gt=0.0, lt=0.5,  description="Hold-out fraction")
    seed:         int   = Field(42,                     description="Random seed")
    notes:        Optional[str] = Field(None, max_length=500)


class RetrainResponse(BaseModel):
    success:         bool
    new_model_path:  str
    new_version_tag: str
    metrics:         Dict[str, float]
    threshold:       float
    trained_at:      str
    message:         str


# ── Threshold ─────────────────────────────────────────────────────────────────

class UpdateThresholdRequest(BaseModel):
    threshold: float = Field(
        ..., gt=0.0, lt=1.0,
        description="New decision threshold, must be strictly between 0 and 1.",
        examples=[0.45],
    )
    reason: Optional[str] = Field(None, max_length=255)


class UpdateThresholdResponse(BaseModel):
    old_threshold: float
    new_threshold: float
    updated_at:    str


# ── Metrics ───────────────────────────────────────────────────────────────────

class MetricPoint(BaseModel):
    metric_name:  str
    metric_value: float
    split:        str
    recorded_at:  datetime

    model_config = {"from_attributes": True}


class MetricsResponse(BaseModel):
    model_version: str
    metrics:       List[MetricPoint]
    summary:       Dict[str, float]


# ── Model info ────────────────────────────────────────────────────────────────

class ModelInfoResponse(BaseModel):
    model_version:     str
    threshold:         float
    trained_at:        Optional[str] = "unknown"
    roc_auc:           Optional[float] = 0.0
    pr_auc:            Optional[float] = 0.0
    f1:                Optional[float] = 0.0
    accuracy:          Optional[float] = 0.0
    optimal_f1:        Optional[float] = 0.0
    optimal_threshold: Optional[float] = 0.5
    n_features:        Optional[int] = 0
    n_estimators:      Optional[int] = 0
    is_ensemble:       bool = False
    groq_enabled:      bool = False


# ── Feature importance ────────────────────────────────────────────────────────

class FeatureImportanceItem(BaseModel):
    rank:       int
    feature:    str
    importance: float


class FeatureImportanceResponse(BaseModel):
    model_version: str
    features:      List[FeatureImportanceItem]


# ── Model versions ────────────────────────────────────────────────────────────

class ModelVersionOut(BaseModel):
    id:          uuid.UUID
    version_tag: str
    is_active:   bool
    roc_auc:     Optional[float]
    pr_auc:      Optional[float]
    f1:          Optional[float]
    accuracy:    Optional[float]
    threshold:   Optional[float]
    created_at:  datetime
    notes:       Optional[str]

    model_config = {"from_attributes": True}


# ── User management ───────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id:               uuid.UUID
    username:         str
    email:            str
    role:             str
    is_active:        bool
    created_at:       datetime
    last_login:       Optional[datetime]
    prediction_count: int = 0
    spam_count:       int = 0
    ham_count:        int = 0

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    total:   int
    page:    int
    size:    int
    items:   List[UserOut]


class UserUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    role:      Optional[str]  = None


# ── Analytics ─────────────────────────────────────────────────────────────────

class AnalyticsDailyPoint(BaseModel):
    date:       str
    total:      int
    spam_count: int
    ham_count:  int
    spam_rate:  float


class GlobalAnalyticsResponse(BaseModel):
    total_messages:     int
    total_spam:         int
    total_ham:          int
    spam_percentage:    float
    ham_percentage:     float
    total_users:        int
    active_users:       int
    recent_activity:    List[AnalyticsDailyPoint]
    model_version:      str
    last_refreshed_at:  str
