from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from models.hospitalization import (
    Hospitalization,
    HospitalizationStatusUpdate,
    DISCHARGE_DISPOSITIONS,
    CLINICAL_STATUSES,
)
from models.patient import Patient
from utils.business_time import business_now
from controller.config_controller import ConfigController
from repositories.config_repo import ConfigRepository
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
from api_backend.backend_app.utils.pdf_generator import render_pdf_from_template

STATUS_LABELS_FR = {
    "AMELIORATION": "Amélioration",
    "STABLE": "Stable",
    "AGGRAVATION": "Aggravation",
}
DISPOSITION_LABELS_FR = {
    "GUERI": "Guéri",
    "TRANSFERE": "Transféré",
    "SORTIE_CONTRE_AVIS_MEDICAL": "Sortie contre avis médical",
    "DECES": "Décès",
}

# Convention de fuseau (2026-10-26, defaut releve par les guides) : TOUTES les
# dates d'un sejour (admitted_at, discharged_at, created_at des evolutions)
# sont l'heure locale de Douala, naive - comme Caisse.paid_at. Avant, la
# sortie etait ecrite en UTC (datetime.utcnow) et l'admission en heure locale
# (server_default now()), d'ou des sorties "avant l'admission".


def stay_duration_label(start: datetime, end: datetime) -> str:
    """Duree lisible : minutes, heures, puis jours (jamais '0 jour(s)')."""
    minutes = max(0, int((end - start).total_seconds() // 60))
    if minutes < 60:
        return f"{minutes} min"
    if minutes < 24 * 60:
        return f"{minutes // 60} h {minutes % 60} min"
    return f"{minutes // (24 * 60)} jour(s) {(minutes % (24 * 60)) // 60} h"


class HospitalizationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_open_for_patient(self, patient_id: int) -> Optional[Hospitalization]:
        return (
            self.session.query(Hospitalization)
            .filter(Hospitalization.patient_id == patient_id, Hospitalization.discharged_at.is_(None))
            .one_or_none()
        )

    def admit(self, patient_id: int, admitted_by_id: int, admission_reason: Optional[str]) -> Hospitalization:
        patient = self.session.get(Patient, patient_id)
        if patient is None:
            raise ValueError(f"Patient introuvable (ID={patient_id}).")
        # Pas de restriction par parcours (decision utilisateur 2026-09-28) :
        # le centre offre des soins holistiques, un patient peut suivre 1, 2
        # ou les 3 parcours (clinique/toxico/spirituel), et un patient
        # toxico ou spirituel peut avoir besoin d'une hospitalisation - c'est
        # l'admission elle-meme qui l'inscrit dans le suivi clinique. Le
        # controle d'acces reste le role (medecin/nurse, cote endpoint).

        if self.get_open_for_patient(patient_id) is not None:
            raise ValueError("Ce patient est déjà hospitalisé (séjour en cours).")

        hosp = Hospitalization(
            patient_id=patient_id,
            admitted_by=admitted_by_id,
            admitted_at=business_now(),
            admission_reason=admission_reason,
        )
        self.session.add(hosp)
        self.session.commit()
        self.session.refresh(hosp)
        return hosp

    def _get_or_raise(self, hospitalization_id: int) -> Hospitalization:
        hosp = self.session.get(Hospitalization, hospitalization_id)
        if hosp is None:
            raise ValueError(f"Aucune hospitalisation trouvée pour l'ID={hospitalization_id}")
        return hosp

    def add_status_update(
        self, hospitalization_id: int, status: str, note: Optional[str], created_by_id: int
    ) -> HospitalizationStatusUpdate:
        if status not in CLINICAL_STATUSES:
            raise ValueError(f"Statut clinique invalide : {status}")

        hosp = self._get_or_raise(hospitalization_id)
        if hosp.discharged_at is not None:
            raise ValueError("Ce séjour est déjà clos, impossible d'ajouter une évolution clinique.")

        update = HospitalizationStatusUpdate(
            hospitalization_id=hospitalization_id,
            status=status,
            note=note,
            created_by=created_by_id,
            created_at=business_now(),
        )
        self.session.add(update)
        self.session.commit()
        self.session.refresh(update)
        return update

    def discharge(
        self,
        hospitalization_id: int,
        discharge_disposition: str,
        discharge_note: Optional[str],
        discharged_by_id: int,
    ) -> Hospitalization:
        if discharge_disposition not in DISCHARGE_DISPOSITIONS:
            raise ValueError(f"Type de sortie invalide : {discharge_disposition}")

        hosp = self._get_or_raise(hospitalization_id)
        if hosp.discharged_at is not None:
            raise ValueError("Ce séjour est déjà clos.")

        hosp.discharged_at = business_now()
        hosp.discharge_disposition = discharge_disposition
        hosp.discharge_note = discharge_note
        hosp.discharged_by = discharged_by_id
        self.session.add(hosp)
        self.session.commit()
        self.session.refresh(hosp)
        return hosp

    def list_current(self) -> List[Hospitalization]:
        return (
            self.session.query(Hospitalization)
            .options(
                joinedload(Hospitalization.patient),
                joinedload(Hospitalization.admitted_by_user),
                joinedload(Hospitalization.discharged_by_user),
                joinedload(Hospitalization.status_updates).joinedload(HospitalizationStatusUpdate.created_by_user),
            )
            .filter(Hospitalization.discharged_at.is_(None))
            .order_by(Hospitalization.admitted_at.desc())
            .all()
        )

    def get_history_for_patient(self, patient_id: int) -> List[Hospitalization]:
        return (
            self.session.query(Hospitalization)
            .options(
                joinedload(Hospitalization.admitted_by_user),
                joinedload(Hospitalization.discharged_by_user),
                joinedload(Hospitalization.status_updates).joinedload(HospitalizationStatusUpdate.created_by_user),
            )
            .filter(Hospitalization.patient_id == patient_id)
            .order_by(Hospitalization.admitted_at.desc())
            .all()
        )

    def generate_discharge_letter_pdf(self, hospitalization_id: int) -> bytes:
        """Lettre de sortie (retour terrain 2026-09-28) - uniquement pour un
        sejour deja clos, jamais en cours (voir controller/endpoint : la
        decision de sortie doit exister). Reutilise integralement
        l'infrastructure PDF existante (chantier exports 2026-09-23) - meme
        en-tete dynamique que la facture caisse, aucun nouveau moteur."""
        hosp = (
            self.session.query(Hospitalization)
            .options(
                joinedload(Hospitalization.patient),
                joinedload(Hospitalization.admitted_by_user),
                joinedload(Hospitalization.discharged_by_user),
                joinedload(Hospitalization.status_updates).joinedload(HospitalizationStatusUpdate.created_by_user),
            )
            .filter(Hospitalization.id == hospitalization_id)
            .one_or_none()
        )
        if hosp is None:
            raise ValueError(f"Aucune hospitalisation trouvée pour l'ID={hospitalization_id}")
        if hosp.discharged_at is None:
            raise ValueError("Ce séjour n'est pas encore clos, lettre de sortie indisponible.")

        def _user_name(user):
            if not user:
                return "Inconnu"
            return getattr(user, "full_name", None) or getattr(user, "username", None) or "Inconnu"

        config_ctrl = ConfigController(repo=ConfigRepository(self.session))
        header_ctx = get_pdf_header_context(config_ctrl)

        patient_name = "Inconnu"
        if hosp.patient:
            patient_name = f"{hosp.patient.first_name or ''} {hosp.patient.last_name or ''}".strip() or "Inconnu"

        status_updates = [
            {
                "created_at": u.created_at.strftime("%d/%m/%Y à %H:%M"),
                "status": u.status,
                "status_label": STATUS_LABELS_FR.get(u.status, u.status),
                "created_by_name": _user_name(u.created_by_user),
                "note": u.note,
            }
            for u in (hosp.status_updates or [])
        ]

        context = {
            **header_ctx,
            "date_impression": business_now().strftime("%d/%m/%Y à %H:%M"),
            "stay": {
                "patient_name": patient_name,
                "admitted_at": hosp.admitted_at.strftime("%d/%m/%Y à %H:%M"),
                "admitted_by_name": _user_name(hosp.admitted_by_user),
                "admission_reason": hosp.admission_reason,
                "discharged_at": hosp.discharged_at.strftime("%d/%m/%Y à %H:%M"),
                "duration_label": stay_duration_label(hosp.admitted_at, hosp.discharged_at),
                "disposition_label": DISPOSITION_LABELS_FR.get(hosp.discharge_disposition, hosp.discharge_disposition),
                "discharged_by_name": _user_name(hosp.discharged_by_user),
                "discharge_note": hosp.discharge_note,
                "status_updates": status_updates,
            },
        }

        return render_pdf_from_template("hospitalization_discharge_letter_template.html", context)

    def get_stays_for_export(self, patient_id: int) -> List[dict]:
        """Sejours du patient mis en forme (francais, heure locale) pour
        l'export du dossier PDF/Excel : motif d'admission, sortie, note de
        sortie (defaut releve par les guides 2026-10-26)."""
        def _fmt(dt):
            return dt.strftime("%d/%m/%Y %H:%M") if dt else ""

        def _name(user):
            return (getattr(user, "full_name", None) or getattr(user, "username", None) or "") if user else ""

        stays = []
        for h in self.get_history_for_patient(patient_id):
            stays.append({
                "admitted_at": _fmt(h.admitted_at),
                "discharged_at": _fmt(h.discharged_at) or "En cours",
                "duration_label": stay_duration_label(h.admitted_at, h.discharged_at or business_now()),
                "admission_reason": h.admission_reason or "",
                "disposition_label": DISPOSITION_LABELS_FR.get(h.discharge_disposition, h.discharge_disposition or ""),
                "discharge_note": h.discharge_note or "",
                "admitted_by_name": _name(h.admitted_by_user),
                "discharged_by_name": _name(h.discharged_by_user),
            })
        return stays

    def count_current(self) -> int:
        return (
            self.session.query(Hospitalization)
            .filter(Hospitalization.discharged_at.is_(None))
            .count()
        )
