"""
app/models/prediction.py  —  predictions table (v8 hybrid intelligence)
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sms_messages.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True,
    )

    # Core prediction ─────────────────────────────────────────────────────
    prediction:     Mapped[int]   = mapped_column(Integer, nullable=False)
    probability:    Mapped[float] = mapped_column(Float,   nullable=False)
    threshold_used: Mapped[float] = mapped_column(Float,   nullable=False)
    is_spam:        Mapped[bool]  = mapped_column(Boolean, nullable=False)
    latency_ms:     Mapped[float] = mapped_column(Float,   nullable=True)
    model_version:  Mapped[str]   = mapped_column(String(50), nullable=False, default="v8")

    # Multi-class spam type (v7+) ─────────────────────────────────────────
    spam_type:             Mapped[Optional[str]]   = mapped_column(String(50),  nullable=True)
    spam_type_confidence:  Mapped[Optional[float]] = mapped_column(Float,       nullable=True)
    spam_type_explanation: Mapped[Optional[str]]   = mapped_column(String(500), nullable=True)
    ai_spam_score:         Mapped[Optional[float]] = mapped_column(Float,       nullable=True)
    traditional_spam_score: Mapped[Optional[float]] = mapped_column(Float,      nullable=True)
    ham_score:             Mapped[Optional[float]] = mapped_column(Float,       nullable=True)

    # Hybrid intelligence (v8+) ───────────────────────────────────────────
    threat_level:              Mapped[Optional[str]]   = mapped_column(String(20),  nullable=True)
    ai_generated_probability:  Mapped[Optional[float]] = mapped_column(Float,       nullable=True)
    phishing_probability:      Mapped[Optional[float]] = mapped_column(Float,       nullable=True)
    ml_model_score:            Mapped[Optional[float]] = mapped_column(Float,       nullable=True)
    groq_semantic_score:       Mapped[Optional[float]] = mapped_column(Float,       nullable=True)
    heuristic_score:           Mapped[Optional[float]] = mapped_column(Float,       nullable=True)
    detected_categories:       Mapped[Optional[list]]  = mapped_column(JSON,        nullable=True)
    reasoning:                 Mapped[Optional[str]]   = mapped_column(String(1000),nullable=True)
    recommended_action:        Mapped[Optional[str]]   = mapped_column(String(500), nullable=True)
    groq_available:            Mapped[Optional[bool]]  = mapped_column(Boolean,     nullable=True)

    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    user:    Mapped["User"]       = relationship("User",       back_populates="predictions")
    message: Mapped["SMSMessage"] = relationship("SMSMessage", back_populates="prediction")

    def __repr__(self) -> str:
        return f"<Prediction id={self.id} is_spam={self.is_spam} prob={self.probability:.3f} threat={self.threat_level}>"
