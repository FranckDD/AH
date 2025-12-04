# Fichier: routes/toxico_routes.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Any,Dict
from sqlalchemy.orm import Session
from fastapi import Request

from api_backend.backend_app.database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required

from controller.toxico_controller import ToxicoController
from repositories.toxico_repo import ToxicoRepository
from repositories.patient_repo import PatientRepository
from repositories.audit_repo import AuditRepository 
from controller.patient_controller import PatientController
from controller.auth_controller import AuthController 

from api_backend.backend_app.routes.toxico.toxico_schema import (
    PsychologistSimple,
    ToxicoListResponse,
    ToxicoDossierDetail,
    ToxicoAdmissionCreate,
    ToxicoEvaluationCreate
)

router = APIRouter(prefix="/toxico", tags=["Toxicologie"],
                    dependencies=[Depends(role_required("ToxicoManager", "Psychologist", "SpiritualCounsellor", "Assistant", "admin"))])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_toxico_controller(
    # 🟢 MODIFICATION: L'utilisateur est fourni par le routeur global
    db: Session = Depends(get_db),
    # 🎯 On dépend du résultat de la dépendance globale role_required/get_current_user
    current_user: Any = Depends(get_current_user) 
) -> ToxicoController:
    
    # 1. Création des Repositories
    toxico_repo = ToxicoRepository(session=db)
    patient_repo = PatientRepository(session=db) 
    audit_repo = AuditRepository(session=db) 
    
    # 2. Construction du PatientController
    patient_ctrl = PatientController(
        repo=patient_repo, 
        current_user=current_user, # Utilisation de l'utilisateur validé
        audit_repo=audit_repo 
    )

    # 3. Construction du ToxicoController
    return ToxicoController(
        repo=toxico_repo,
        patient_controller=patient_ctrl,
        current_user=current_user # Utilisation de l'utilisateur validé
    )

# --- ROUTES ---

@router.get("/psychologists", response_model=List[PsychologistSimple], 
            dependencies=[Depends(role_required("ToxicoManager", "admin","manger"))])
def get_psychologists(
    # 🟢 INJECTION DIRECTE DU CONTRÔLEUR (Utilisation de get_toxico_controller)
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
    # Items est l'objet ORM, total est l'entier.
    items, total = ctrl.list_dossiers(search=search, phase=phase, page=page, per_page=per_page)
    
    # Mapping via helper du Controller
    data = [ctrl.map_dossier_to_list_item(item) for item in items]
    return {"data": data, "total": total, "page": page, "per_page": per_page}

@router.get("/patients/{patient_id}", response_model=Any)
def get_patient_detail(
    patient_id: int,
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    dossier = ctrl.get_dossier_details(patient_id) 
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier Toxico introuvable")

    # --- CORRECTION ICI ---
    # On récupère le nom proprement sans evaluer de f-string risqué
    psy_name = "Non assigné"
    if dossier.psychologist:
        # On priorise full_name car votre contrôleur l'utilise ailleurs
        if hasattr(dossier.psychologist, "full_name"):
            psy_name = dossier.psychologist.full_name
        # Fallback de sécurité (si jamais full_name n'existe pas, on tente username ou autre)
        elif hasattr(dossier.psychologist, "username"):
             psy_name = dossier.psychologist.username
        else:
             psy_name = "Psychologue (Nom inconnu)"

    return {
        "dossier_id": dossier.id,
        "patient_id": dossier.patient_id,
        "code": dossier.patient.code_patient,
        
        # Mapping Identité
        "firstName": dossier.patient.first_name,
        "lastName": dossier.patient.last_name,
        "dob": dossier.patient.birth_date,
        # Attention: dans votre controller vous avez utilisé 'mother_name' pour la création, 
        # vérifiez bien le nom de la colonne dans votre modèle Patient (souvent mother_name ou mothers_name)
        "mothersName": getattr(dossier.patient, "mother_name", getattr(dossier.patient, "mothers_name", None)),

        # Contact
        "address": getattr(dossier.patient, "address", "Non renseignée"),
        "contact": getattr(dossier.patient, "contact_phone", getattr(dossier.patient, "contact", None)),

        # Admission
        "admissionDate": dossier.admission_date,
        "createdAt": dossier.created_at,
        "substance": dossier.substance,
        "currentPhase": dossier.current_phase,
        "relapseCount": dossier.relapse_count,
        "psychologist": psy_name,  # ✅ Variable corrigée
        
        # Tuteur
        "guardianName": dossier.guardian_name,
        "guardianContact": dossier.guardian_contact,
        "consentFile": dossier.consent_file, # Peut nécessiter un lien URL complet selon votre stockage
        "notes": dossier.notes_admission, # Ou dossier.notes selon votre modèle

        # Historique
        "phaseHistory": sorted([
            {
                "phase": h.phase,
                "start_date": h.start_date,
                "end_date": h.end_date,
                "status": h.status,
                "comments": h.comments
            } for h in dossier.phase_history
        ], key=lambda x: x['start_date'], reverse=True),
        
        # Evaluations
        "evaluations": [
            {
                "id": e.id,
                "created_at": e.created_at,
                "decision": e.decision,
                "observation": e.observation,
                "recommendation": e.recommendation,
                "phase_before": e.phase_before,
                "phase_after": e.phase_after,
                "is_relapse": e.is_relapse,
                # Sécurisation ici aussi au cas où
                "evaluator_name": getattr(e.evaluator, "full_name", "Inconnu") if e.evaluator else "Inconnu"
            } for e in dossier.evaluations
        ]
    }

@router.post("/admission", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(role_required("ToxicoManager", "admin", "Assistant"))])
def admission_patient(
    data: ToxicoAdmissionCreate,
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    try:
        dossier = ctrl.admission_patient(data.model_dump())
        return {"message": "Admission réussie", "code_patient": dossier.patient.code_patient}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[ERREUR ADMISSION] {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur interne lors de l'admission.")

@router.post("/evaluation", status_code=status.HTTP_200_OK,
             dependencies=[Depends(role_required("Psychologist", "SpiritualCounsellor", "admin"))])
def submit_evaluation(
    data: ToxicoEvaluationCreate,
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    try:
        payload = data.model_dump()
        if not payload.get('dossier_id'):
            dossier = ctrl.get_dossier_details(payload['patientId'])
            if not dossier:
                raise ValueError("Dossier introuvable pour ce patient")
            payload['dossier_id'] = dossier.id

        ctrl.submit_evaluation(payload) 
        return {"message": "Évaluation enregistrée"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/discharge/{dossier_id}", status_code=status.HTTP_200_OK,
             dependencies=[Depends(role_required("ToxicoManager", "admin"))])
def discharge_patient(
    dossier_id: int,
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    try:
        ctrl.discharge_patient(dossier_id)
        return {"message": "Dossier clôturé avec succès."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
# Route pour les statistiques du tableau de bord
@router.get("/stats/dashboard", response_model=Dict[str, Any], tags=["ToxicoStats"])
def get_dashboard_stats(ctrl: ToxicoController = Depends(get_toxico_controller)):
    """Récupère les statistiques clés du tableau de bord."""
    
    # Note: Vous pourriez ajouter d'autres stats ici à l'avenir (total actif, etc.)
    admissions = ctrl.get_current_month_admissions_count()
    
    return {
        "currentMonthAdmissions": admissions
        # Ajoutez ici d'autres KPIs futurs
    }    