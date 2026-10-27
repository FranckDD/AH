# Fichier: routes/toxico_routes.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Request
from typing import List, Any, Dict, Optional, Literal
from sqlalchemy.orm import Session
from datetime import date, datetime
from fastapi.responses import Response, FileResponse, RedirectResponse
import logging
import os
from api_backend.backend_app.utils.file_storage import CONSENT_MAX_BYTES, consent_path, detect_consent_extension
from models.toxico import ToxicoDossier

from api_backend.backend_app.utils.pdf_generator import render_pdf_from_template
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
from controller.config_controller import ConfigController
from repositories.config_repo import ConfigRepository

from api_backend.backend_app.database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required

from controller.toxico_controller import ToxicoController
from repositories.toxico_repo import (ToxicoRepository, ToxicoValidationError, ToxicoConflictError,
                                      ToxicoForbiddenError, ToxicoNotFoundError)
from repositories.patient_repo import PatientRepository
from repositories.audit_repo import AuditRepository 
from controller.patient_controller import PatientController

from api_backend.backend_app.routes.toxico.toxico_schema import (
    PsychologistSimple,
    ToxicoListResponse,
    ToxicoDischargedListResponse,
    ToxicoPreviousListResponse,
    ToxicoAdmissionCreate,
    ToxicoEvaluationCreate,
    ToxicoDischargeRequest,
    ToxicoTransferRequest,
)

# 🟢 GLOBAL : On autorise le Psychologue ici.
router = APIRouter(prefix="/toxico", tags=["Toxicologie"],
                    dependencies=[Depends(role_required("ToxicoManager", "Psychologist", "SpiritualCounsellor", "Assistant", "admin", "promoteur"))])

# Roles "metier toxico" historiques (garde du routeur avant 2026-10-22). Le
# promoteur n'est admis au routeur que pour valider une sortie : il ne voit que
# les listes active/sortis, le detail (sans le texte des evaluations) et le POST
# de sortie. Toute autre route GET qui herite du routeur reprend cette liste.
TOXICO_STAFF_ROLES = ("ToxicoManager", "Psychologist", "SpiritualCounsellor", "Assistant", "admin")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_toxico_controller(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user) 
) -> ToxicoController:
    
    toxico_repo = ToxicoRepository(session=db)
    patient_repo = PatientRepository(session=db) 
    audit_repo = AuditRepository(session=db) 
    
    patient_ctrl = PatientController(
        repo=patient_repo, 
        current_user=current_user,
        audit_repo=audit_repo 
    )

    return ToxicoController(
        repo=toxico_repo,
        patient_controller=patient_ctrl,
        current_user=current_user
    )

# --- ROUTES ---

@router.get("/psychologists", response_model=List[PsychologistSimple], 
            # 🟢 CORRECTION MAJEURE ICI : Ajout de "Psychologist" et "Assistant"
            dependencies=[Depends(role_required("ToxicoManager", "admin", "Psychologist", "SpiritualCounsellor", "Assistant"))])
def get_psychologists(
    ctrl: ToxicoController = Depends(get_toxico_controller) 
):
    return ctrl.get_psychologists_list()

@router.get("/patients", response_model=ToxicoListResponse)
def list_patients(
    search: str = Query(None),
    phase: int = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    # Cette route hérite des permissions du Router (qui incluent déjà Psychologist)
    items, total = ctrl.list_dossiers(search=search, phase=phase, page=page, per_page=per_page)
    data = [ctrl.map_dossier_to_list_item(item) for item in items]
    return {"data": data, "total": total, "page": page, "per_page": per_page}

@router.get("/dossiers/discharged", response_model=ToxicoDischargedListResponse)
def list_discharged(
    search: Optional[str] = Query(None, max_length=100),
    reason: Optional[Literal['guerison', 'abandon', 'exclusion', 'autre']] = Query(None),
    discharged_from: Optional[date] = Query(None),
    discharged_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    # Patients sortis : mêmes rôles que la liste active (garde du routeur).
    if discharged_from and discharged_to and discharged_from > discharged_to:
        raise HTTPException(status_code=422,
                            detail="La date de début doit précéder la date de fin.")
    return ctrl.list_discharged(search=search, reason=reason, discharged_from=discharged_from,
                                discharged_to=discharged_to, page=page, per_page=per_page)

@router.get("/dossiers/previous", response_model=ToxicoPreviousListResponse,
            # Declaree AVANT les routes /dossiers/{dossier_id}/... ; psychologue seulement.
            dependencies=[Depends(role_required("Psychologist"))])
def list_previously_followed(
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    ctrl: ToxicoController = Depends(get_toxico_controller),
):
    """Patients dont l'utilisateur n'est plus referent mais qu'il a suivis
    (transfert, sejour ou evaluation a son nom) : consultation en lecture seule."""
    return ctrl.list_previously_followed(search=search, page=page, per_page=per_page)


READ_ONLY_DETAIL = {"code": "read_only_access",
                    "message": "Consultation en lecture seule : export et consentement indisponibles."}


# --- EXPORTS PDF (2026-10-22) ---

# Plafond dur de l'export liste : au-dela, le PDF le signale (tronque).
DISCHARGED_EXPORT_CAP = 2000

REASON_LABELS = {"guerison": "Guérison", "abandon": "Abandon",
                 "exclusion": "Exclusion", "autre": "Autre"}
DECISION_LABELS = {"PROGRESS": "Progression", "REGRESS": "Régression",
                   "MAINTAIN": "Maintien"}


def _fmt_date(v) -> str:
    if not v:
        return "-"
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y %H:%M")
    if isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    return str(v)


def _discharged_filters_summary(search, reason, discharged_from, discharged_to) -> str:
    parts = []
    if search and search.strip():
        parts.append(f"Recherche : « {search.strip()} »")
    if reason:
        parts.append(f"Motif : {REASON_LABELS.get(reason, reason)}")
    if discharged_from:
        parts.append(f"Sortie à partir du {_fmt_date(discharged_from)}")
    if discharged_to:
        parts.append(f"Sortie jusqu'au {_fmt_date(discharged_to)}")
    return " - ".join(parts) if parts else "Aucun filtre"


def _header_ctx(db: Session) -> dict:
    return get_pdf_header_context(ConfigController(repo=ConfigRepository(db)))


@router.get("/dossiers/discharged/export",
            dependencies=[Depends(role_required(*TOXICO_STAFF_ROLES))])
def export_discharged(
    search: Optional[str] = Query(None, max_length=100),
    reason: Optional[Literal['guerison', 'abandon', 'exclusion', 'autre']] = Query(None),
    discharged_from: Optional[date] = Query(None),
    discharged_to: Optional[date] = Query(None),
    ctrl: ToxicoController = Depends(get_toxico_controller),
    db: Session = Depends(get_db),
):
    """PDF de la liste des patients sortis : memes filtres et memes roles
    (garde du routeur) que GET /dossiers/discharged, toutes les lignes
    (plafond DISCHARGED_EXPORT_CAP, signale sur le PDF)."""
    if discharged_from and discharged_to and discharged_from > discharged_to:
        raise HTTPException(status_code=422,
                            detail="La date de début doit précéder la date de fin.")
    rows, total = ctrl.list_discharged_for_export(
        search=search, reason=reason, discharged_from=discharged_from,
        discharged_to=discharged_to, cap=DISCHARGED_EXPORT_CAP)
    items = []
    for r in rows:
        ls = r.get("last_stay") or {}
        items.append({
            "name": r["patientName"], "code": r.get("code") or "-",
            "admission": _fmt_date(ls.get("admission_date")),
            "discharge": _fmt_date(ls.get("discharge_date")),
            "reason": REASON_LABELS.get(ls.get("discharge_reason"), ls.get("discharge_reason") or "-"),
            "psychologist": ls.get("psychologist_name") or "-",
            "stays_count": r["stays_count"],
        })
    pdf_bytes = render_pdf_from_template("toxico_discharged_export_template.html", {
        **_header_ctx(db),
        "rows": items,
        "total": total,
        "truncated": total > len(items),
        "cap": DISCHARGED_EXPORT_CAP,
        "filters_label": _discharged_filters_summary(search, reason, discharged_from, discharged_to),
        "date_impression": datetime.now().strftime("%d/%m/%Y à %H:%M"),
    })
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=toxico_patients_sortis.pdf"})


def _build_dossier_pdf_context(d: dict) -> dict:
    """Regroupe phases et evaluations (deja serialisees par
    serialize_dossier_details) sous chaque sejour."""
    stays, by_num = [], {}
    for s in d.get("stays") or []:
        entry = {
            "number": s["stay_number"],
            "admission": _fmt_date(s.get("admission_date")),
            "discharge": _fmt_date(s.get("discharge_date")) if s.get("discharge_date") else "En cours",
            "reason": REASON_LABELS.get(s.get("discharge_reason"), s.get("discharge_reason") or "-"),
            "note": s.get("discharge_note") or "",
            "psychologist": s.get("psychologist_name") or "-",
            "substance": s.get("substance") or "-",
            "discharged_by": s.get("discharged_by_name") or "",
            "phases": [], "evaluations": [],
        }
        stays.append(entry)
        by_num[s["stay_number"]] = entry

    raw_stays = d.get("stays") or []
    last_stay = max(raw_stays, key=lambda s: s.get("stay_number") or 0) if raw_stays else None

    # Donnees historiques sans sejour rattache (avant migration 022).
    orphan = {"number": None, "phases": [], "evaluations": []}

    for h in sorted(d.get("phaseHistory") or [], key=lambda h: str(h.get("start_date") or "")):
        by_num.get(h.get("stay_number"), orphan)["phases"].append({
            "phase": h.get("phase"),
            "start": _fmt_date(h.get("start_date")),
            "end": _fmt_date(h.get("end_date")),
            "status": h.get("status") or "-",
            "comments": h.get("comments") or "",
        })
    for e in sorted(d.get("evaluations") or [],
                    key=lambda e: (str(e.get("created_at") or ""), e.get("id") or 0)):
        by_num.get(e.get("stay_number"), orphan)["evaluations"].append({
            "date": _fmt_date(e.get("created_at")),
            "decision": DECISION_LABELS.get(e.get("decision"), e.get("decision") or "-"),
            "observation": e.get("observation") or "",
            "recommendation": e.get("recommendation") or "",
            "phase_before": e.get("phase_before") if e.get("phase_before") is not None else "-",
            "phase_after": e.get("phase_after") if e.get("phase_after") is not None else "-",
            "author": e.get("evaluator_name") or "-",
        })

    return {
        "patient": {
            "name": f"{d.get('firstName') or ''} {d.get('lastName') or ''}".strip(),
            "code": d.get("code") or "-",
            "dob": _fmt_date(d.get("dob")),
        },
        "status": "Actif (en séjour)" if d.get("isActive") else "Sorti (dossier inactif)",
        "current_phase": d.get("currentPhase"),
        "psychologist": d.get("psychologist") or "-",
        "guardian_name": d.get("guardianName") or "",
        "guardian_contact": d.get("guardianContact") or "",
        "stays": stays,
        "orphan": orphan if (orphan["phases"] or orphan["evaluations"]) else None,
        # Changements de psychologue (deja tries du plus recent au plus ancien).
        "transfers": [
            {
                "date": t["decided_at"].strftime("%d/%m/%Y") if isinstance(t.get("decided_at"), (date, datetime))
                        else _fmt_date(t.get("decided_at")),
                "from": t.get("from_name") or "Aucun",
                "to": t.get("to_name") or "-",
                "by": t.get("decided_by_name") or "-",
                "reason": t.get("reason") or "",
            } for t in (d.get("transfers") or [])
        ],
        # Zones de signature (2026-10-22) : psychologue du DERNIER sejour ;
        # responsable administratif = qui a valide la sortie du dernier sejour,
        # seulement si le dossier est sorti (sinon case vierge a signer).
        # Ancien dossier sans sejour (avant migration 022) : psychologue du dossier.
        "sig_psychologist": ((last_stay or {}).get("psychologist_name") or "") if last_stay
                            else (d.get("psychologist") if d.get("psychologist") not in (None, "Non assigné") else ""),
        "sig_discharger": ((last_stay or {}).get("discharged_by_name") or "")
                          if not d.get("isActive") else "",
    }


@router.get("/patients/{patient_id}/export",
            # Evaluations = donnees sensibles : ni Assistant ni accompagnateur spirituel.
            dependencies=[Depends(role_required("Psychologist", "ToxicoManager", "admin"))])
def export_dossier(
    patient_id: int,
    ctrl: ToxicoController = Depends(get_toxico_controller),
    db: Session = Depends(get_db),
):
    access = ctrl.access_for_patient(patient_id)
    if access == 'none':
        raise HTTPException(status_code=404, detail="Dossier Toxico introuvable")
    if access != 'full':
        raise HTTPException(status_code=403, detail=READ_ONLY_DETAIL)
    dossier = ctrl.get_dossier_details(patient_id)
    data = ctrl.serialize_dossier_details(dossier)
    if not data:
        raise HTTPException(status_code=404, detail="Dossier Toxico introuvable")
    pdf_bytes = render_pdf_from_template("toxico_dossier_export_template.html", {
        **_header_ctx(db),
        **_build_dossier_pdf_context(data),
        "date_impression": datetime.now().strftime("%d/%m/%Y à %H:%M"),
    })
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=dossier_toxico_{patient_id}.pdf"})


@router.get("/patients/{patient_id}", response_model=Any)
def get_patient_detail(
    patient_id: int,
    ctrl: ToxicoController = Depends(get_toxico_controller),
):
    # Psychologue limite : None (404 identique a un id inconnu) hors perimetre.
    dossier = ctrl.get_dossier_details(patient_id)
    data = ctrl.serialize_dossier_details(dossier) if dossier else None
    if not data:
        raise HTTPException(status_code=404, detail="Dossier Toxico introuvable")

    # Masquage du texte des evaluations pour le promoteur "pur" : fait dans
    # ToxicoController.serialize_dossier_details (partage avec le dossier consolide).
    return data

logger = logging.getLogger(__name__)
CONSENT_MEDIA_TYPES = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".png": "image/png"}


async def _validate_consent_upload(upload: Optional[UploadFile]) -> None:
    """5 Mo max, et type reel (PDF/JPEG/PNG) d'apres le contenu, avant toute creation de patient ou de fichier."""
    if upload is None or not upload.filename:
        return
    data = await upload.read(CONSENT_MAX_BYTES + 1)
    await upload.seek(0)
    if len(data) > CONSENT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Le fichier de consentement dépasse 5 Mo.")
    if not detect_consent_extension(data[:16]):
        raise HTTPException(status_code=422, detail="Le consentement doit être un PDF, un JPEG ou un PNG.")


@router.get("/dossiers/{dossier_id}/consent",
            # Memes roles que la lecture du detail dossier hors promoteur (TOXICO_STAFF_ROLES).
            dependencies=[Depends(role_required(*TOXICO_STAFF_ROLES))])
def get_consent_file(dossier_id: int,
                     request: Request,
                     db: Session = Depends(get_db),
                     current_user: Any = Depends(get_current_user),
                     ctrl: ToxicoController = Depends(get_toxico_controller)):
    """Consentement signe : jamais servi par /static ; lecture authentifiee et journalisee.
    Psychologue limite : hors perimetre = meme 404 qu'un id inconnu ; lecture seule = 403."""
    access = ctrl.access_for_dossier(dossier_id)
    if access == 'none':
        raise HTTPException(status_code=404, detail="Aucun consentement pour ce dossier.")
    if access != 'full':
        raise HTTPException(status_code=403, detail=READ_ONLY_DETAIL)
    dossier = db.get(ToxicoDossier, dossier_id)
    stored = dossier.consent_file if dossier else None
    if not stored:
        raise HTTPException(status_code=404, detail="Aucun consentement pour ce dossier.")
    if str(stored).startswith("http"):
        target = None  # stockage distant (bucket) : l'URL est deja celle du fichier
    else:
        target = consent_path(stored)
        if not target or not os.path.isfile(target):
            raise HTTPException(status_code=404, detail="Fichier de consentement introuvable.")
    AuditRepository(session=db).log_user_action(
        current_user, "ToxicoConsent", "READ", resource_id=dossier_id,
        ip_address=request.client.host if request.client else None)
    db.commit()
    logger.info("Consentement toxico lu : dossier=%s user=%s", dossier_id, getattr(current_user, "user_id", None))
    if target is None:
        return RedirectResponse(str(stored))
    ext = os.path.splitext(target)[1]
    return FileResponse(target, media_type=CONSENT_MEDIA_TYPES.get(ext, "application/octet-stream"),
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/admission", status_code=status.HTTP_201_CREATED,
             # Psychologist n'est PAS ici, c'est correct (il ne peut pas admettre)
             dependencies=[Depends(role_required("ToxicoManager", "admin", "Assistant"))])
async def admission_patient(
    request: Request,
    patientId: Optional[int] = Form(None),
    firstName: Optional[str] = Form(None),
    lastName: Optional[str] = Form(None),
    dob: Optional[date] = Form(None),
    mothersName: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    admissionDate: date = Form(...),
    substance: str = Form(...),
    psychologist: int = Form(...),
    guardianName: str = Form(...),
    guardianContact: str = Form(...),
    notes: Optional[str] = Form(None),
    consentFile: Optional[UploadFile] = File(None),
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    await _validate_consent_upload(consentFile)
    try:
        data = {
            "patient_id": patientId,
            "firstName": firstName, "lastName": lastName, "dob": dob, "mothersName": mothersName, "gender": gender,
            "address": address, "contact": contact, "admissionDate": admissionDate,
            "substance": substance, "psychologist_id": psychologist,
            "guardianName": guardianName, "guardianContact": guardianContact, "notes": notes
        }
        base_url = str(request.base_url).rstrip("/")
        dossier = await ctrl.admission_patient(data=data, consent_file=consentFile, base_url=base_url) # type: ignore
        return {
            "message": "Réadmission réussie" if dossier.is_readmission else "Admission réussie",
            "code_patient": dossier.patient.code_patient,
            "dossier_id": dossier.id,
            "is_readmission": dossier.is_readmission,
            "stay_number": dossier.stay_number,
        }
    except ToxicoValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ToxicoConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/evaluation", status_code=status.HTTP_200_OK,
             # Regle metier : SEUL le psychologue fait l'evaluation psychologique
             # (ni admin, ni accompagnateur spirituel). La lecture reste ouverte aux autres roles.
             dependencies=[Depends(role_required("Psychologist"))])
def submit_evaluation(
    data: ToxicoEvaluationCreate,
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    try:
        payload = data.model_dump()
        if not payload.get('dossier_id'):
            dossier = ctrl.get_dossier_details(payload['patientId'])
            if not dossier:
                raise ValueError("Dossier introuvable")
            payload['dossier_id'] = dossier.id

        ctrl.submit_evaluation(payload)
        return {"message": "Évaluation enregistrée"}
    except ToxicoForbiddenError as e:  # sous-classe de ValueError : AVANT
        raise HTTPException(status_code=403, detail={"code": e.code, "message": str(e)})
    except ToxicoConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

def _open_hosp_payload(hosp):
    if hosp is None:
        return None
    return {"hospitalization_id": hosp.id,
            "admitted_at": hosp.admitted_at.isoformat() if hosp.admitted_at else None}


@router.get("/dossiers/{dossier_id}/open-hospitalization",
            dependencies=[Depends(role_required("ToxicoManager", "admin", "promoteur"))])
def get_open_hospitalization(dossier_id: int, ctrl: ToxicoController = Depends(get_toxico_controller)):
    """Indicateur minimal (aucune donnee medicale) : le patient du dossier a-t-il
    un sejour hospitalier ouvert ? Le ToxicoManager n'a pas acces a /hospitalizations."""
    try:
        hosp = ctrl.get_open_hospitalization(dossier_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    payload = _open_hosp_payload(hosp)
    return {"open": hosp is not None,
            "hospitalization_id": payload["hospitalization_id"] if payload else None,
            "admitted_at": payload["admitted_at"] if payload else None}


@router.post("/discharge/{dossier_id}", status_code=status.HTTP_200_OK,
             # 2026-10-22 : le promoteur peut valider une sortie (responsable administratif).
             dependencies=[Depends(role_required("ToxicoManager", "admin", "promoteur"))])
def discharge_patient(
    dossier_id: int,
    body: ToxicoDischargeRequest,
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    try:
        open_hosp = ctrl.discharge_patient(dossier_id, body.reason, body.note, body.discharge_date)
        return {"message": "Dossier clôturé avec succès.",
                "open_hospitalization": _open_hosp_payload(open_hosp)}
    except ToxicoValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ToxicoConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.post("/dossiers/{dossier_id}/transfer", status_code=status.HTTP_200_OK,
             dependencies=[Depends(role_required("ToxicoManager", "admin"))])
def transfer_dossier(
    dossier_id: int,
    body: ToxicoTransferRequest,
    ctrl: ToxicoController = Depends(get_toxico_controller),
):
    """Transfere un patient a un autre psychologue (historique + notification, une transaction)."""
    try:
        row = ctrl.transfer_dossier(dossier_id, body.to_psychologist_id, body.reason)
    except ToxicoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ToxicoValidationError as e:
        raise HTTPException(status_code=422, detail={"code": e.code, "message": str(e)})
    except ToxicoConflictError as e:
        raise HTTPException(status_code=409, detail={"code": e.code, "message": str(e)})
    return {"message": "Patient transféré.", "transfer": row}

@router.get("/stats/dashboard",response_model=Dict[str, Any], tags=["ToxicoStats"])
def get_dashboard_stats(ctrl: ToxicoController = Depends(get_toxico_controller)):
    # Compteur agrege (aucune donnee nominative) : ouvert aussi au promoteur,
    # la page liste toxico l'appelle au chargement.
    # Hérite des permissions globales du router (donc Psychologist OK)
    return ctrl.get_dashboard_stats()