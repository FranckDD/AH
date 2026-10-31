# api_backend/backend_app/routes/labo/pregnancy_report_endpoints.py
"""Rapport de subvention (grossesse) : patientes enceintes ayant au moins un resultat de laboratoire VALIDE
dans la periode. Reserve au promoteur et a l'admin ; usage interne et nominatif.

  GET /labo/reports/pregnancy?from=YYYY-MM-DD&to=YYYY-MM-DD       -> JSON
  GET /labo/reports/pregnancy.pdf?from=YYYY-MM-DD&to=YYYY-MM-DD   -> PDF (en-tete dynamique)

Un resultat est valide quand `lab_results.status = 'completed'` ; sa date de validation est `test_date`
(posee a la validation, heure naive de Douala comme toutes les heures metier). La periode est inclusive
(de minuit de `from` a 23h59 de `to`, Douala), 366 jours au plus, 2000 lignes au plus.

Appartenance au rapport = grossesse A LA RECEPTION, jamais le statut actuel du dossier :
`lab_results.pregnancy_status_at_result = 'enceinte'` (cliche pose a l'enregistrement de la demande, migration 042),
ou une SA superieure a 0 portee par le resultat. Une patiente devenue "non enceinte" apres l'accouchement reste
donc dans les mois ou elle l'etait, et un statut pose plus tard ne remonte pas dans le passe. Les lignes anterieures
a la migration n'ont pas de cliche (NULL) : seules celles qui portent une SA comptent. Les patients supprimes sont
exclus. Chaque consultation (JSON et PDF) est inscrite au journal d'audit (sans aucun nom) et la reponse n'est
jamais mise en cache. Les routes sont gardees par `role_required` : le filtre central de grossesse les classe
donc en lecteurs.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import role_required
from api_backend.backend_app.utils.pdf_generator import render_pdf_from_template
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
from controller.config_controller import ConfigController
from models.lab import LabResult
from repositories.audit_repo import AuditRepository
from repositories.config_repo import ConfigRepository
from utils.business_time import business_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/labo/reports", tags=["labo-reports"])

MAX_RANGE_DAYS = 366
MAX_ROWS = 2000
# Garde-fou de lecture : jamais plus de MAX_RESULT_ROWS resultats charges pour construire le rapport.
MAX_RESULT_ROWS = 20000
NO_STORE_HEADERS = {"Cache-Control": "no-store, private", "Pragma": "no-cache"}
UNNAMED = "Nom non renseigne"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def parse_period(date_from: str, date_to: str) -> Tuple[date, date]:
    """Dates AAAA-MM-JJ, from <= to, 366 jours au plus (bornes comprises) ; sinon 422."""
    try:
        d1 = date.fromisoformat((date_from or "").strip())
        d2 = date.fromisoformat((date_to or "").strip())
    except ValueError:
        raise HTTPException(status_code=422, detail="Dates invalides (format AAAA-MM-JJ).")
    if d2 < d1:
        raise HTTPException(status_code=422, detail="La date de fin precede la date de debut.")
    if (d2 - d1).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(status_code=422, detail=f"Periode trop longue ({MAX_RANGE_DAYS} jours au maximum).")
    return d1, d2


def _clean(value: Any) -> str:
    return " ".join(str(value).split()) if value not in (None, "") else ""


def _as_dict(value: Any) -> Dict[str, Any]:
    """JSON de resultat : seul un objet est exploitable, tout autre contenu est traite comme vide."""
    return value if isinstance(value, dict) else {}


def _int_weeks(value: Any) -> Optional[int]:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _too_many_message() -> str:
    return (f"Trop de lignes pour un seul rapport (plus de {MAX_ROWS}). "
            "Reduisez la periode et recommencez.")


def build_pregnancy_rows(db: Session, d1: date, d2: date) -> List[Dict[str, Any]]:
    """Une ligne par patiente et par jour de validation (ses examens valides ce jour-la regroupes).
    Grossesse a la reception (cliche `pregnancy_status_at_result` ou SA > 0), patients supprimes exclus."""
    start = datetime.combine(d1, datetime.min.time())
    end = datetime.combine(d2 + timedelta(days=1), datetime.min.time())
    from models.patient import Patient

    results = (
        db.query(LabResult)
        .options(joinedload(LabResult.patient), joinedload(LabResult.examen))
        .outerjoin(Patient, Patient.patient_id == LabResult.patient_id)
        .filter(
            LabResult.status == "completed",
            LabResult.test_date >= start,
            LabResult.test_date < end,
            or_(LabResult.pregnancy_status_at_result == "enceinte", LabResult.gestational_age_weeks > 0),
            # Resultat d'un patient externe, ou d'un patient interne non supprime
            or_(LabResult.patient_id.is_(None), func.coalesce(Patient.is_deleted, False).is_(False)),
        )
        .order_by(LabResult.test_date, LabResult.result_id)
        .limit(MAX_RESULT_ROWS + 1)
        .all()
    )
    if len(results) > MAX_RESULT_ROWS:
        raise HTTPException(status_code=422, detail=_too_many_message())

    grouped: Dict[tuple, Dict[str, Any]] = {}
    for r in results:
        day = r.test_date.date()
        preg = _as_dict(r.external_pregnancy_info)
        if r.patient is not None:
            p = r.patient
            key = ("i", p.patient_id, day)
            base = {
                "patient_number": p.code_patient or "",
                "patient_name": _clean(f"{p.last_name or ''} {p.first_name or ''}") or UNNAMED,
                "external": False,
                "pregnancy_program_number": p.pregnancy_program_number or "",
            }
            identity = ("i", p.patient_id)
        else:
            info = _as_dict(r.external_patient_info)
            name = _clean(f"{info.get('nom') or info.get('name') or ''} {info.get('prenom') or info.get('first_name') or ''}")
            prog = _clean(preg.get("pregnancy_program_number"))
            # Une ligne par reception (batch) et par jour : deux homonymes ne fusionnent pas, et la meme
            # patiente avec ou sans numero de suivi ne se scinde pas.
            key = ("e", str(r.batch_id or f"r{r.result_id}"), day)
            base = {"patient_number": "", "patient_name": name or UNNAMED, "external": True,
                    "pregnancy_program_number": prog}
            identity = ("e", name.lower(), prog.lower()) if name else ("e", str(r.batch_id or r.result_id))
        row = grouped.setdefault(key, {
            **base, "gestational_age_weeks": None, "exams": [], "validated_on": day.isoformat(),
            "_identity": identity,
        })
        if row["external"] and not row["pregnancy_program_number"] and base["pregnancy_program_number"]:
            row["pregnancy_program_number"] = base["pregnancy_program_number"]
        sa = _int_weeks(r.gestational_age_weeks)
        if sa is None and r.patient is None:
            sa = _int_weeks(preg.get("gestational_age_weeks"))
        if sa is not None:
            row["gestational_age_weeks"] = sa if row["gestational_age_weeks"] is None else max(row["gestational_age_weeks"], sa)
        name_ex = r.examen.nom if r.examen is not None else (r.test_type or "")
        if name_ex and name_ex not in row["exams"]:
            row["exams"].append(name_ex)
    rows = list(grouped.values())
    if len(rows) > MAX_ROWS:
        raise HTTPException(status_code=422, detail=_too_many_message())
    rows.sort(key=lambda x: (x["validated_on"], x["patient_name"].lower()))
    return rows


def _payload(db: Session, d1: date, d2: date) -> Dict[str, Any]:
    rows = build_pregnancy_rows(db, d1, d2)
    patients = {r["_identity"] for r in rows}
    out_rows = [{k: v for k, v in r.items() if k != "_identity"} for r in rows]
    return {"from": d1.isoformat(), "to": d2.isoformat(), "total_rows": len(out_rows),
            "total_patients": len(patients), "rows": out_rows}


def _fr(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


def _audit(db: Session, user: Any, request: Request, data: Dict[str, Any], fmt: str) -> None:
    """Journal d'acces au rapport nominatif : qui, quelle periode, quel format, combien de lignes. Aucun nom."""
    try:
        ip = request.client.host if request.client else None
        AuditRepository(db).log_user_action(
            current_user=user,
            resource_type="PregnancyReport",
            action_performed="VIEW" if fmt == "json" else "EXPORT",
            ip_address=ip,
            new_values={"from": data["from"], "to": data["to"], "format": fmt,
                        "rows": data["total_rows"], "patients": data["total_patients"]},
            details=f"Rapport de grossesse {fmt} du {data['from']} au {data['to']} ({data['total_rows']} lignes)",
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Journal d'audit du rapport de grossesse non ecrit")
        # Un acces non journalise est refuse : le rapport est nominatif.
        raise HTTPException(status_code=500, detail="Journal d'audit indisponible : rapport non delivre.")


@router.get("/pregnancy")
def pregnancy_report(
    request: Request,
    response: Response,
    date_from: str = Query(..., alias="from"),
    date_to: str = Query(..., alias="to"),
    db: Session = Depends(get_db),
    user=Depends(role_required("promoteur", "admin")),
):
    d1, d2 = parse_period(date_from, date_to)
    data = _payload(db, d1, d2)
    _audit(db, user, request, data, "json")
    for k, v in NO_STORE_HEADERS.items():
        response.headers[k] = v
    return data


@router.get("/pregnancy.pdf")
def pregnancy_report_pdf(
    request: Request,
    date_from: str = Query(..., alias="from"),
    date_to: str = Query(..., alias="to"),
    db: Session = Depends(get_db),
    user=Depends(role_required("promoteur", "admin")),
):
    d1, d2 = parse_period(date_from, date_to)
    data = _payload(db, d1, d2)
    header_ctx = get_pdf_header_context(ConfigController(repo=ConfigRepository(db)))
    rows = [{**r, "validated_fr": _fr(r["validated_on"]), "exams_text": ", ".join(r["exams"])} for r in data["rows"]]
    try:
        pdf = render_pdf_from_template("pregnancy_report_template.html", {
            **header_ctx,
            "rows": rows,
            "period_label": f"{_fr(data['from'])} au {_fr(data['to'])}",
            "total_rows": data["total_rows"],
            "total_patients": data["total_patients"],
            "printed_on": business_now().strftime("%d/%m/%Y %H:%M"),
        })
    except Exception:
        logger.exception("Erreur de generation du PDF du rapport de grossesse")
        raise HTTPException(status_code=500, detail="Erreur lors de la creation du document PDF")
    _audit(db, user, request, data, "pdf")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="rapport_grossesse_{data["from"]}_{data["to"]}.pdf"',
                 **NO_STORE_HEADERS},
    )
