"""
app/services/prediction_service.py
-----------------------------------
Business logic for prediction storage, history retrieval, spam trends,
CSV export, and admin-wide analytics.
"""

import csv
import io
from datetime import datetime, timedelta, timezone
import time
from typing import Any, AsyncIterator, Dict, List, Optional
import uuid

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.prediction import Prediction
from app.models.sms_message import SMSMessage
from app.models.user import User
from app.schemas.prediction import HistoryItem, HistoryResponse, TrendPoint, SpamTrendsResponse
from app.services.cache_service import cache_manager
from app.services.job_service import job_service, JobStatus
import asyncio

logger = get_logger("prediction_service")


async def process_prediction_job(
    job_id: str,
    user: User,
    text: str,
    ml_service: Any
):
    """Background task for single message prediction."""
    try:
        # Input Validation
        if not text or not text.strip():
            job_service.update_job(job_id, status=JobStatus.FAILED, error="Empty input payload.")
            return

        job_service.update_job(job_id, status=JobStatus.PROCESSING, progress=10)
        
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            # 1. ML Inference with timeout safety
            start_t = time.perf_counter()
            try:
                ml_result = ml_service.predict(text)
            except Exception as ml_exc:
                logger.error(f"ML Inference Error: {ml_exc}")
                job_service.update_job(job_id, status=JobStatus.FAILED, error="Neural core execution error.")
                return

            latency = (time.perf_counter() - start_t) * 1000
            
            job_service.update_job(job_id, progress=50)
            
            # 2. Store in DB
            pred = await store_prediction(
                db=db,
                user=user,
                text=text,
                ml_result=ml_result,
                latency_ms=latency,
                model_version=ml_service._model_version
            )
            await db.commit()
            
            job_service.update_job(
                job_id, 
                status=JobStatus.COMPLETED, 
                progress=100, 
                result={"prediction_id": str(pred.id), "is_spam": pred.is_spam, "probability": pred.probability}
            )
    except Exception as e:
        logger.error(f"Prediction job {job_id} failed: {e}")
        job_service.update_job(job_id, status=JobStatus.FAILED, error=str(e))

async def process_batch_job(
    job_id: str,
    user: User,
    texts: List[str],
    ml_service: Any,
    chunk_size: int = 50
):
    """Background task for high-throughput batch processing."""
    try:
        job_service.update_job(job_id, status=JobStatus.PROCESSING, progress=5)
        
        # Split into chunks
        chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]
        total_chunks = len(chunks)
        
        from app.database import AsyncSessionLocal
        
        async def process_chunk(chunk_texts, chunk_idx):
            async with AsyncSessionLocal() as db:
                batch_res = ml_service.batch_predict(chunk_texts)
                
                # Store all in DB
                for i, text in enumerate(chunk_texts):
                    ml_data = batch_res[i]
                    await store_prediction(
                        db=db,
                        user=user,
                        text=text,
                        ml_result=ml_data,
                        latency_ms=ml_data.get("_latency_ms", 0.0),
                        model_version=ml_service._model_version
                    )
                await db.commit()
                
                # Update progress
                current_prog = int(5 + (chunk_idx + 1) / total_chunks * 90)
                job_service.update_job(job_id, progress=current_prog)
                return batch_res

        # Execute chunks in parallel (limited concurrency for DB sanity)
        semaphore = asyncio.Semaphore(5)
        async def sem_process(c, idx):
            async with semaphore:
                return await process_chunk(c, idx)

        tasks = [sem_process(chunk, i) for i, chunk in enumerate(chunks)]
        all_res = await asyncio.gather(*tasks)
        
        # Flatten results
        flattened = [item for sublist in all_res for item in sublist]
        
        # Calculate summary stats
        spam_count = sum(1 for r in flattened if r.get("prediction") == 1)
        ham_count = len(flattened) - spam_count
        
        job_service.update_job(
            job_id, 
            status=JobStatus.COMPLETED, 
            progress=100, 
            result={
                "processed": len(flattened),
                "spam_count": spam_count,
                "ham_count": ham_count,
                "items": [
                    {
                        "row": i + 1,
                        "message": texts[i],
                        "verdict": "SPAM" if r["prediction"] == 1 else "HAM",
                        "probability": r["probability"]
                    }
                    for i, r in enumerate(flattened)
                ],
                "summary": f"Processed {len(flattened)} messages ({spam_count} spam, {ham_count} ham)."
            }
        )
        
    except Exception as e:
        logger.error(f"Batch job {job_id} failed: {e}")
        job_service.update_job(job_id, status=JobStatus.FAILED, error=str(e))


async def store_prediction(
    db:          AsyncSession,
    user:        User,
    text:        str,
    ml_result:   Dict[str, Any],
    latency_ms:  float = 0.0,
    model_version: str = "v1",
) -> Prediction:
    """
    Persist a single ML prediction result to the database.

    Parameters
    ----------
    db           : async SQLAlchemy session
    user         : authenticated User ORM object
    text         : the SMS message text
    ml_result    : dict returned by SpamDetectorService.predict()
    latency_ms   : inference latency
    model_version: active model version string

    Returns
    -------
    Prediction ORM object (already added to session, not committed)
    """

    # ── Store the raw SMS message ─────────────────────────────────────────────
    message = SMSMessage(
        user_id    = user.id,
        text       = text,
        char_count = len(text),
        word_count = len(text.split()),
    )
    db.add(message)
    await db.flush()   # get message.id without committing

    # ── Store the prediction ──────────────────────────────────────────────────
    prediction = Prediction(
        user_id         = user.id,
        message_id      = message.id,
        prediction      = ml_result["prediction"],
        probability     = ml_result["probability"],
        threshold_used  = ml_result["threshold_used"],
        is_spam         = ml_result["prediction"] == 1,
        latency_ms      = latency_ms,
        model_version   = model_version,
    )
    db.add(prediction)
    await db.flush()

    logger.info(
        "Stored prediction │ user=%s │ is_spam=%s │ prob=%.4f",
        user.username, prediction.is_spam, prediction.probability,
    )
    return prediction


async def get_user_history(
    db:      AsyncSession,
    user:    User,
    page:    int = 1,
    size:    int = 20,
    is_spam: Optional[bool] = None,
) -> HistoryResponse:
    """
    Return paginated prediction history for *user*.

    Parameters
    ----------
    is_spam : None → return all, True → spam only, False → ham only
    """
    stmt = (
        select(Prediction, SMSMessage.text)
        .join(SMSMessage, Prediction.message_id == SMSMessage.id)
        .where(Prediction.user_id == user.id)
    )
    if is_spam is not None:
        stmt = stmt.where(Prediction.is_spam == is_spam)
    stmt = stmt.order_by(Prediction.predicted_at.desc())

    # Total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total      = (await db.execute(count_stmt)).scalar_one()

    # Paginated rows
    offset = (page - 1) * size
    rows   = (await db.execute(stmt.offset(offset).limit(size))).all()

    items = [
        HistoryItem(
            id             = pred.id,
            text           = text,
            prediction     = pred.prediction,
            probability    = pred.probability,
            threshold_used = pred.threshold_used,
            is_spam        = pred.is_spam,
            predicted_at   = pred.predicted_at,
            model_version  = pred.model_version,
        )
        for pred, text in rows
    ]

    return HistoryResponse(total=total, page=page, size=size, items=items)


async def get_user_spam_trends_by_id(
    db:   AsyncSession,
    user_id: uuid.UUID,
    days: int = 7,
) -> SpamTrendsResponse:
    """Return daily counts for a specific user ID."""
    cache_key = f"trends_{user_id}_{days}"
    cached = cache_manager.get(cache_key)
    if cached: return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            func.date(Prediction.predicted_at).label("date"),
            func.count().label("total"),
            func.sum(func.cast(Prediction.is_spam, Integer)).label("spam_count"),
        )
        .where(Prediction.user_id == user_id)
        .where(Prediction.predicted_at >= since)
        .group_by(func.date(Prediction.predicted_at))
        .order_by(func.date(Prediction.predicted_at))
    )
    rows = (await db.execute(stmt)).all()
    points = [
        TrendPoint(
            date       = str(row.date),
            total      = row.total,
            spam_count = int(row.spam_count or 0),
            ham_count  = row.total - int(row.spam_count or 0),
            spam_rate  = round(int(row.spam_count or 0) / row.total, 4) if row.total else 0.0,
        )
        for row in rows
    ]
    res = SpamTrendsResponse(period=f"last_{days}_days", points=points)
    cache_manager.set(cache_key, res)
    return res


async def get_spam_trends(
    db:   AsyncSession,
    user: User,
    days: int = 7,
) -> SpamTrendsResponse:
    """
    Return daily spam/ham counts for the past *days* days for *user*.
    """
    # Cache check
    cache_key = f"trends_{user.id}_{days}"
    cached = cache_manager.get(cache_key)
    if cached: return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            func.date(Prediction.predicted_at).label("date"),
            func.count().label("total"),
            func.sum(func.cast(Prediction.is_spam, Integer)).label("spam_count"),
        )
        .where(Prediction.user_id == user.id)
        .where(Prediction.predicted_at >= since)
        .group_by(func.date(Prediction.predicted_at))
        .order_by(func.date(Prediction.predicted_at))
    )
    rows = (await db.execute(stmt)).all()

    points = [
        TrendPoint(
            date       = str(row.date),
            total      = row.total,
            spam_count = int(row.spam_count or 0),
            ham_count  = row.total - int(row.spam_count or 0),
            spam_rate  = round(int(row.spam_count or 0) / row.total, 4) if row.total else 0.0,
        )
        for row in rows
    ]
    res = SpamTrendsResponse(period=f"last_{days}_days", points=points)
    cache_manager.set(cache_key, res)
    return res

async def get_user_stats(
    db:   AsyncSession,
    user: User,
) -> Dict[str, Any]:
    """
    Return a summary of prediction stats for *user*.
    """
    # Cache check
    cache_key = f"stats_{user.id}"
    cached = cache_manager.get(cache_key)
    if cached: return cached

    # Run queries in parallel
    import asyncio
    stmt = select(
        func.count().label("total"),
        func.sum(func.cast(Prediction.is_spam, Integer)).label("spam_count"),
    ).where(Prediction.user_id == user.id)
    
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    stmt_24h = select(
        func.count().label("total"),
        func.sum(func.cast(Prediction.is_spam, Integer)).label("spam_count"),
    ).where(Prediction.user_id == user.id).where(Prediction.predicted_at >= since_24h)

    res_task = db.execute(stmt)
    res_24h_task = db.execute(stmt_24h)
    
    res_out, res_24h_out = await asyncio.gather(res_task, res_24h_task)
    
    res = res_out.one()
    res_24h = res_24h_out.one()

    total = res.total or 0
    spam  = int(res.spam_count or 0)
    total_24h = res_24h.total or 0
    spam_24h  = int(res_24h.spam_count or 0)
    
    # Calculate threat level
    spam_ratio = spam / total if total > 0 else 0
    if spam_ratio > 0.4:
        threat = "High"
    elif spam_ratio > 0.15:
        threat = "Medium"
    else:
        threat = "Low"

    data = {
        "total_scanned": total,
        "spam_blocked":  spam,
        "threat_level":  threat,
        "trends": {
            "total": f"+{total_24h}" if total_24h > 0 else "0",
            "spam":  f"+{spam_24h}" if spam_24h > 0 else "0",
        }
    }
    cache_manager.set(cache_key, data)
    return data



# ── Admin-wide services ────────────────────────────────────────────────────────

async def get_global_analytics(
    db:  AsyncSession,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Return global analytics across ALL users.
    """
    # Cache check
    cache_key = f"global_analytics_{days}"
    cached = cache_manager.get(cache_key)
    if cached: return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Total counts
    total_stmt = select(
        func.count().label("total"),
        func.sum(func.cast(Prediction.is_spam, Integer)).label("spam_count"),
    )
    total_row = (await db.execute(total_stmt)).one()
    total      = total_row.total or 0
    spam_count = int(total_row.spam_count or 0)
    ham_count  = total - spam_count

    # User counts
    user_count_stmt  = select(func.count()).select_from(User)
    active_count_stmt = select(func.count()).select_from(User).where(User.is_active == True)  # noqa: E712
    total_users  = (await db.execute(user_count_stmt)).scalar_one()
    active_users = (await db.execute(active_count_stmt)).scalar_one()

    # Recent daily activity (last N days)
    daily_stmt = (
        select(
            func.date(Prediction.predicted_at).label("date"),
            func.count().label("total"),
            func.sum(func.cast(Prediction.is_spam, Integer)).label("spam_count"),
        )
        .where(Prediction.predicted_at >= since)
        .group_by(func.date(Prediction.predicted_at))
        .order_by(func.date(Prediction.predicted_at))
    )
    daily_rows = (await db.execute(daily_stmt)).all()

    recent_activity = [
        {
            "date":       str(r.date),
            "total":      r.total,
            "spam_count": int(r.spam_count or 0),
            "ham_count":  r.total - int(r.spam_count or 0),
            "spam_rate":  round(int(r.spam_count or 0) / r.total, 4) if r.total else 0.0,
        }
        for r in daily_rows
    ]

    data = {
        "total_messages":  total,
        "total_spam":      spam_count,
        "total_ham":       ham_count,
        "spam_percentage": round(spam_count / total * 100, 2) if total else 0.0,
        "ham_percentage":  round(ham_count  / total * 100, 2) if total else 0.0,
        "total_users":     total_users,
        "active_users":    active_users,
        "recent_activity": recent_activity,
    }
    cache_manager.set(cache_key, data)
    return data


async def get_all_users_with_count(
    db:   AsyncSession,
    page: int = 1,
    size: int = 20,
) -> Dict[str, Any]:
    """Return paginated user list with prediction counts."""
    from app.models.user import User
    from sqlalchemy import outerjoin

    # Count predictions per user via subquery
    pred_count_sub = (
        select(
            Prediction.user_id.label("uid"),
            func.count().label("pcount"),
            func.sum(func.cast(Prediction.is_spam, Integer)).label("scount"),
        )
        .group_by(Prediction.user_id)
        .subquery()
    )

    stmt = (
        select(
            User, 
            func.coalesce(pred_count_sub.c.pcount, 0).label("prediction_count"),
            func.coalesce(pred_count_sub.c.scount, 0).label("spam_count"),
        )
        .outerjoin(pred_count_sub, User.id == pred_count_sub.c.uid)
        .order_by(User.created_at.desc())
    )

    count_stmt = select(func.count()).select_from(User)
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * size
    rows   = (await db.execute(stmt.offset(offset).limit(size))).all()

    items = []
    for user, pred_count, spam_count in rows:
        p_count = pred_count or 0
        s_count = int(spam_count or 0)
        h_count = p_count - s_count
        items.append({
            "id":               user.id,
            "username":         user.username,
            "email":            user.email,
            "role":             user.role.value if hasattr(user.role, "value") else str(user.role),
            "is_active":        user.is_active,
            "created_at":       user.created_at,
            "last_login":       user.last_login,
            "prediction_count": p_count,
            "spam_count":       s_count,
            "ham_count":        h_count,
        })

    return {"total": total, "page": page, "size": size, "items": items}


async def export_user_predictions_csv(
    db:        AsyncSession,
    user_id:   Any      = None,    # None → all users (admin)
    is_spam:   Optional[bool] = None,
    from_date: Optional[datetime] = None,
    to_date:   Optional[datetime]   = None,
) -> str:
    """
    Generate a CSV string of predictions (optionally filtered).
    Returns the complete CSV as a string (suitable for StreamingResponse).
    """
    stmt = (
        select(
            Prediction.id,
            SMSMessage.text,
            Prediction.prediction,
            Prediction.probability,
            Prediction.threshold_used,
            Prediction.is_spam,
            Prediction.model_version,
            Prediction.predicted_at,
            Prediction.latency_ms,
            User.username,
        )
        .join(SMSMessage, Prediction.message_id == SMSMessage.id)
        .join(User, Prediction.user_id == User.id)
    )

    if user_id is not None:
        stmt = stmt.where(Prediction.user_id == user_id)
    if is_spam is not None:
        stmt = stmt.where(Prediction.is_spam == is_spam)
    if from_date is not None:
        stmt = stmt.where(Prediction.predicted_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Prediction.predicted_at <= to_date)

    stmt = stmt.order_by(Prediction.predicted_at.desc())
    rows = (await db.execute(stmt)).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "id", "username", "message", "prediction", "probability",
        "threshold_used", "is_spam", "verdict", "model_version",
        "predicted_at", "latency_ms",
    ])

    # Handle empty data gracefully
    if not rows:
        logger.info("Export: no rows matched filters.")
        return output.getvalue()

    # Rows
    for row in rows:
        verdict = "SPAM" if row.is_spam else "HAM"
        writer.writerow([
            str(row.id),
            row.username,
            row.text,
            row.prediction,
            round(row.probability, 6),
            round(row.threshold_used, 6),
            row.is_spam,
            verdict,
            row.model_version,
            row.predicted_at.isoformat() if row.predicted_at else "",
            round(row.latency_ms or 0, 2),
        ])

    logger.info("Export: generated %d rows", len(rows))
    return output.getvalue()
