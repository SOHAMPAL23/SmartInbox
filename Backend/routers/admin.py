"""
app/routers/admin.py
--------------------
Admin-only endpoints: retrain, update-threshold, metrics, model-info,
user management, global analytics, prediction management, messages, and export.
All routes require role=admin enforced by the `AdminUser` dependency.

Routes:
  POST   /api/v1/admin/login            - Admin login (role-checked)
  GET    /api/v1/admin/dashboard        - Dashboard stats alias → analytics
  GET    /api/v1/admin/analytics        - Global analytics
  GET    /api/v1/admin/stats            - Quick stat summary
  GET    /api/v1/admin/users            - List users (paginated)
  DELETE /api/v1/admin/users/{id}       - Delete user
  PATCH  /api/v1/admin/users/{id}       - Update user status/role
  GET    /api/v1/admin/messages         - All messages/predictions (paginated)
  DELETE /api/v1/admin/predictions/{id} - Delete prediction
  GET    /api/v1/admin/export           - Export CSV
  GET    /api/v1/admin/logs             - Audit logs
  GET    /api/v1/admin/metrics          - Model evaluation metrics
  GET    /api/v1/admin/model-info       - Model card
  POST   /api/v1/admin/retrain          - Retrain model
  POST   /api/v1/admin/update-threshold - Update threshold
  GET    /api/v1/admin/model-versions   - List model versions
  GET    /api/v1/admin/model-info/feature-importance
"""

import io
import json
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Integer, case, func, select, update

from app.auth.dependencies import AdminUser, DBSession, PublicAdminUser
from app.auth.jwt_handler import decode_access_token, create_access_token, create_refresh_token
from app.auth.password import verify_password
from app.core.logging import get_logger
from app.schemas.prediction import SpamTrendsResponse
from app.models.admin_log import AdminLog
from app.models.evaluation_metric import EvaluationMetric
from app.models.model_version import ModelVersion
from app.models.prediction import Prediction
from app.models.sms_message import SMSMessage
from app.models.user import User, UserRole
from app.schemas.admin import (
    AnalyticsDailyPoint,
    FeatureImportanceResponse,
    GlobalAnalyticsResponse,
    MetricPoint,
    MetricsResponse,
    ModelInfoResponse,
    ModelVersionOut,
    RetrainResponse,
    UpdateThresholdRequest,
    UpdateThresholdResponse,
    UserListResponse,
    UserOut,
    UserUpdateRequest,
)
from app.schemas.notification import NotificationCreate, NotificationOut
from app.services.ml_service import MLService, translate_ml_error
from app.services.notification_service import create_notification
from app.models.notification import Notification
from app.services.prediction_service import (
    export_user_predictions_csv,
    get_all_users_with_count,
    get_global_analytics,
    get_user_spam_trends_by_id,
)

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = get_logger("router.admin")


# ── Helper: write audit log ───────────────────────────────────────────────────

async def _audit(
    db: Any,
    admin: User,
    action: str,
    *,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    detail: Optional[str] = None,
    request: Optional[Request] = None,
    severity: str = "INFO",
) -> None:
    """Persist an admin audit log entry (non-blocking fire-and-forget style)."""
    try:
        ip = None
        ua = None
        if request:
            forwarded = request.headers.get("X-Forwarded-For")
            ip = forwarded.split(",")[0].strip() if forwarded else str(request.client.host) if request.client else None
            ua = request.headers.get("User-Agent")

        log = AdminLog(
            admin_id    = admin.id,
            admin_email = admin.email,
            action      = action,
            target_type = target_type,
            target_id   = str(target_id) if target_id else None,
            detail      = detail,
            ip_address  = ip,
            user_agent  = ua,
            severity    = severity,
        )
        db.add(log)
        # Note: caller must commit the session
    except Exception as exc:
        logger.warning("Audit log write failed (non-fatal): %s", exc)


# ── POST /admin/login ─────────────────────────────────────────────────────────

@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="[Admin] Dedicated admin login – validates role=admin",
)
async def admin_login(
    req: Dict[str, str],
    db:  DBSession,
) -> Dict[str, Any]:
    """
    Admin-specific login that:
    - Validates email + password
    - Ensures role == 'admin'
    - Issues JWT with sub=admin_id, role='admin'
    - Returns access + refresh tokens
    """
    email    = req.get("email", "").strip().lower()
    password = req.get("password", "")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="email and password are required.",
        )

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: admin role required.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is deactivated.",
        )

    # Issue tokens
    access_token  = create_access_token(str(user.id), role="admin")
    refresh_token = create_refresh_token(str(user.id))

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    logger.info("Admin login │ email=%s │ id=%s", user.email, user.id)

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "role":          "admin",
        "user_id":       str(user.id),
        "username":      user.username,
        "email":         user.email,
    }


# ── GET /admin/dashboard ──────────────────────────────────────────────────────

@router.get(
    "/dashboard",
    response_model=GlobalAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Dashboard overview – same as /analytics",
)
async def admin_dashboard(
    admin: AdminUser,
    db:    DBSession,
    ml:    MLService,
    days:  Annotated[int, Query(ge=1, le=365)] = 30,
) -> GlobalAnalyticsResponse:
    """Alias to /analytics – returns the full dashboard stat set."""
    analytics = await get_global_analytics(db, days=days)
    
    try:
        info = ml.get_model_info()
    except Exception as exc:
        raise translate_ml_error(exc)

    return GlobalAnalyticsResponse(
        total_messages    = analytics["total_messages"],
        total_spam        = analytics["total_spam"],
        total_ham         = analytics["total_ham"],
        spam_percentage   = analytics["spam_percentage"],
        ham_percentage    = analytics["ham_percentage"],
        total_users       = analytics["total_users"],
        active_users      = analytics["active_users"],
        recent_activity   = [AnalyticsDailyPoint(**p) for p in analytics["recent_activity"]],
        model_version     = info["model_version"],
        last_refreshed_at = datetime.now(timezone.utc).isoformat(),
    )


# ── GET /admin/stats ──────────────────────────────────────────────────────────

@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="[Admin] Quick stat summary (counts only)",
)
async def admin_stats(
    admin: AdminUser,
    db:    DBSession,
) -> Dict[str, Any]:
    """
    Lightweight stat summary used by dashboard cards:
    - total_users, total_messages, spam_count, ham_count
    """
    total_msg_row = (await db.execute(
        select(
            func.count().label("total"),
            func.sum(func.cast(Prediction.is_spam, Integer)).label("spam_count"),
        )
    )).one()

    total_users  = (await db.execute(select(func.count(User.id)))).scalar_one_or_none() or 0
    active_users = (await db.execute(
        select(func.count()).select_from(User).where(User.is_active == True)  # noqa: E712
    )).scalar_one()

    total    = total_msg_row.total or 0
    spam     = int(total_msg_row.spam_count or 0)
    ham      = total - spam

    return {
        "total_users":   total_users,
        "active_users":  active_users,
        "total_messages": total,
        "spam_count":    spam,
        "ham_count":     ham,
        "spam_rate":     round(spam / total * 100, 2) if total else 0.0,
    }


# ── GET /admin/messages ───────────────────────────────────────────────────────

@router.get(
    "/messages",
    status_code=status.HTTP_200_OK,
    summary="[Admin] View all SMS predictions (paginated, filterable)",
)
async def list_all_messages(
    admin:   AdminUser,
    db:      DBSession,
    page:    Annotated[int,           Query(ge=1,        description="Page number")]         = 1,
    size:    Annotated[int,           Query(ge=1, le=100, description="Items per page")]     = 20,
    is_spam: Annotated[Optional[bool], Query(description="Filter spam (true) or ham (false)")] = None,
    user_id: Annotated[Optional[str], Query(description="Filter by user UUID")]              = None,
    q:       Annotated[Optional[str], Query(description="Search in message text")]           = None,
) -> Dict[str, Any]:
    """
    Returns all SMS messages with predictions across all users.
    Supports:
    - Filter by is_spam (True/False)
    - Filter by user_id
    - Full-text search (ilike)
    - Pagination
    """
    stmt = (
        select(
            Prediction.id.label("prediction_id"),
            SMSMessage.text.label("message_text"),
            Prediction.is_spam,
            Prediction.probability,
            Prediction.threshold_used,
            Prediction.model_version,
            Prediction.predicted_at,
            Prediction.latency_ms,
            User.username,
            User.email,
            User.id.label("user_id"),
        )
        .join(SMSMessage, Prediction.message_id == SMSMessage.id)
        .join(User, Prediction.user_id == User.id)
    )

    if is_spam is not None:
        stmt = stmt.where(Prediction.is_spam == is_spam)
    if user_id:
        try:
            uid = uuid.UUID(user_id)
            stmt = stmt.where(Prediction.user_id == uid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format.")
    if q:
        stmt = stmt.where(SMSMessage.text.ilike(f"%{q}%"))

    stmt = stmt.order_by(Prediction.predicted_at.desc())

    # Count
    count_sq = stmt.subquery()
    total    = (await db.execute(select(func.count()).select_from(count_sq))).scalar_one()

    # Page
    offset = (page - 1) * size
    rows   = (await db.execute(stmt.offset(offset).limit(size))).all()

    items = [
        {
            "prediction_id":  str(r.prediction_id),
            "message_text":   r.message_text,
            "is_spam":        r.is_spam,
            "verdict":        "SPAM" if r.is_spam else "HAM",
            "probability":    round(r.probability, 4),
            "threshold_used": round(r.threshold_used, 4),
            "confidence_score": round(r.probability * 100, 2),
            "model_version":  r.model_version,
            "predicted_at":   r.predicted_at.isoformat() if r.predicted_at else None,
            "latency_ms":     round(r.latency_ms or 0, 2),
            "username":       r.username,
            "user_email":     r.email,
            "user_id":        str(r.user_id),
        }
        for r in rows
    ]

    return {
        "total":    total,
        "page":     page,
        "size":     size,
        "pages":    -(-total // size),  # ceiling division
        "filters":  {"is_spam": is_spam, "user_id": user_id, "q": q},
        "items":    items,
    }


# ── POST /admin/retrain ───────────────────────────────────────────────────────

@router.post(
    "/retrain",
    response_model=RetrainResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="[Admin] Retrain the model on a new dataset",
)
async def retrain(
    admin:        AdminUser,
    db:           DBSession,
    ml:           MLService,
    request:      Request,
    file:         UploadFile = File(..., description="CSV with columns: text, label (0=ham, 1=spam)"),
    n_estimators: int     = Form(300,  ge=50,  le=1000),
    test_size:    float   = Form(0.20, gt=0.0, lt=0.5),
    seed:         int     = Form(42),
    notes:        Optional[str] = Form(None, max_length=500),
) -> RetrainResponse:
    """Upload a labeled CSV and trigger a full retraining cycle."""
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")

    if not {"text", "label"}.issubset(set(df.columns)):
        raise HTTPException(status_code=400, detail="CSV must contain 'text' and 'label' columns.")

    logger.info("Retrain │ admin=%s │ rows=%d │ n_estimators=%d", admin.username, len(df), n_estimators)

    try:
        result = ml.retrain(new_dataset=df, n_estimators=n_estimators, test_size=test_size, seed=seed)
    except Exception as exc:
        raise translate_ml_error(exc)

    new_version_tag = ml._model_version

    mv = ModelVersion(
        version_tag = new_version_tag,
        is_active   = True,
        trained_by  = admin.username,
        roc_auc     = result["metrics"].get("roc_auc"),
        pr_auc      = result["metrics"].get("pr_auc"),
        f1          = result["metrics"].get("f1"),
        accuracy    = result["metrics"].get("accuracy"),
        threshold   = result["threshold"],
        notes       = notes,
    )
    db.add(mv)

    previous = (await db.execute(
        select(ModelVersion).where(ModelVersion.version_tag != new_version_tag)
    )).scalars().all()
    for old in previous:
        old.is_active = False

    await _audit(db, admin, "retrain_model",
                 target_type="model_version", target_id=new_version_tag,
                 detail=json.dumps({"rows": len(df), "n_estimators": n_estimators}),
                 request=request)
    await db.commit()

    logger.info("Retrain complete │ new_version=%s", new_version_tag)
    return RetrainResponse(
        success=result["success"], new_model_path=result["new_model_path"],
        new_version_tag=new_version_tag, metrics=result["metrics"],
        threshold=result["threshold"], trained_at=result["trained_at"],
        message=result["message"],
    )


# ── POST /admin/update-threshold ──────────────────────────────────────────────

@router.post(
    "/update-threshold",
    response_model=UpdateThresholdResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Dynamically update the decision threshold",
)
async def update_threshold(
    admin:   AdminUser,
    db:      DBSession,
    ml:      MLService,
    req:     UpdateThresholdRequest,
    request: Request,
) -> UpdateThresholdResponse:
    """Change the spam/ham threshold live — no model reload required."""
    old_threshold = ml._threshold
    try:
        ml.update_threshold(req.threshold)
    except Exception as exc:
        raise translate_ml_error(exc)

    version_tag = ml._model_version
    await db.execute(
        update(ModelVersion)
        .where(ModelVersion.version_tag == version_tag)
        .where(ModelVersion.is_active == True)  # noqa: E712
        .values(threshold=req.threshold)
    )
    await db.execute(
        update(Prediction).values(
            is_spam=case(
                (Prediction.probability >= req.threshold, True),
                else_=False,
            )
        )
    )

    await _audit(db, admin, "update_threshold",
                 detail=json.dumps({"old": old_threshold, "new": req.threshold, "reason": req.reason}),
                 request=request)
    await db.commit()

    logger.info("Threshold │ admin=%s │ %.4f → %.4f", admin.username, old_threshold, req.threshold)
    return UpdateThresholdResponse(
        old_threshold=old_threshold,
        new_threshold=ml._threshold,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


# ── GET /admin/metrics ────────────────────────────────────────────────────────

@router.get(
    "/metrics",
    response_model=MetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Evaluation metrics for the active model",
)
async def get_metrics(db: DBSession, ml: MLService) -> MetricsResponse:
    info        = ml.get_model_info()
    version_tag = info["model_version"]

    mv = (await db.execute(
        select(ModelVersion).where(ModelVersion.version_tag == version_tag)
    )).scalar_one_or_none()

    metric_rows: List[MetricPoint] = []
    if mv:
        rows = (await db.execute(
            select(EvaluationMetric)
            .where(EvaluationMetric.model_version_id == mv.id)
            .order_by(EvaluationMetric.recorded_at.desc())
        )).scalars().all()
        metric_rows = [MetricPoint(metric_name=r.metric_name, metric_value=r.metric_value,
                                    split=r.split, recorded_at=r.recorded_at) for r in rows]

    summary = {k: v for k in ("roc_auc", "pr_auc", "f1", "accuracy", "optimal_f1")
               if (v := info.get(k, -1.0)) != -1.0}

    return MetricsResponse(model_version=version_tag, metrics=metric_rows, summary=summary)


# ── GET /admin/model-info ─────────────────────────────────────────────────────

@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Model card for the currently loaded model",
)
async def get_model_info(ml: MLService) -> ModelInfoResponse:
    try:
        return ModelInfoResponse(**ml.get_model_info())
    except Exception as exc:
        raise translate_ml_error(exc)


# ── GET /admin/model-info/feature-importance ──────────────────────────────────

@router.get(
    "/model-info/feature-importance",
    response_model=FeatureImportanceResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Top-N most important features",
)
async def get_feature_importance(
    ml:    MLService,
    top_n: Annotated[int, Query(ge=1, le=50)] = 20,
) -> FeatureImportanceResponse:
    try:
        features = ml.get_feature_importance(top_n=top_n)
    except Exception as exc:
        raise translate_ml_error(exc)
    return FeatureImportanceResponse(model_version=ml._model_version, features=features)


# ── GET /admin/model-versions ─────────────────────────────────────────────────

@router.get(
    "/model-versions",
    response_model=List[ModelVersionOut],
    status_code=status.HTTP_200_OK,
    summary="[Admin] List all registered model versions",
)
async def list_model_versions(db: DBSession) -> List[ModelVersionOut]:
    rows = (await db.execute(
        select(ModelVersion).order_by(ModelVersion.created_at.desc())
    )).scalars().all()
    return [ModelVersionOut.model_validate(r) for r in rows]


# ── GET /admin/analytics ──────────────────────────────────────────────────────

@router.get(
    "/analytics",
    response_model=GlobalAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Global analytics across all users",
)
async def global_analytics(
    admin: AdminUser,
    db:    DBSession,
    ml:    MLService,
    days:  Annotated[int, Query(ge=1, le=365)] = 30,
) -> GlobalAnalyticsResponse:
    analytics = await get_global_analytics(db, days=days)
    
    try:
        info = ml.get_model_info()
    except Exception as exc:
        raise translate_ml_error(exc)

    return GlobalAnalyticsResponse(
        total_messages    = analytics["total_messages"],
        total_spam        = analytics["total_spam"],
        total_ham         = analytics["total_ham"],
        spam_percentage   = analytics["spam_percentage"],
        ham_percentage    = analytics["ham_percentage"],
        total_users       = analytics["total_users"],
        active_users      = analytics["active_users"],
        recent_activity   = [AnalyticsDailyPoint(**p) for p in analytics["recent_activity"]],
        model_version     = info["model_version"],
        last_refreshed_at = datetime.now(timezone.utc).isoformat(),
    )


# ── GET /admin/users/{user_id}/analytics ──────────────────────────────────────

@router.get(
    "/users/{user_id}/analytics",
    response_model=SpamTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Get specific user's spam/ham trends",
)
async def get_user_analytics(
    user_id: uuid.UUID,
    admin:   AdminUser,
    db:      DBSession,
    days:    Annotated[int, Query(ge=1, le=365)] = 30,
) -> SpamTrendsResponse:
    return await get_user_spam_trends_by_id(db, user_id=user_id, days=days)


# ── GET /admin/users ──────────────────────────────────────────────────────────

@router.get(
    "/users",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] List all users with prediction counts",
)
async def list_users(
    admin: AdminUser,
    db:    DBSession,
    page:  Annotated[int, Query(ge=1,        description="Page number")]    = 1,
    size:  Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> UserListResponse:
    result = await get_all_users_with_count(db, page=page, size=size)
    return UserListResponse(
        total = result["total"],
        page  = result["page"],
        size  = result["size"],
        items = [UserOut(**u) for u in result["items"]],
    )


# ── PATCH /admin/users/{user_id} ──────────────────────────────────────────────

@router.patch(
    "/users/{user_id}",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Update user status or role",
)
async def update_user(
    user_id: uuid.UUID,
    req:     UserUpdateRequest,
    admin:   AdminUser,
    db:      DBSession,
    request: Request,
) -> UserOut:
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot modify their own account via this endpoint.")

    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    changes: Dict[str, Any] = {}
    if req.is_active is not None:
        target.is_active = req.is_active
        changes["is_active"] = req.is_active
    if req.role is not None:
        try:
            target.role = UserRole(req.role)
            changes["role"] = req.role
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}")

    await _audit(db, admin, "update_user",
                 target_type="user", target_id=str(user_id),
                 detail=json.dumps(changes), request=request)
    await db.commit()
    await db.refresh(target)

    logger.info("User updated │ admin=%s │ target=%s │ changes=%s", admin.username, target.username, changes)
    return UserOut(
        id=target.id, username=target.username, email=target.email,
        role=target.role.value, is_active=target.is_active,
        created_at=target.created_at, last_login=target.last_login,
        prediction_count=0,
    )


# ── DELETE /admin/users/{user_id} ─────────────────────────────────────────────

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="[Admin] Permanently delete a user and all their data",
)
async def delete_user(
    user_id: uuid.UUID,
    admin:   AdminUser,
    db:      DBSession,
    request: Request,
):
    """
    Permanently delete a user account.
    This also cascades and deletes all their predictions and messages.
    Admins cannot delete themselves.
    """
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot delete their own account.")

    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    username = target.username
    email    = target.email

    await _audit(db, admin, "delete_user",
                 target_type="user", target_id=str(user_id),
                 detail=json.dumps({"username": username, "email": email}),
                 request=request)

    await db.delete(target)
    await db.commit()

    logger.info("User deleted │ admin=%s │ deleted_user=%s (%s)", admin.username, username, email)
    return {"deleted": str(user_id), "username": username, "message": "User and all associated data deleted."}


# ── DELETE /admin/predictions/{prediction_id} ─────────────────────────────────

@router.delete(
    "/predictions/{prediction_id}",
    status_code=status.HTTP_200_OK,
    summary="[Admin] Delete a prediction record",
)
async def delete_prediction(
    prediction_id: uuid.UUID,
    admin:         AdminUser,
    db:            DBSession,
    request:       Request,
):
    pred = (await db.execute(
        select(Prediction).where(Prediction.id == prediction_id)
    )).scalar_one_or_none()

    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found.")

    message_id = pred.message_id
    await db.delete(pred)

    # Clean up orphaned SMSMessage
    other_preds = (await db.execute(
        select(Prediction).where(Prediction.message_id == message_id)
    )).scalar_one_or_none()
    if not other_preds:
        msg = (await db.execute(
            select(SMSMessage).where(SMSMessage.id == message_id)
        )).scalar_one_or_none()
        if msg:
            await db.delete(msg)

    await _audit(db, admin, "delete_prediction",
                 target_type="prediction", target_id=str(prediction_id),
                 request=request)
    await db.commit()

    logger.info("Prediction deleted │ admin=%s │ prediction_id=%s", admin.username, prediction_id)
    return {"deleted": str(prediction_id), "message": "Prediction deleted successfully."}


# ── GET /admin/export ─────────────────────────────────────────────────────────

@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="[Admin] Export all predictions as CSV",
    response_class=StreamingResponse,
)
async def export_all_predictions(
    admin:     AdminUser,
    db:        DBSession,
    request:   Request,
    is_spam:   Annotated[Optional[bool],     Query(description="Filter: spam only / ham only")] = None,
    from_date: Annotated[Optional[datetime], Query(description="ISO start datetime")]           = None,
    to_date:   Annotated[Optional[datetime], Query(description="ISO end datetime")]             = None,
):
    """Export all users' prediction history as CSV. Supports filters."""
    logger.info("Admin export │ admin=%s │ is_spam=%s", admin.username, is_spam)

    csv_content = await export_user_predictions_csv(
        db, user_id=None, is_spam=is_spam, from_date=from_date, to_date=to_date
    )

    filename = f"smartinbox_admin_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    await _audit(db, admin, "export_csv",
                 detail=json.dumps({"is_spam": is_spam}),
                 request=request)
    await db.commit()

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── POST /admin/notifications ──────────────────────────────────────────────────

@router.post(
    "/notifications",
    response_model=NotificationOut,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Send a notification to a specific user",
)
async def admin_send_notification(
    req:   NotificationCreate,
    admin: AdminUser,
    db:    DBSession,
    request: Request,
) -> NotificationOut:
    """Send a notification/security alert to a user."""
    notif = await create_notification(db, req)
    
    await _audit(db, admin, "send_notification",
                 target_type="user", target_id=str(req.user_id),
                 detail=json.dumps({"title": req.title, "type": req.type}),
                 request=request)
                 
    logger.info("Notification sent │ admin=%s │ user=%s │ type=%s", admin.username, req.user_id, req.type)
    return notif


# ── GET /admin/logs ───────────────────────────────────────────────────────────

@router.get(
    "/logs",
    status_code=status.HTTP_200_OK,
    summary="[Admin] View admin audit logs",
)
async def get_audit_logs(
    admin:     AdminUser,
    db:        DBSession,
    page:      Annotated[int, Query(ge=1)]           = 1,
    size:      Annotated[int, Query(ge=1, le=100)]   = 20,
    action:    Annotated[Optional[str], Query(description="Filter by action type")]       = None,
    severity:  Annotated[Optional[str], Query(description="Filter by severity (INFO/WARNING/ERROR)")] = None,
    search:    Annotated[Optional[str], Query(description="Search in detail field")]      = None,
    from_date: Annotated[Optional[datetime], Query(description="ISO datetime lower bound")] = None,
    to_date:   Annotated[Optional[datetime], Query(description="ISO datetime upper bound")] = None,
) -> Dict[str, Any]:
    """Return paginated admin audit logs, newest first. Supports filtering & full-text search."""
    stmt = select(AdminLog).order_by(AdminLog.timestamp.desc())

    if action:
        stmt = stmt.where(AdminLog.action == action)
    if severity:
        stmt = stmt.where(AdminLog.severity == severity.upper())
    if search:
        stmt = stmt.where(AdminLog.detail.ilike(f"%{search}%"))
    if from_date:
        stmt = stmt.where(AdminLog.timestamp >= from_date)
    if to_date:
        stmt = stmt.where(AdminLog.timestamp <= to_date)

    total = (await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )).scalar_one()

    offset = (page - 1) * size
    rows   = (await db.execute(stmt.offset(offset).limit(size))).scalars().all()

    items = [
        {
            "id":          str(r.id),
            "admin_id":    str(r.admin_id),
            "admin_email": r.admin_email,
            "action":      r.action,
            "target_type": r.target_type,
            "target_id":   r.target_id,
            "detail":      r.detail,
            "ip_address":  r.ip_address,
            "user_agent":  r.user_agent,
            "severity":    getattr(r, "severity", "INFO"),
            "timestamp":   r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in rows
    ]

    return {
        "total": total,
        "page":  page,
        "size":  size,
        "pages": max(1, -(-total // size)),  # ceiling division
        "items": items,
    }
