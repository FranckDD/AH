# repositories/spiritual_note_repo.py
"""Acces donnees des notes du conseiller spirituel. Ne commit jamais."""
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from models.spiritual_note import SpiritualNote
from models.user import User


class SpiritualNoteRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, note: SpiritualNote) -> SpiritualNote:
        self.session.add(note)
        self.session.flush()
        return note

    def get(self, note_id: int) -> Optional[SpiritualNote]:
        return self.session.query(SpiritualNote).filter(SpiritualNote.id == note_id).one_or_none()

    def delete(self, note: SpiritualNote) -> None:
        self.session.delete(note)
        self.session.flush()

    def author_name(self, author_id: int) -> Optional[str]:
        u = self.session.query(User).filter(User.user_id == author_id).one_or_none()
        return u.full_name if u else None

    def list_page(self, page: int, per_page: int) -> Tuple[List[Tuple[SpiritualNote, Optional[str]]], int]:
        total = self.session.query(SpiritualNote).count()
        rows = (self.session.query(SpiritualNote, User.full_name)
                .outerjoin(User, User.user_id == SpiritualNote.author_id)
                .order_by(SpiritualNote.meeting_date.desc(), SpiritualNote.created_at.desc(),
                          SpiritualNote.id.desc())
                .offset((page - 1) * per_page).limit(per_page).all())
        return [(n, name) for n, name in rows], total
