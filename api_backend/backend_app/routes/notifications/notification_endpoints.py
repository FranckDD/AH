# api_backend/backend_app/routes/notifications/notification_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user
from repositories.notification_repo import NotificationRepository
from controller.notification_controller import NotificationController

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_notification_controller(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> NotificationController:
    repo = NotificationRepository(db)
    return NotificationController(repo=repo, current_user=current_user)


@router.get("", response_model=List[Dict])
def list_notifications(
    status: Optional[str] = Query(None),
    ctrl: NotificationController = Depends(get_notification_controller),
):
    notifs = ctrl.list_unread() if status == "unread" or status is None else []
    return [
        {
            "id": n.id,
            "type": n.type,
            "payload": n.payload,
            "status": n.status,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@router.post("/{notification_id}/read")
def mark_notification_read(notification_id: int, ctrl: NotificationController = Depends(get_notification_controller)):
    try:
        ctrl.mark_read(notification_id)
        return {"detail": "Notification marquée lue."}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
