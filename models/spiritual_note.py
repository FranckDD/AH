# models/spiritual_note.py
"""Notes du conseiller spirituel (migration 035)."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Boolean, ForeignKey, CheckConstraint, Index, func, text
from .database import Base


class SpiritualNote(Base):
    __tablename__ = 'spiritual_notes'
    __table_args__ = (
        CheckConstraint("content IS NULL OR char_length(content) <= 5000",
                        name="spiritual_notes_content_len_check"),
        Index("idx_spiritual_notes_author", "author_id"),
    )

    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    meeting_date = Column(Date, nullable=False)
    counsel = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    prayer = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    verse_read = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    discussion = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    text_given = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    qa = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    verse_reference = Column(String(120), nullable=True)
    no_one_spoke = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
