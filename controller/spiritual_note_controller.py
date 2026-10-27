# controller/spiritual_note_controller.py
"""Notes du conseiller spirituel.

Le controleur possede la transaction. Les roles de lecture/ecriture sont verifies par les
endpoints ; ici on applique la regle d'auteur (seul l'auteur modifie ou supprime).
Erreurs : LookupError -> 404, PermissionError -> 403, ValueError -> 422.
Le texte d'une note n'est JAMAIS ecrit dans l'audit ni dans les journaux.
"""
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from models.spiritual_note import SpiritualNote
from repositories.audit_repo import AuditRepository
from repositories.spiritual_note_repo import SpiritualNoteRepository
from utils.business_time import business_today

logger = logging.getLogger(__name__)

WRITER_ROLE = "spiritualcounsellor"
MAX_PAST_DAYS = 365
MAX_CONTENT = 5000
MAX_VERSE = 120
FLAGS = ("counsel", "prayer", "verse_read", "discussion", "text_given", "qa", "no_one_spoke")
RESOURCE_TYPE = "SpiritualNote"
_BAD_DATE = "Date de rencontre invalide (format AAAA-MM-JJ)."


class SpiritualNoteNotFoundError(LookupError):
    pass


def _parse_date(value: Any, today: date) -> date:
    if isinstance(value, str):
        try:
            d = date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError(_BAD_DATE)
    else:
        raise ValueError(_BAD_DATE)
    if d > today:
        raise ValueError("La date de rencontre ne peut pas etre dans le futur.")
    if d < today - timedelta(days=MAX_PAST_DAYS):
        raise ValueError("La date de rencontre ne peut pas depasser 365 jours dans le passe.")
    return d


class SpiritualNoteController:
    def __init__(self, repo: SpiritualNoteRepository, audit_repo: AuditRepository, current_user: Any):
        self.repo = repo
        self.session = repo.session
        self.audit_repo = audit_repo
        self.user = current_user

    def _is_counsellor(self) -> bool:
        roles = {str(r).strip().lower() for r in (getattr(self.user, "roles", None) or []) if r}
        return WRITER_ROLE in roles

    def _dict(self, n: SpiritualNote, author_name: Optional[str]) -> Dict[str, Any]:
        d = {
            "id": n.id, "author_id": n.author_id, "author_name": author_name,
            "meeting_date": n.meeting_date.isoformat(),
            "verse_reference": n.verse_reference, "content": n.content,
            "created_at": n.created_at, "updated_at": n.updated_at,
            "can_edit": bool(self._is_counsellor() and n.author_id == self.user.user_id),
        }
        for f in FLAGS:
            d[f] = bool(getattr(n, f))
        return d

    @staticmethod
    def _clean_text(data: Dict[str, Any]) -> None:
        for key, limit, label in (("verse_reference", MAX_VERSE, "La reference du verset"),
                                  ("content", MAX_CONTENT, "Le texte")):
            if key in data and data[key] is not None:
                v = str(data[key]).strip()
                if len(v) > limit:
                    raise ValueError(f"{label} depasse {limit} caracteres.")
                data[key] = v or None

    def _own_note(self, note_id: int) -> SpiritualNote:
        note = self.repo.get(note_id)
        if note is None:
            raise SpiritualNoteNotFoundError("Note introuvable.")
        if not self._is_counsellor() or note.author_id != self.user.user_id:
            raise PermissionError("Seul l'auteur peut modifier ou supprimer sa note.")
        return note

    @staticmethod
    def _audit_info(n: SpiritualNote) -> Dict[str, Any]:
        return {"note_id": n.id, "meeting_date": n.meeting_date.isoformat(), "author_id": n.author_id}

    # ---- lecture ----
    def list_notes(self, page: int, per_page: int) -> Dict[str, Any]:
        rows, total = self.repo.list_page(page, per_page)
        return {
            "data": [self._dict(n, name) for n, name in rows],
            "total": total, "page": page, "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    def get_note(self, note_id: int) -> Dict[str, Any]:
        note = self.repo.get(note_id)
        if note is None:
            raise SpiritualNoteNotFoundError("Note introuvable.")
        return self._dict(note, self.repo.author_name(note.author_id))

    # ---- ecriture ----
    def create_note(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            data = dict(data)
            today = business_today()
            meeting = _parse_date(data["meeting_date"], today) if "meeting_date" in data else today
            self._clean_text(data)
            note = SpiritualNote(author_id=self.user.user_id, meeting_date=meeting)
            for f in FLAGS:
                if data.get(f) is not None:
                    setattr(note, f, bool(data[f]))
            note.verse_reference = data.get("verse_reference")
            note.content = data.get("content")
            self.repo.add(note)
            self.audit_repo.log_user_action(
                current_user=self.user, resource_type=RESOURCE_TYPE, action_performed="CREATE",
                resource_id=note.id, new_values=self._audit_info(note))
            out = self._dict(note, self.repo.author_name(note.author_id))
            self.session.commit()
            return out
        except Exception:
            self.session.rollback()
            raise

    def update_note(self, note_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            note = self._own_note(note_id)
            data = dict(data)
            if "meeting_date" in data:
                today = business_today()
                raw = data["meeting_date"]
                unchanged = isinstance(raw, str) and raw.strip() == note.meeting_date.isoformat()
                if not unchanged:
                    note.meeting_date = _parse_date(raw, today)
            self._clean_text(data)
            for f in FLAGS:
                if data.get(f) is not None:
                    setattr(note, f, bool(data[f]))
            for k in ("verse_reference", "content"):
                if k in data:
                    setattr(note, k, data[k])
            note.updated_at = datetime.utcnow()
            self.session.flush()
            self.audit_repo.log_user_action(
                current_user=self.user, resource_type=RESOURCE_TYPE, action_performed="UPDATE",
                resource_id=note.id, new_values=self._audit_info(note))
            out = self._dict(note, self.repo.author_name(note.author_id))
            self.session.commit()
            return out
        except Exception:
            self.session.rollback()
            raise

    def delete_note(self, note_id: int) -> None:
        try:
            note = self._own_note(note_id)
            info = self._audit_info(note)
            self.repo.delete(note)
            self.audit_repo.log_user_action(
                current_user=self.user, resource_type=RESOURCE_TYPE, action_performed="DELETE",
                resource_id=info["note_id"], old_values=info)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
