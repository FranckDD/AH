# controller/notification_controller.py
from typing import List
from repositories.notification_repo import NotificationRepository
from models.notification import Notification


class NotificationController:
    def __init__(self, repo: NotificationRepository, current_user):
        self.repo = repo
        self.user = current_user

    def list_unread(self) -> List[Notification]:
        return self.repo.list_unread(self.user.user_id)

    def mark_read(self, notification_id: int) -> Notification:
        notif = self.repo.mark_read(notification_id, self.user.user_id)
        if not notif:
            raise ValueError("Notification introuvable.")
        self.repo.session.commit()
        return notif
