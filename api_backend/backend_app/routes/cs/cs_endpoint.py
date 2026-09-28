# api_backend/app/routes/consultations/consultations_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
import logging
from typing import List, Any, Optional

import csv
import io
from datetime import date as date_type, datetime
from fastapi.responses import Response, StreamingResponse
from api_backend.backend_app.utils.pdf_generator import render_pdf_from_template
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
from controller.config_controller import ConfigController
from repositories.config_repo import ConfigRepository

from ...database import SessionLocal
from controller.auth_controller import AuthController
from controller.patient_controller import PatientController
from controller.cs_controller import ConsultationSpirituelController
from repositories.cs_repo import ConsultationSpirituelRepository
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user,role_required
from api_backend.backend_app.exceptions import translate_integrity_error

from .mapping import normalize_consultation_data
from ..cs.schemas_cs import   ConsultationCreate,ConsultationUpdate,ConsultationResponse,PrayerBookTypeResponse,ConsultationListResponse

logger = logging.getLogger(__name__)

#router = APIRouter( prefix="/consultations",    tags=["Consultations"],    dependencies=[Depends(get_current_user)],)
router = APIRouter(
    prefix="/cs",
    tags=["Consultation spirituelle"],
    # "medecin"/"nurse" retires (chantier perimetre medical, decision
    # utilisateur 2026-09-22) : le spirituel ne les concerne pas, meme
    # motif que le retrait deja fait du dossier consolide et des onglets
    # patients. Aucune route de ce fichier n'a de dependance propre qui
    # les mentionnait, donc ce seul changement ferme tout le module.
    dependencies=[Depends(role_required("secretaire", "admin", "SpiritualCounsellor"))]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_consultation_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsultationSpirituelController:
    """
    Construit le controller de consultation en réutilisant AuthController pour
    récupérer les repos liés (ex: patient_repo) afin de respecter la
    séparation repo/controller présente dans le projet.
    """
    auth_ctrl = AuthController(db_session=db)
    # patient controller utile au controller de consultations (injection)
    patient_ctrl = PatientController(repo=auth_ctrl.patient_repo, current_user=current_user)
    cs_repo = ConsultationSpirituelRepository(session=db)
    return ConsultationSpirituelController(repo=cs_repo, patient_controller=patient_ctrl, current_user=current_user)


def _safe_validate_consultation(raw: Any) -> ConsultationResponse:
    """
    Normalise & valide une consultation pour éviter ResponseValidationError.
    - normalise (dates, tableaux, etc) via normalize_consultation_data
    - tente model_validate (pydantic v2)
    - si ValidationError, applique heuristique pour nuller certains champs et retenter
    """
    data = normalize_consultation_data(raw)
    try:
        return ConsultationResponse.model_validate(data)
    except ValidationError as ve:
        errors = ve.errors()
        to_null = set()
        for e in errors:
            loc = e.get("loc", ())
            if not loc:
                continue
            # heuristique : si problème sur fields optionnels list/array ou created_by_name => nuller
            if "presc_generic" in loc or "presc_med_spirituel" in loc or "created_by_name" in loc:
                to_null.add(loc[-1])
        if to_null:
            for k in to_null:
                data[k] = None
            try:
                return ConsultationResponse.model_validate(data)
            except ValidationError:
                logger.exception("Failed to auto-correct consultation data after nulling fields: %s", to_null)
                raise HTTPException(status_code=500, detail="Erreur interne : données consultation invalides")
        logger.exception("Unrecoverable response validation error for consultation: %s -- errors: %s", data, errors)
        raise HTTPException(status_code=500, detail="Erreur interne : données consultation invalides")
    


@router.get("/prayer-book-types")
def get_prayer_book_types(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # obligatoire si tu as l'authentification
):
    repo = ConsultationSpirituelRepository(session=db)
    books = repo.get_prayer_book_types()  # ta méthode qui fait query(PrayerBookType).all()
    return [{"type_code": b.type_code, "label": b.label} for b in books]    


@router.get("/", response_model=ConsultationListResponse)
def list_consultations(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=200),
    search: Optional[str] = Query(None),
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    """
    Retourne la liste paginee des consultations, avec le total reel.
    Pagination toujours en memoire cote endpoint (dette connue, hors
    perimetre de ce chantier) : le controller charge la liste complete
    avant de la decouper, donc le total exact est disponible sans cout
    de requete supplementaire.

    "search" (registre J1) : etait deja declare ici mais jamais transmis
    au controller - la recherche cote frontend n'avait donc jamais d'effet.
    """
    all_raw = cs_ctrl.list_consultations(search=search)
    total = len(all_raw)
    start = (page - 1) * per_page
    page_items = all_raw[start:start + per_page]
    validated = [ _safe_validate_consultation(item) for item in page_items ]
    return {
        "data": validated,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 1,
    }


@router.get("/patient/{patient_id}", response_model=List[ConsultationResponse])
def list_for_patient(
    patient_id: int,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    raws = cs_ctrl.list_for_patient(patient_id)
    return [ _safe_validate_consultation(r) for r in raws ]


@router.get("/last/{patient_id}", response_model=Optional[ConsultationResponse])
def get_last_for_patient(
    patient_id: int,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    last = cs_ctrl.get_last_for_patient(patient_id)
    if not last:
        return None
    return _safe_validate_consultation(last)

@router.get("/patient/{patient_id}/history", response_model=List[ConsultationResponse])
def get_spiritual_history(
    patient_id: int,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    try:
        # Appel au controller (utilise get_patient_history qui trie par date)
        raws = cs_ctrl.get_patient_history(patient_id)
        
        # Sécurité : Si None, on renvoie une liste vide
        if raws is None:
            return []
            
        # Conversion et validation
        return [ _safe_validate_consultation(r) for r in raws ]
        
    except Exception as e:
        logger.exception("Erreur lors de la récupération de l'historique spirituel")
        return [] # On renvoie vide plutôt que de planter


@router.get("/export")
def export_consultations(
    format: str = Query(..., regex="^(pdf|csv)$"),
    search: Optional[str] = Query(None),
    date_from: Optional[date_type] = Query(None),
    date_to: Optional[date_type] = Query(None),
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
    db: Session = Depends(get_db),
):
    raw = cs_ctrl.list_consultations_for_export(search=search, date_from=date_from, date_to=date_to)
    items = [normalize_consultation_data(c) for c in raw]

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Patient", "Code", "Type", "Date", "Intervenant"])
        for c in items:
            writer.writerow([
                c.get("patient_name") or f"#{c.get('patient_id')}", c.get("patient_code") or "",
                c.get("type_consultation"), c.get("consultation_date"), c.get("created_by_name"),
            ])
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=consultations_export.csv"},
        )

    config_ctrl = ConfigController(repo=ConfigRepository(db))
    header_ctx = get_pdf_header_context(config_ctrl)

    if date_from and date_to:
        periode_label = f"Période du {date_from} au {date_to}"
    elif date_from:
        periode_label = f"Depuis le {date_from}"
    elif date_to:
        periode_label = f"Jusqu'au {date_to}"
    else:
        periode_label = "Toutes périodes"

    pdf_bytes = render_pdf_from_template('cs_export_template.html', {
        **header_ctx,
        "consultations": items,
        "periode_label": periode_label,
        "date_impression": datetime.now().strftime("%d/%m/%Y à %H:%M"),
    })
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=consultations_export.pdf"},
    )


@router.get("/{cs_id}", response_model=ConsultationResponse)
def get_consultation(
    cs_id: int,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    try:
        cs = cs_ctrl.get_consultation(cs_id)
        return _safe_validate_consultation(cs)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
def create_consultation(
    data: ConsultationCreate,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    try:
        cs = cs_ctrl.create_consultation(data.model_dump())
        # cs devrait être l'objet ORM retourné par le repo
        return _safe_validate_consultation(cs)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except IntegrityError as ie:
        try:
            cs_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        raise translate_integrity_error(ie)
    except SQLAlchemyError as e:
        try:
            cs_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError creating consultation: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la création de la consultation")


@router.put("/{cs_id}", response_model=ConsultationResponse)
def update_consultation(
    cs_id: int,
    data: ConsultationUpdate,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    try:
        updated = cs_ctrl.update_consultation(cs_id, data.model_dump(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Consultation non trouvée après mise à jour")
        return _safe_validate_consultation(updated)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except IntegrityError as ie:
        try:
            cs_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        raise translate_integrity_error(ie)
    except SQLAlchemyError as e:
        try:
            cs_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError updating consultation: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la mise à jour de la consultation")


@router.delete("/{cs_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consultation(
    cs_id: int,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    cs = cs_ctrl.delete_consultation(cs_id)
    if not cs:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")
    return None

# Ajoute cet endpoint (juste après les autres @router.get par exemple)

