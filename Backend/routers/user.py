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
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.auth.dependencies import CurrentUser, DBSession
from app.core.config import get_settings
from app.core.logging import get_logger
from app.database import AsyncSessionLocal
from app.schemas.prediction import (
    BatchCSVResponse,
    BatchPredictRequest,
    BatchPredictionOut,
    CSVRowResult,
    HistoryResponse,
    PredictRequest,
    PredictionOut,
    SpamTrendsResponse,
)
from app.services.ml_service import MLService, translate_ml_error
from app.services.prediction_service import (
    export_user_predictions_csv,
    get_spam_trends,
    get_user_history,
    get_user_stats,
    store_prediction,
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


async def _create_notif_bg(notif: NotificationCreate):
    async with AsyncSessionLocal() as session:
        await create_notification(session, notif)


# ── POST /user/predict ────────────────────────────────────────────────────────

@router.post(
    "/predict",
    response_model=PredictionOut,
    status_code=status.HTTP_200_OK,
    summary="Classify a single SMS message",
)
async def predict(
    req:          PredictRequest,
    current_user: CurrentUser,
    db:           DBSession,
    ml:           MLService,
    background_tasks: BackgroundTasks,
) -> PredictionOut:
    """
    Classify a single SMS message as **spam** or **ham**.

    Returns:
    - **prediction**: `0` (ham) or `1` (spam)
    - **probability**: raw P(spam) from the model
    - **threshold_used**: decision threshold applied
    - **verdict**: `"SPAM"`, `"HAM"`, or `"UNCERTAIN"` (if confidence is low)
    - **confidence**: distance from decision boundary (0–1)
    """
    start = time.perf_counter()
    try:
        result = ml.predict(req.text)
    except Exception as exc:
        raise translate_ml_error(exc)
    latency_ms = (time.perf_counter() - start) * 1000

    verdict, confidence = _compute_verdict(result["probability"], result["threshold_used"])

    logger.info(
        "predict │ user=%s │ verdict=%s │ prob=%.4f │ conf=%.4f",
        current_user.username, verdict, result["probability"], confidence,
    )

    pred = await store_prediction(
        db, current_user, text=req.text, ml_result=result,
        latency_ms=latency_ms, model_version=ml._model_version
    )
    
    if verdict == "SPAM":
        notif = NotificationCreate(
            user_id=current_user.id,
            title="Spam Threat Blocked",
            message=f"Neural core intercepted a malicious message: '{req.text[:50]}...'",
            type="security"
        )
        background_tasks.add_task(_create_notif_bg, notif)

    await db.commit()
    await db.refresh(pred)

    return PredictionOut(
        id             = pred.id,
        text           = req.text,
        prediction     = pred.prediction,
        probability    = pred.probability,
        threshold_used = pred.threshold_used,
        is_spam        = pred.is_spam,
        verdict        = verdict,
        confidence     = confidence,
        latency_ms     = pred.latency_ms,
        model_version  = pred.model_version,
        predicted_at   = pred.predicted_at,
    )


# ── POST /user/batch-predict (JSON) ──────────────────────────────────────────

@router.post(
    "/batch-predict",
    response_model=BatchPredictionOut,
    status_code=status.HTTP_200_OK,
    summary="Classify up to 100 SMS messages in one call",
)
async def batch_predict(
    req:          BatchPredictRequest,
    current_user: CurrentUser,
    db:           DBSession,
    ml:           MLService,
) -> BatchPredictionOut:
    """
    Classify a **batch** of SMS messages (max 100).
    Messages are processed in a single vectorised pass for efficiency.
    All results are persisted to the database.
    """
    start = time.perf_counter()
    try:
        results = ml.batch_predict(req.texts)
    except Exception as exc:
        raise translate_ml_error(exc)
    elapsed = (time.perf_counter() - start) * 1000

    logger.info(
        "batch_predict │ user=%s │ n=%d │ spam=%d",
        current_user.username,
        len(results),
        sum(1 for r in results if r["prediction"] == 1),
    )

    predictions_out = []
    uncertain_count  = 0
    for i, result in enumerate(results):
        verdict, confidence = _compute_verdict(result["probability"], result["threshold_used"])
        if verdict == "UNCERTAIN":
            uncertain_count += 1
        latency_ms = result.get("_latency_ms", round(elapsed / len(results), 2))
        pred = await store_prediction(
            db, current_user, text=req.texts[i], ml_result=result,
            latency_ms=latency_ms, model_version=ml._model_version
        )
        await db.flush()
        await db.refresh(pred)

        predictions_out.append(PredictionOut(
            id             = pred.id,
            text           = req.texts[i],
            prediction     = pred.prediction,
            probability    = pred.probability,
            threshold_used = pred.threshold_used,
            is_spam        = pred.is_spam,
            verdict        = verdict,
            confidence     = confidence,
            latency_ms     = pred.latency_ms,
            model_version  = pred.model_version,
            predicted_at   = pred.predicted_at,
        ))

    await db.commit()

    spam_count = sum(1 for p in predictions_out if p.is_spam)
    return BatchPredictionOut(
        total     = len(predictions_out),
        spam      = spam_count,
        ham       = len(predictions_out) - spam_count,
        uncertain = uncertain_count,
        results   = predictions_out,
    )


# ── POST /user/predict-batch-csv ──────────────────────────────────────────────

@router.post(
    "/predict-batch-csv",
    response_model=BatchCSVResponse,
    status_code=status.HTTP_200_OK,
    summary="Classify SMS messages uploaded via CSV file",
)
async def predict_batch_csv(
    current_user: CurrentUser,
    db:           DBSession,
    ml:           MLService,
    file:         UploadFile = File(..., description="CSV file with a 'message' column"),
) -> BatchCSVResponse:
    """
    Upload a **CSV file** and classify all messages in it.

    **CSV format**: must contain a column named `message` (other columns ignored).

    **Limits**:
    - File must be `.csv` (Content-Type or extension checked)
    - Max file size: 5 MB
    - Max rows: 1,000

    **Handles**:
    - Empty rows → skipped
    - Partial failures per row → recorded in `error` field
    - Corrupted CSV → 400 error
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

    logger.info(
        "predict_batch_csv │ user=%s │ rows=%d │ file=%s",
        current_user.username, len(df), file.filename,
    )

    # ── Process rows ─────────────────────────────────────────────────────────
    row_results: list[CSVRowResult] = []
    skipped_count = 0
    error_count   = 0
    spam_count    = 0
    ham_count     = 0
    uncertain_count = 0

    # Collect non-empty messages for batch vectorisation
    valid_indices: list[int] = []
    valid_messages: list[str] = []

    for i, row_val in enumerate(df["message"]):
        msg = str(row_val).strip() if pd.notna(row_val) else ""
        if not msg or msg.lower() in ("nan", "none", ""):
            row_results.append(CSVRowResult(row=i + 1, message="", skipped=True))
            skipped_count += 1
        else:
            valid_indices.append(i)
            valid_messages.append(msg)
            row_results.append(CSVRowResult(row=i + 1, message=msg))  # placeholder

    # Batch predict all valid messages
    if valid_messages:
        try:
            ml_results = ml.batch_predict(valid_messages)
        except Exception as exc:
            # Total batch failure — mark all as errors
            for idx, vi in enumerate(valid_indices):
                row_results[vi].error = f"Model error: {exc}"
                error_count += 1
            ml_results = []

        # Map results back to rows
        for idx, (vi, result) in enumerate(zip(valid_indices, ml_results)):
            try:
                verdict, confidence = _compute_verdict(result["probability"], result["threshold_used"])
                row_results[vi].verdict     = verdict
                row_results[vi].probability = round(result["probability"], 4)
                row_results[vi].confidence  = confidence
                row_results[vi].is_spam     = result["prediction"] == 1

                if verdict == "SPAM":
                    spam_count += 1
                elif verdict == "HAM":
                    ham_count += 1
                else:
                    uncertain_count += 1

                # Persist to DB (best-effort; don't fail the whole batch)
                try:
                    pred = await store_prediction(
                        db, current_user,
                        text=valid_messages[idx],
                        ml_result=result,
                        latency_ms=result.get("_latency_ms", 0),
                        model_version=ml._model_version,
                    )
                    await db.flush()
                except Exception as db_exc:
                    logger.warning("DB store failed for row %d: %s", vi + 1, db_exc)

            except Exception as row_exc:
                row_results[vi].error = str(row_exc)
                error_count += 1

    # Commit all stored predictions
    try:
        await db.commit()
    except Exception as commit_exc:
        logger.error("Batch CSV commit failed: %s", commit_exc)
        await db.rollback()

    processed = len(valid_messages) - error_count

    return BatchCSVResponse(
        total_rows      = len(df),
        processed       = processed,
        skipped         = skipped_count,
        errors          = error_count,
        spam_count      = spam_count,
        ham_count       = ham_count,
        uncertain_count = uncertain_count,
        results         = row_results,
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
