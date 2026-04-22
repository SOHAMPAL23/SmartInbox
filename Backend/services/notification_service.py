"""
app/services/notification_service.py
--------------------------------------
CRUD operations for in-app notifications.

After creating a notification we also push it to the user's active
WebSocket connections (if any) so the client receives real-time updates
without polling.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.notification import Notification
from app.schemas.notification import NotificationCreate


async def create_notification(db: AsyncSession, schema: NotificationCreate) -> Notification:
    """Persist a new notification and push it to the user's WS connections."""
    notif = Notification(
        user_id = schema.user_id,
        title   = schema.title,
        message = schema.message,
        type    = schema.type,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)

    # ── Real-time push via WebSocket (best-effort, never fails silently) ──────
    try:
        from app.services.ws_manager import manager
        payload = {
            "id":         str(notif.id),
            "user_id":    str(notif.user_id),
            "title":      notif.title,
            "message":    notif.message,
            "type":       notif.type,
            "is_read":    notif.is_read,
            "created_at": notif.created_at.isoformat() if notif.created_at else None,
        }
        await manager.broadcast_to_user(notif.user_id, payload)
    except Exception:
        pass  # WS push is best-effort; REST polling is the fallback

    return notif


async def get_user_notifications(db: AsyncSession, user_id: uuid.UUID):
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)          # cap at 50 for performance
    )
    return (await db.execute(stmt)).scalars().all()


async def mark_as_read(
    db: AsyncSession,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    stmt = (
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        .values(is_read=True)
    )
    await db.execute(stmt)
    await db.commit()
