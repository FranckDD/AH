# api_backend/backend_app/routes/spiritual_notes/spiritual_notes_endpoints.py
"""Routeur /spiritual-notes : notes de rencontres du conseiller spirituel.

Lecture : SpiritualCounsellor, promoteur, admin. Ecriture : SpiritualCounsellor seulement,
et seulement sur ses propres notes (regle d'auteur dans le controleur).
Erreurs : LookupError -> 404, PermissionError -> 403, ValueError -> 422.
"""
from contextlib import contextmanager
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from controller.spiritual_note_controller import SpiritualNoteController
from repositories.audit_repo import AuditRepository
from repositories.spiritual_note_repo import SpiritualNoteRepository

from .spiritual_notes_schemas import NoteBody

router = APIRouter(prefix="/spiritual-notes", tags=["Notes spirituelles"])

READERS = ("SpiritualCounsellor", "promoteur", "admin")
WRITERS = ("SpiritualCounsellor",)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_spiritual_note_controller(
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SpiritualNoteController:
    return SpiritualNoteController(SpiritualNoteRepository(db), AuditRepository(db), current_user)


@contextmanager
def _errors():
    try:
        yield
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/", dependencies=[Depends(role_required(*READERS))])
def list_notes(page: int = Query(1, ge=1, le=1_000_000), per_page: int = Query(20, ge=1, le=100),
               ctrl: SpiritualNoteController = Depends(get_spiritual_note_controller)):
    with _errors():
        return ctrl.list_notes(page, per_page)


@router.get("/{note_id}", dependencies=[Depends(role_required(*READERS))])
def get_note(note_id: int, ctrl: SpiritualNoteController = Depends(get_spiritual_note_controller)):
    with _errors():
        return ctrl.get_note(note_id)


@router.post("/", status_code=status.HTTP_201_CREATED, dependencies=[Depends(role_required(*WRITERS))])
def create_note(payload: NoteBody, ctrl: SpiritualNoteController = Depends(get_spiritual_note_controller)):
    with _errors():
        return ctrl.create_note(payload.model_dump(exclude_unset=True))


@router.put("/{note_id}", dependencies=[Depends(role_required(*WRITERS))])
def update_note(note_id: int, payload: NoteBody,
                ctrl: SpiritualNoteController = Depends(get_spiritual_note_controller)):
    with _errors():
        return ctrl.update_note(note_id, payload.model_dump(exclude_unset=True))


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(role_required(*WRITERS))])
def delete_note(note_id: int, ctrl: SpiritualNoteController = Depends(get_spiritual_note_controller)):
    with _errors():
        ctrl.delete_note(note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
