# api_backend/backend_app/routes/spiritual_notes/spiritual_notes_schemas.py
"""Entrees strictes du routeur /spiritual-notes (extra=forbid).

La date reste une valeur brute : le controleur la valide et renvoie un message clair (422).
Les longueurs (verset 120, texte 5000) sont aussi bornees ici."""
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class NoteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting_date: Any = None
    counsel: Optional[bool] = None
    prayer: Optional[bool] = None
    verse_read: Optional[bool] = None
    discussion: Optional[bool] = None
    text_given: Optional[bool] = None
    qa: Optional[bool] = None
    no_one_spoke: Optional[bool] = None
    verse_reference: Optional[str] = Field(None, max_length=120)
    content: Optional[str] = Field(None, max_length=5000)
