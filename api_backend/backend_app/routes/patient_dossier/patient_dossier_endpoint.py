from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from datetime import datetime
from fastapi.responses import Response
from api_backend.backend_app.utils.pdf_generator import render_pdf_from_template
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
from api_backend.backend_app.utils.dossier_excel_export import build_dossier_excel
from controller.config_controller import ConfigController
from repositories.config_repo import ConfigRepository

from api_backend.backend_app.database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from controller.auth_controller import AuthController
from controller.patient_controller import PatientController
from controller.medical_controller import MedicalRecordController
from controller.prescription_controller import PrescriptionController
from controller.lab_controller import LabController
from controller.cs_controller import ConsultationSpirituelController
from controller.toxico_controller import ToxicoController
from controller.patient_dossier_controller import PatientDossierController
from repositories.audit_repo import AuditRepository
from repositories.medical_repo import MedicalRecordRepository
from repositories.prescription_repo import PrescriptionRepository
from repositories.lab_repo import LabRepository
from repositories.cs_repo import ConsultationSpirituelRepository
from repositories.toxico_repo import ToxicoRepository

# Routeur separe de patients_endpoints.py : ce dernier porte une
# dependance de ROUTEUR (role_required(...)) qui s'ET-erait avec toute
# route ajoutee ici, restreignant l'acces a l'intersection des deux
# listes au lieu de leur union (chantier 6, meme constat qu'au chantier 5
# pour routes/finance/).
router = APIRouter(prefix="/patients", tags=["Dossier patient"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_patient_dossier_controller(
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientDossierController:
    auth_ctrl = AuthController(db_session=db)
    audit_repo = AuditRepository(db)
    patient_ctrl = PatientController(repo=auth_ctrl.patient_repo, current_user=current_user, audit_repo=audit_repo)
    medical_ctrl = MedicalRecordController(
        repo=MedicalRecordRepository(db), patient_controller=patient_ctrl,
        current_user=current_user, audit_repo=audit_repo,
    )
    prescription_ctrl = PrescriptionController(
        repo=PrescriptionRepository(db), patient_controller=patient_ctrl,
        current_user=current_user, audit_repo=audit_repo,
    )
    lab_ctrl = LabController(repo=LabRepository(db), current_user=current_user)
    cs_ctrl = ConsultationSpirituelController(
        repo=ConsultationSpirituelRepository(session=db), patient_controller=patient_ctrl,
        current_user=current_user,
    )
    toxico_ctrl = ToxicoController(
        repo=ToxicoRepository(session=db), patient_controller=patient_ctrl, current_user=current_user,
    )
    return PatientDossierController(
        patient_ctrl=patient_ctrl, medical_ctrl=medical_ctrl, prescription_ctrl=prescription_ctrl,
        lab_ctrl=lab_ctrl, cs_ctrl=cs_ctrl, toxico_ctrl=toxico_ctrl,
        audit_repo=audit_repo, current_user=current_user,
    )


@router.get(
    "/{patient_id}/dossier",
    response_model=Any,
    dependencies=[Depends(role_required(
        "medecin", "nurse", "psychologist", "spiritualcounsellor",
        "toxicomanager", "laborantin", "assistant", "admin", "promoteur",
    ))],
)
def get_patient_dossier(
    patient_id: int,
    ctrl: PatientDossierController = Depends(get_patient_dossier_controller),
):
    """Dossier consolide : les 6 domaines en un appel, tolerant aux pannes
    par domaine, journalise (politique d'acces 2026-09-15 - soignants +
    admin + promoteur, secretariat exclu, tracabilite forte)."""
    try:
        return ctrl.get_full_dossier(patient_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{patient_id}/dossier/export",
    dependencies=[Depends(role_required(
        "medecin", "nurse", "psychologist", "spiritualcounsellor",
        "toxicomanager", "laborantin", "assistant", "admin", "promoteur",
    ))],
)
def export_patient_dossier(
    patient_id: int,
    format: str = Query(..., regex="^(pdf|excel)$"),
    ctrl: PatientDossierController = Depends(get_patient_dossier_controller),
    db: Session = Depends(get_db),
):
    try:
        dossier = ctrl.get_full_dossier(patient_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if format == "excel":
        excel_bytes = build_dossier_excel(dossier)
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=dossier_{patient_id}.xlsx"},
        )

    config_ctrl = ConfigController(repo=ConfigRepository(db))
    header_ctx = get_pdf_header_context(config_ctrl)

    pdf_bytes = render_pdf_from_template('dossier_export_template.html', {
        **header_ctx,
        "patient": dossier.get("patient") or {},
        "historique_medical": dossier.get("historique_medical"),
        "prescriptions": dossier.get("prescriptions"),
        "historique_labo": dossier.get("historique_labo"),
        "dossier_toxico": dossier.get("dossier_toxico"),
        "historique_spirituel": dossier.get("historique_spirituel"),
        "date_impression": datetime.now().strftime("%d/%m/%Y à %H:%M"),
    })
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=dossier_{patient_id}.pdf"},
    )
