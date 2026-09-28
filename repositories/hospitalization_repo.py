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
            raise ValueError("Ce séjour est déjà clos — impossible d'ajouter une évolution clinique.")

        update = HospitalizationStatusUpdate(
            hospitalization_id=hospitalization_id,
            status=status,
            note=note,
            created_by=created_by_id,
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

        hosp.discharged_at = datetime.utcnow()
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
            .options(joinedload(Hospitalization.patient), joinedload(Hospitalization.status_updates))
            .filter(Hospitalization.discharged_at.is_(None))
            .order_by(Hospitalization.admitted_at.desc())
            .all()
        )

    def get_history_for_patient(self, patient_id: int) -> List[Hospitalization]:
        return (
            self.session.query(Hospitalization)
            .options(joinedload(Hospitalization.status_updates))
            .filter(Hospitalization.patient_id == patient_id)
            .order_by(Hospitalization.admitted_at.desc())
            .all()
        )

    def count_current(self) -> int:
        return (
            self.session.query(Hospitalization)
            .filter(Hospitalization.discharged_at.is_(None))
            .count()
        )
