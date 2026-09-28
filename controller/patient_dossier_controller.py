# controller/patient_dossier_controller.py
import logging
from typing import Any, Dict

from fastapi.encoders import jsonable_encoder

from api_backend.backend_app.routes.medical_records.schemas import MedicalRecordResponse
from api_backend.backend_app.routes.prescription.prescriptions_schemas import PrescriptionResponse
from api_backend.backend_app.routes.cs.schemas_cs import ConsultationResponse

logger = logging.getLogger(__name__)


class PatientDossierController:
    """Compose les controleurs de domaine existants en une vue unifiee du
    dossier patient (chantier 6, registre L5). Ne duplique aucune logique
    metier des controleurs existants, les appelle directement - motif deja
    utilise dans ce projet (PrescriptionController prend deja
    patient_controller en dependance)."""

    def __init__(self, patient_ctrl, medical_ctrl, prescription_ctrl, lab_ctrl,
                 cs_ctrl, toxico_ctrl, audit_repo, current_user):
        self.patient_ctrl = patient_ctrl
        self.medical_ctrl = medical_ctrl
        self.prescription_ctrl = prescription_ctrl
        self.lab_ctrl = lab_ctrl
        self.cs_ctrl = cs_ctrl
        self.toxico_ctrl = toxico_ctrl
        self.audit_repo = audit_repo
        self.current_user = current_user
        self.session = patient_ctrl.session

    def get_full_dossier(self, patient_id: int) -> Dict[str, Any]:
        patient = self.patient_ctrl.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} introuvable")

        flags = self.patient_ctrl.repo.compute_domain_flags(patient_id)

        resultats: Dict[str, Any] = {}
        echecs = []
        for cle, appel in [
            ("resume_clinique", lambda: self.medical_ctrl.get_patient_dme_summary(patient_id)),
            # jsonable_encoder() avant model_validate() : get_patient_history()
            # charge la relation .patient en eager (joinedload, voir
            # repositories/medical_repo.py:get_full_history), mais
            # MedicalRecordResponse.patient est type Optional[dict] - passer
            # l'objet ORM brut a model_validate() leve une ValidationError
            # ("Input should be a valid dictionary"), from_attributes=True
            # ne coerce pas recursivement un objet ORM imbrique vers un champ
            # dict simple. Meme defaut deja rencontre et corrige pour ce
            # meme couple modele/schema dans
            # routes/medical_records/mapping.py (normalize_medical_record_data)
            # et pour Prescription dans prescriptions_endpoints.py
            # (_validate_and_normalize_single, meme jsonable_encoder).
            ("historique_medical", lambda: [
                MedicalRecordResponse.model_validate(jsonable_encoder(r)).model_dump(mode="json")
                for r in self.medical_ctrl.get_patient_history(patient_id)
            ]),
            ("prescriptions", lambda: [
                PrescriptionResponse.model_validate(jsonable_encoder(p)).model_dump(mode="json")
                for p in self.prescription_ctrl.get_patient_prescriptions(patient_id)
            ]),
            ("historique_labo", lambda: self.lab_ctrl.get_patient_lab_history(patient_id)),
            ("historique_spirituel", lambda: [
                ConsultationResponse.model_validate(c).model_dump(mode="json")
                for c in self.cs_ctrl.list_for_patient(patient_id)
            ]),
            ("dossier_toxico", lambda: self.toxico_ctrl.serialize_dossier_details(
                self.toxico_ctrl.get_dossier_details(patient_id)
            )),
        ]:
            try:
                resultats[cle] = appel()
            except Exception:
                echecs.append(cle)
                resultats[cle] = None
                logger.exception(f"Echec chargement '{cle}' pour le dossier patient {patient_id}")
                # Une vraie erreur SQLAlchemy (ProgrammingError, DataError...)
                # laisse la session dans un etat "transaction avortee" - sans
                # rollback, le log_user_action + commit qui suivent la boucle
                # levent PendingRollbackError et transforment un succes
                # partiel en 500 (perte de la ligne d'audit). Lecture seule
                # ici, rien a preserver.
                self.session.rollback()

        # 'details' n'est pas une colonne de audit_user_actions (seul
        # UserAccessLog en a une) - log_user_action l'ignore en silence.
        # new_values (JSONB reel) porte l'information a la place.
        self.audit_repo.log_user_action(
            current_user=self.current_user,
            resource_type="Patient",
            resource_id=patient_id,
            action_performed="VIEW_DOSSIER_COMPLET",
            new_values={"domaines_en_echec": echecs} if echecs else None,
        )
        self.session.commit()

        # Le dict "patient" vient de patient_repo.get_by_id et porte encore
        # les colonnes is_clinical/is_toxicology/is_spiritual stockees,
        # potentiellement obsoletes face aux "flags" calcules juste
        # au-dessus. Ne pas les renvoyer cote-a-cote : seul "flags" doit
        # porter l'information de domaine dans la reponse.
        patient_sans_drapeaux_obsoletes = {
            k: v for k, v in patient.items()
            if k not in ("is_clinical", "is_toxicology", "is_spiritual")
        }

        # Revirement de politique (2026-09-22, decision utilisateur) :
        # medecin/nurse ne voient que le clinique dans le dossier
        # consolide - jamais toxico/spirituel, meme si le patient a ces
        # deux domaines. Cle absente de la reponse, pas juste a None :
        # un frontend qui checkait "if (dossier_toxico)" laisserait
        # passer une valeur null par erreur de logique, une cle absente
        # ne peut pas se confondre avec "pas encore de donnees". flags
        # reste toujours renvoye, a tous les roles - savoir qu'un
        # domaine existe reste cliniquement utile sans en exposer le
        # detail. La tracabilite (log_user_action ci-dessus) ne change
        # pas : un acces filtre reste un acces trace.
        roles = set(getattr(self.current_user, "roles", []) or [])
        est_medical_seul = bool(roles & {"medecin", "nurse"})

        reponse = {
            "patient": patient_sans_drapeaux_obsoletes,
            "flags": flags,
            **resultats,
            "domaines_indisponibles": echecs,
        }
        if est_medical_seul:
            reponse.pop("dossier_toxico", None)
            reponse.pop("historique_spirituel", None)
        return reponse
