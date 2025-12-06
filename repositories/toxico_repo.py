from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_, and_, func
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime
from typing import List, Optional, Tuple

from models.toxico import ToxicoDossier, ToxicoPhaseHistory, ToxicoEvaluation
from models.patient import Patient
from models.user import User
from models.application_role import ApplicationRole

class ToxicoRepository:
    def __init__(self, session: Session):
        self.session = session

    # =========================================================================
    # 1. LECTURE & RECHERCHE AVANCÉE
    # =========================================================================

    def search_dossiers(
        self, 
        search_query: str = None, 
        phase: int = None, 
        page: int = 1, 
        per_page: int = 20
    ) -> Tuple[List[ToxicoDossier], int]:
        """
        Recherche robuste avec filtres et pagination.
        Retourne (items, total_count).
        """
        query = (
            self.session.query(ToxicoDossier)
            .join(ToxicoDossier.patient) # Jointure pour chercher par nom
            .options(
                joinedload(ToxicoDossier.patient),
                joinedload(ToxicoDossier.psychologist)
            )
            .filter(ToxicoDossier.is_active == True)
        )

        # Filtre Texte (Code, Nom, Prénom, Substance)
        if search_query:
            term = f"%{search_query}%"
            query = query.filter(
                or_(
                    Patient.last_name.ilike(term),
                    Patient.first_name.ilike(term),
                    Patient.code_patient.ilike(term),
                    ToxicoDossier.substance.ilike(term)
                )
            )

        # Filtre par Phase
        if phase:
            query = query.filter(ToxicoDossier.current_phase == phase)

        # Total avant pagination
        total = query.count()

        # Pagination & Tri
        items = (
            query
            .order_by(desc(ToxicoDossier.created_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return items, total

    def get_dossier_full(self, patient_id: int) -> Optional[ToxicoDossier]:
        """
        Charge tout le dossier avec l'historique complet pour la vue détaillée.
        """
        return (
            self.session.query(ToxicoDossier)
            .options(
                joinedload(ToxicoDossier.patient),
                # ✅ CORRECTION : Supprimer order_by sur le joinedload
                joinedload(ToxicoDossier.phase_history), 
                joinedload(ToxicoDossier.evaluations).joinedload(ToxicoEvaluation.evaluator)
            )
            .filter(ToxicoDossier.patient_id == patient_id)
            .first()
        )

    def get_psychologists(self) -> List[User]:
        """ Récupère les psys actifs via leurs rôles """
        # Adapte les noms exacts de tes rôles en BDD ici
        target_roles = ['Psychologist', 'ToxicoManager', 'medecin']
        
        return (
            self.session.query(User)
            .join(ApplicationRole)
            .filter(ApplicationRole.role_name.in_(target_roles))
            .filter(User.is_active == True)
            .order_by(User.full_name)
            .all()
        )

    # =========================================================================
    # 2. ÉCRITURE (CREATE / UPDATE)
    # =========================================================================

    def create_dossier_after_patient_commit(self, patient_id: int, toxico_data: dict) -> ToxicoDossier:
        """
        Crée le Dossier Toxico et l'Historique de Phase.
        Utilisée APRÈS que le patient ait été créé et commité (via PS Patient).
        """
        try:
            # Vérification Doublon Dossier (inchangée)
            existing = self.session.query(ToxicoDossier).filter_by(patient_id=patient_id, is_active=True).first()
            if existing: 
                raise ValueError(f"Ce patient a déjà un dossier Toxicologie actif.")

            # 1. Création Dossier
            dossier = ToxicoDossier(
                patient_id=patient_id,
                admission_date=toxico_data['admission_date'],
                substance=toxico_data['substance'],
                psychologist_id=toxico_data['psychologist_id'],
                current_phase=1,
                is_active=True,
                guardian_name=toxico_data.get('guardian_name'),
                guardian_contact=toxico_data.get('guardian_contact'),
                notes_admission=toxico_data.get('notes'),
                # 🟢 AJOUT : Gestion du fichier
                consent_file=toxico_data.get('consent_file')
            )
            self.session.add(dossier)
            self.session.flush() # Génère l'ID

            # 2. Historique Initial (inchangé)
            history = ToxicoPhaseHistory(
                dossier_id=dossier.id,
                phase=1,
                start_date=toxico_data['admission_date'],
                status="En cours",
                comments="Admission initiale"
            )
            self.session.add(history)

            self.session.commit()
            return dossier

        except Exception as e:
            self.session.rollback()
            raise e

    def process_evaluation(self, dossier_id: int, data: dict, user_id: int) -> ToxicoEvaluation:
        """
        Gère l'évaluation et la machine à états des phases.
        """
        try:
            dossier = self.session.get(ToxicoDossier, dossier_id)
            if not dossier: raise ValueError("Dossier introuvable")

            target_phase = data['target_phase']
            decision = data['decision'] # PROGRESS, REGRESS, MAINTAIN

            # 1. Créer l'évaluation
            eval_entry = ToxicoEvaluation(
                dossier_id=dossier.id,
                created_by=user_id,
                decision=decision,
                observation=data['observation'],
                recommendation=data.get('recommendation'),
                phase_before=dossier.current_phase,
                phase_after=target_phase,
                is_relapse=(decision == 'REGRESS')
            )
            self.session.add(eval_entry)

            # 2. Si changement de phase, on ferme l'ancienne et ouvre la nouvelle
            if dossier.current_phase != target_phase:
                # Fermeture de la phase en cours
                self._close_current_phase(dossier.id, decision)
                
                # Ouverture nouvelle phase
                new_hist = ToxicoPhaseHistory(
                    dossier_id=dossier.id,
                    phase=target_phase,
                    start_date=date.today(),
                    status="En cours",
                    comments=f"Changement suite évaluation ({decision})"
                )
                self.session.add(new_hist)
                
                # Mise à jour Dossier
                dossier.current_phase = target_phase
                if decision == 'REGRESS':
                    dossier.relapse_count += 1

            self.session.commit()
            return eval_entry

        except Exception as e:
            self.session.rollback()
            raise e

    def _close_current_phase(self, dossier_id: int, reason: str):
        """Helper interne pour fermer proprement une phase"""
        current = (
            self.session.query(ToxicoPhaseHistory)
            .filter(ToxicoPhaseHistory.dossier_id == dossier_id)
            .filter(ToxicoPhaseHistory.end_date == None)
            .first()
        )
        if current:
            current.end_date = date.today()
            current.status = "Terminé" if reason == 'PROGRESS' else "Interrompu"

    def discharge(self, dossier_id: int):
        """Sortie du programme (Clôture)"""
        try:
            dossier = self.session.get(ToxicoDossier, dossier_id)
            if not dossier: raise ValueError("Dossier introuvable")
            
            # Fermer phase active
            self._close_current_phase(dossier.id, "DISCHARGE")
            
            dossier.is_active = False
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e
        

    def count_dossiers_created_since(self, start_date):
        """Compte les dossiers de patients créés (ou admis) depuis une certaine date."""
        count = self.session.query(ToxicoDossier).filter(
            # On filtre sur la date de création du dossier.
            # SQLite supporte la comparaison directe des datetime.
            ToxicoDossier.created_at >= start_date 
        ).count()
        
        return count    