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
    PredictRequest,
    PredictionOut,
    SpamTrendsResponse,
    JobResponse
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

    - Filter by spam/ham with `?is_spam=true/false`
    - Filter by date range with `?from_date=` and `?to_date=` (ISO format)
    - Empty data → returns empty CSV with headers (no error)
    - Large datasets are streamed efficiently
    """
    logger.info(
        "export │ user=%s │ is_spam=%s │ from=%s │ to=%s",
        current_user.username, is_spam, from_date, to_date,
    )

    csv_content = await export_user_predictions_csv(
        db,
        user_id   = current_user.id,
        is_spam   = is_spam,
        from_date = from_date,
        to_date   = to_date,
    )

    filename = f"smartinbox_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
