"""
app/routers/user.py
--------------------
User-facing endpoints: predict, batch-predict, batch-csv, history, spam-trends, export.
All routes require authentication (any role).
"""

import io
import time
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, Optional

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse

from app.auth.dependencies import CurrentUser, DBSession
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.prediction import (
    BatchCSVResponse,
    BatchPredictRequest,
    BatchPredictionOut,
    CSVRowResult,
    HistoryResponse,
    HistoryItem,
    PredictRequest,
    PredictionOut,
    SpamTrendsResponse,
    JobResponse,
    AiSpamAnalysisRequest,
    AiSpamAnalysisResponse,
    ThreatReportResponse
)
from app.services.job_service import job_service
from app.services.ml_service import MLService, translate_ml_error
from app.services.prediction_service import (
    export_user_predictions_csv,
    get_spam_trends,
    get_user_history,
    get_user_stats,
    store_prediction,
    process_prediction_job,
    process_batch_job
)
from app.schemas.notification import NotificationCreate
from app.services.notification_service import create_notification

router   = APIRouter(prefix="/user", tags=["User – Predictions"])
settings = get_settings()
logger   = get_logger("router.user")

# ── Constants ─────────────────────────────────────────────────────────────────
_MAX_CSV_BYTES  = 5 * 1024 * 1024   # 5 MB
_MAX_CSV_ROWS   = 1000
_UNCERTAINTY_MARGIN = 0.08           # |prob - threshold| < margin → UNCERTAIN


def _compute_verdict(probability: float, threshold: float) -> tuple[str, float]:
    """
    Return (verdict, confidence_score).
    - verdict: "SPAM" | "HAM" | "UNCERTAIN"
    - confidence: how far the prob is from the threshold (0-1 scale)
    """
    distance = abs(probability - threshold)
    if distance < _UNCERTAINTY_MARGIN:
        verdict = "UNCERTAIN"
    elif probability >= threshold:
        verdict = "SPAM"
    else:
        verdict = "HAM"
    confidence = round(min(distance / max(threshold, 1 - threshold), 1.0), 4)
    return verdict, confidence


# ── POST /user/predict ────────────────────────────────────────────────────────

@router.post(
    "/predict",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue classification for a single SMS",
)
async def predict(
    req:          PredictRequest,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    ml:           MLService,
) -> JobResponse:
    """
    Queue classification for a single SMS message.
    Returns a **job_id** immediately. Use `/jobs/{job_id}` to poll status.
    """
    job_id = job_service.create_job()
    background_tasks.add_task(
        process_prediction_job,
        job_id=job_id,
        user=current_user,
        text=req.text,
        ml_service=ml
    )
    
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Message queued for neural analysis."
    )


# ── POST /user/batch-predict (JSON) ──────────────────────────────────────────

@router.post(
    "/batch-predict",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue batch classification",
)
async def batch_predict(
    req:          BatchPredictRequest,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    ml:           MLService,
) -> JobResponse:
    """
    Queue classification for a **batch** of messages.
    Parallel chunks will be processed in the background.
    """
    job_id = job_service.create_job()
    background_tasks.add_task(
        process_batch_job,
        job_id=job_id,
        user=current_user,
        texts=req.texts,
        ml_service=ml
    )
    
    return JobResponse(
        job_id=job_id,
        status="pending",
        message=f"Batch of {len(req.texts)} messages queued."
    )


# ── POST /user/predict-batch-csv ──────────────────────────────────────────────

@router.post(
    "/predict-batch-csv",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue CSV batch classification",
)
async def predict_batch_csv(
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    ml:           MLService,
    file:         UploadFile = File(..., description="CSV file with a 'message' column"),
) -> JobResponse:
    """
    Upload a **CSV file** and queue all messages for classification.
    """
    # ── File type check ──────────────────────────────────────────────────────
    if file.content_type not in ("text/csv", "application/csv", "application/vnd.ms-excel") \
            and not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are accepted. Please upload a .csv file.",
        )

    # ── Read & size check ───────────────────────────────────────────────────
    contents = await file.read()
    if len(contents) > _MAX_CSV_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {_MAX_CSV_BYTES // 1024 // 1024} MB.",
        )

    # ── Parse CSV ───────────────────────────────────────────────────────────
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse CSV file: {exc}",
        )

    # Normalise column names
    df.columns = [c.strip().lower() for c in df.columns]
    col_map = {}
    for col in df.columns:
        if col in ("message", "text", "sms", "msg", "content"):
            col_map[col] = "message"
            break
    df = df.rename(columns=col_map)

    if "message" not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV must contain a 'message' column. Found columns: {list(df.columns)}",
        )

    if len(df) > _MAX_CSV_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many rows ({len(df)}). Maximum is {_MAX_CSV_ROWS} rows per upload.",
        )

    # Extract messages
    valid_messages = [str(m).strip() for m in df["message"].tolist() if str(m).strip() and str(m).lower() != "nan"]

    if not valid_messages:
        raise HTTPException(status_code=400, detail="No valid messages found in CSV.")

    job_id = job_service.create_job()
    background_tasks.add_task(
        process_batch_job,
        job_id=job_id,
        user=current_user,
        texts=valid_messages,
        ml_service=ml
    )

    return JobResponse(
        job_id=job_id,
        status="pending",
        message=f"CSV with {len(valid_messages)} messages queued for processing."
    )


# ── GET /user/history ─────────────────────────────────────────────────────────

@router.get(
    "/history",
    response_model=HistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve your prediction history",
)
async def get_history(
    current_user: CurrentUser,
    db:           DBSession,
    page:         Annotated[int,  Query(ge=1,               description="Page number")]         = 1,
    size:         Annotated[int,  Query(ge=1, le=100,       description="Items per page")]       = 20,
    is_spam:      Annotated[Optional[bool], Query(description="Filter: true=spam, false=ham")]      = None,
) -> HistoryResponse:
    """
    Return your paginated SMS classification history.

    Use `?is_spam=true` to filter for spam messages only,
    `?is_spam=false` for ham only.
    """
    return await get_user_history(db, current_user, page=page, size=size, is_spam=is_spam)


# ── GET /user/spam-trends ─────────────────────────────────────────────────────

@router.get(
    "/spam-trends",
    response_model=SpamTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Daily spam vs ham statistics for the past N days",
)
async def spam_trends(
    current_user: CurrentUser,
    db:           DBSession,
    days:         Annotated[int, Query(ge=1, le=365, description="Lookback window in days")] = 7,
) -> SpamTrendsResponse:
    """
    Return a time-series of daily spam / ham counts for the last `days` days.

    Useful for visualising spam detection trends over time.
    """
    return await get_spam_trends(db, current_user, days=days)


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Get user dashboard statistics",
)
async def user_stats(
    current_user: CurrentUser,
    db:           DBSession,
) -> Dict[str, Any]:
    """
    Return real-time statistics for the authenticated user's dashboard.
    Includes total scanned, spam blocked, threat level, and 24h trends.
    """
    return await get_user_stats(db, current_user)


# ── GET /user/export ─────────────────────────────────────────────────────────

@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export your prediction history as CSV",
    response_class=StreamingResponse,
)
async def export_history(
    current_user: CurrentUser,
    db:           DBSession,
    is_spam:      Annotated[Optional[bool], Query(description="Filter: true=spam only, false=ham only")] = None,
    from_date:    Annotated[Optional[datetime], Query(description="ISO datetime filter start")]          = None,
    to_date:      Annotated[Optional[datetime], Query(description="ISO datetime filter end")]            = None,
):
    """
    Export your SMS classification history as a downloadable **CSV file**.
    """
    logger.info("export │ user=%s │ is_spam=%s │ from=%s │ to=%s",
                current_user.username, is_spam, from_date, to_date)
    csv_content = await export_user_predictions_csv(
        db, user_id=current_user.id, is_spam=is_spam, from_date=from_date, to_date=to_date,
    )
    filename = f"smartinbox_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── POST /user/analyze-ai-spam ────────────────────────────────────────────────

@router.post(
    "/analyze-ai-spam",
    status_code=status.HTTP_200_OK,
    response_model=AiSpamAnalysisResponse,
    summary="Deep hybrid AI spam analysis (synchronous full pipeline)",
)
async def analyze_ai_spam(
    body:         AiSpamAnalysisRequest,
    current_user: CurrentUser,
    ml:           MLService,
) -> Dict[str, Any]:
    """
    Run the **full 4-layer hybrid pipeline** synchronously:
    - Layer 1: ML ensemble (RF + XGB + LightGBM + NB + LR)
    - Layer 2: Groq LLM semantic analysis
    - Layer 3: Heuristic + threat intelligence
    - Layer 4: Weighted ensemble decision

    Returns the complete intelligence report immediately (no job queue).
    """
    text = body.text.strip()

    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text must not be empty.")
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="text exceeds 2000 characters.")

    start_t = time.perf_counter()
    try:
        result = ml.predict(text)
    except Exception as exc:
        raise translate_ml_error(exc)
    latency_ms = round((time.perf_counter() - start_t) * 1000, 2)

    return {
        "text":                       text,
        "final_prediction":           result.get("final_prediction", "spam" if result["prediction"] == 1 else "ham"),
        "final_confidence":           result.get("final_confidence", round(result["probability"] * 100, 2)),
        "threat_level":               result.get("threat_level", "low"),
        "ml_model_score":             result.get("ml_model_score", round(result["probability"] * 100, 2)),
        "groq_semantic_score":        result.get("groq_semantic_score", 0.0),
        "heuristic_score":            result.get("heuristic_score", 0.0),
        "ai_generated_probability":   result.get("ai_generated_probability", 0.0),
        "phishing_probability":       result.get("phishing_probability", 0.0),
        "spam_type":                  result.get("spam_type", "ham"),
        "spam_type_confidence":       result.get("spam_type_confidence", 0.0),
        "spam_type_explanation":      result.get("spam_type_explanation", ""),
        "spam_scores":                result.get("spam_scores", {}),
        "detected_categories":        result.get("detected_categories", []),
        "reasoning":                  result.get("reasoning", ""),
        "recommended_action":         result.get("recommended_action", ""),
        "feature_importance":         result.get("feature_importance", []),
        "safe_for_user":              result.get("safe_for_user", result["prediction"] == 0),
        "groq_available":             result.get("groq_available", False),
        "latency_ms":                 latency_ms,
    }


# ── GET /user/threat-report ───────────────────────────────────────────────────

@router.get(
    "/threat-report",
    status_code=status.HTTP_200_OK,
    summary="Aggregated threat intelligence report from your history",
)
async def threat_report(
    current_user: CurrentUser,
    db:           DBSession,
    days:         Annotated[int, Query(ge=1, le=365, description="Lookback window")] = 30,
) -> Dict[str, Any]:
    """
    Aggregate threat intelligence from the user's prediction history.
    Returns breakdown by threat level, spam type, AI-generated count, etc.
    """
    from sqlalchemy import select, func, cast, Integer
    from app.models.prediction import Prediction
    from datetime import timedelta, timezone
    from app.services.cache_service import cache_manager

    cache_key = f"threat_report_{current_user.id}_{days}"
    cached = cache_manager.get(cache_key)
    if cached:
        return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # All predictions in window (with message join for text)
    from sqlalchemy.orm import selectinload
    stmt = select(Prediction).where(
        Prediction.user_id == current_user.id,
        Prediction.predicted_at >= since,
    ).options(selectinload(Prediction.message))
    rows = (await db.execute(stmt)).scalars().all()

    total = len(rows)
    threat_breakdown: Dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    type_breakdown: Dict[str, int] = {}
    ai_gen_count = 0
    phishing_count = 0
    category_counter: Dict[str, int] = {}

    for row in rows:
        tl = (row.threat_level or "low").lower()
        threat_breakdown[tl] = threat_breakdown.get(tl, 0) + 1
        st = row.spam_type or "unknown"
        type_breakdown[st] = type_breakdown.get(st, 0) + 1
        if (row.ai_generated_probability or 0) > 50:
            ai_gen_count += 1
        if (row.phishing_probability or 0) > 50:
            phishing_count += 1
        for cat in (row.detected_categories or []):
            category_counter[cat] = category_counter.get(cat, 0) + 1

    spam_count = sum(1 for r in rows if r.is_spam)
    risk_score = round(
        (threat_breakdown.get("critical", 0) * 1.0 +
         threat_breakdown.get("high", 0) * 0.7 +
         threat_breakdown.get("medium", 0) * 0.3) / max(total, 1) * 100, 2
    )

    if risk_score > 60:
        overall_threat = "critical"
    elif risk_score > 35:
        overall_threat = "high"
    elif risk_score > 15:
        overall_threat = "medium"
    else:
        overall_threat = "low"

    top_cats = sorted(
        [{"category": k, "count": v} for k, v in category_counter.items()],
        key=lambda x: x["count"], reverse=True
    )[:10]

    report = {
        "user_id":               str(current_user.id),
        "period_days":           days,
        "total_analyzed":        total,
        "spam_count":            spam_count,
        "ham_count":             total - spam_count,
        "threat_breakdown":      threat_breakdown,
        "spam_type_breakdown":   type_breakdown,
        "ai_generated_count":    ai_gen_count,
        "phishing_count":        phishing_count,
        "top_detected_categories": top_cats,
        "overall_threat_level":  overall_threat,
        "risk_score":            risk_score,
        "recent_threats": [
            HistoryItem(
                id             = r.id,
                text           = r.message.text,
                prediction     = r.prediction,
                probability    = r.probability,
                threshold_used = r.threshold_used,
                is_spam        = r.is_spam,
                predicted_at   = r.predicted_at,
                model_version  = r.model_version,
                spam_type      = r.spam_type,
                spam_type_confidence = r.spam_type_confidence,
                spam_type_explanation = r.spam_type_explanation,
                spam_scores    = {"ai_spam": r.ai_spam_score, "traditional_spam": r.traditional_spam_score, "ham": r.ham_score} if r.ai_spam_score is not None else None,
                threat_level               = r.threat_level,
                ai_generated_probability   = r.ai_generated_probability,
                phishing_probability       = r.phishing_probability,
                detected_categories        = r.detected_categories if isinstance(r.detected_categories, list) else None,
                reasoning                  = r.reasoning,
                recommended_action         = r.recommended_action
            )
            for r in rows[:5]
        ]
    }
    cache_manager.set(cache_key, report, ttl=120)
    return report
