# repositories/notification_repo.py
from datetime import datetime
from typing import Optional, Dict, Any, List
from models.notification import Notification


class NotificationRepository:
    def __init__(self, session):
        self.session = session

    def create(self, recipient_user_id: int, type: str, payload: Optional[Dict[str, Any]] = None) -> Notification:
        notif = Notification(recipient_user_id=recipient_user_id, type=type, payload=payload)
        self.session.add(notif)
        self.session.flush()
        return notif

    def list_unread(self, recipient_user_id: int) -> List[Notification]:
        return (
            self.session.query(Notification)
            .filter(Notification.recipient_user_id == recipient_user_id, Notification.status == "unread")
            .order_by(Notification.created_at.desc())
            .all()
        )

    def mark_read(self, notification_id: int, recipient_user_id: int) -> Optional[Notification]:
        notif = (
            self.session.query(Notification)
            .filter(Notification.id == notification_id, Notification.recipient_user_id == recipient_user_id)
            .first()
        )
        if not notif:
            return None
        notif.status = "read"
        notif.read_at = datetime.utcnow()
        return notif
