from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_, and_, func
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import selectinload

from models.toxico import ToxicoDossier, ToxicoPhaseHistory, ToxicoEvaluation, ToxicoStay, DISCHARGE_REASONS
from models.patient import Patient
from models.hospitalization import Hospitalization
from models.user import User
from models.application_role import ApplicationRole


# Rôles proposés par GET /toxico/psychologists ET acceptés comme responsable à l'admission
RESPONSIBLE_ROLES = ('Psychologist', 'ToxicoManager', 'medecin')
# Liste deroulante « psychologue referent » : uniquement le role Psychologue (les autres roles restent acceptes
# par _validate_psychologist pour les dossiers existants, mais ne sont plus proposes).
PSYCHOLOGIST_LIST_ROLES = ('Psychologist',)


class ToxicoValidationError(ValueError):
    """Donnée invalide (mappée en 422)."""


class ToxicoConflictError(ValueError):
    """État incompatible : déjà sorti, déjà actif, doublon (mappée en 409)."""


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

    def search_discharged_dossiers(
        self,
        search_query: str = None,
        reason: str = None,
        discharged_from: date = None,
        discharged_to: date = None,
        page: int = 1,
        per_page: Optional[int] = 20,
        export_cap: Optional[int] = None,
    ) -> Tuple[list, int]:
        """per_page=None : pas de pagination (export PDF) - toutes les lignes,
        l'appelant borne via export_cap.
        Dossiers INACTIFS (patients sortis) avec leur dernier séjour, en une
        seule requête agrégée (pas de N+1). Les filtres motif/dates portent sur
        le dernier séjour. Un dossier sans séjour reste listé (champs à None).
        Retourne (lignes, total) ; chaque ligne est un tuple nommé."""
        from sqlalchemy.orm import aliased

        agg = (
            self.session.query(
                ToxicoStay.dossier_id.label("dossier_id"),
                func.count(ToxicoStay.id).label("stays_count"),
                func.max(ToxicoStay.stay_number).label("last_number"),
            )
            .group_by(ToxicoStay.dossier_id)
            .subquery()
        )
        psy = aliased(User)
        disch = aliased(User)

        query = (
            self.session.query(
                ToxicoDossier.id.label("dossier_id"),
                ToxicoDossier.patient_id.label("patient_id"),
                Patient.first_name, Patient.last_name, Patient.code_patient,
                func.coalesce(agg.c.stays_count, 0).label("stays_count"),
                ToxicoStay.stay_number, ToxicoStay.admission_date, ToxicoStay.discharge_date,
                ToxicoStay.discharge_reason, ToxicoStay.substance,
                psy.full_name.label("psychologist_name"),
                disch.full_name.label("discharged_by_name"),
            )
            .join(Patient, Patient.patient_id == ToxicoDossier.patient_id)
            .outerjoin(agg, agg.c.dossier_id == ToxicoDossier.id)
            .outerjoin(ToxicoStay, and_(ToxicoStay.dossier_id == ToxicoDossier.id,
                                        ToxicoStay.stay_number == agg.c.last_number))
            .outerjoin(psy, psy.user_id == ToxicoStay.psychologist_id)
            .outerjoin(disch, disch.user_id == ToxicoStay.discharged_by)
            .filter(ToxicoDossier.is_active == False)  # noqa: E712
        )

        if search_query and search_query.strip():
            raw = search_query.strip()
            esc = raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            term = f"%{esc}%"
            query = query.filter(or_(
                Patient.last_name.ilike(term, escape="\\"),
                Patient.first_name.ilike(term, escape="\\"),
                Patient.code_patient.ilike(term, escape="\\"),
                (Patient.first_name + " " + Patient.last_name).ilike(term, escape="\\"),
                (Patient.last_name + " " + Patient.first_name).ilike(term, escape="\\"),
            ))
        if reason:
            query = query.filter(ToxicoStay.discharge_reason == reason)
        if discharged_from:
            query = query.filter(ToxicoStay.discharge_date >= discharged_from)
        if discharged_to:
            query = query.filter(ToxicoStay.discharge_date <= discharged_to)

        total = query.order_by(None).count()
        ordered = query.order_by(ToxicoStay.discharge_date.desc().nullslast(), ToxicoDossier.id.desc())
        if per_page is None:
            rows = ordered.limit(export_cap).all() if export_cap else ordered.all()
        else:
            rows = ordered.offset((page - 1) * per_page).limit(per_page).all()
        return rows, total

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
                joinedload(ToxicoDossier.evaluations).joinedload(ToxicoEvaluation.evaluator),
                selectinload(ToxicoDossier.stays).joinedload(ToxicoStay.psychologist),
                selectinload(ToxicoDossier.stays).joinedload(ToxicoStay.discharger),
            )
            .filter(ToxicoDossier.patient_id == patient_id)
            .first()
        )

    def get_psychologists(self) -> List[User]:
        """ Récupère les psys actifs via leurs rôles """
        # Adapte les noms exacts de tes rôles en BDD ici
        target_roles = list(PSYCHOLOGIST_LIST_ROLES)

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
        Admission OU réadmission (une seule transaction) :
        - aucun dossier -> création du dossier + séjour 1 + phase 1 (liés au séjour) ;
        - dossier inactif -> réactivation, séjour n+1, nouvelle phase 1 ;
        - dossier actif -> ToxicoConflictError (409), rien n'est écrit.
        Utilisée APRÈS que le patient ait été créé et commité (via PS Patient).
        """
        try:
            self._validate_psychologist(toxico_data.get('psychologist_id'))

            # Verrou de ligne : deux réadmissions simultanées se sérialisent ici.
            existing = (
                self.session.query(ToxicoDossier)
                .filter(ToxicoDossier.patient_id == patient_id)
                .with_for_update()
                .first()
            )
            if existing is not None:
                if existing.is_active:
                    raise ToxicoConflictError("Ce patient a déjà un dossier Toxicologie actif.")
                dossier = self._readmit(existing, toxico_data)
                self.session.commit()
                return dossier

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

            stay = ToxicoStay(
                dossier_id=dossier.id,
                stay_number=1,
                admission_date=toxico_data['admission_date'],
                psychologist_id=toxico_data['psychologist_id'],
                substance=toxico_data['substance'],
            )
            self.session.add(stay)
            self.session.flush()

            # 2. Historique Initial
            history = ToxicoPhaseHistory(
                dossier_id=dossier.id,
                phase=1,
                start_date=toxico_data['admission_date'],
                status="En cours",
                comments="Admission initiale",
                stay_id=stay.id,
            )
            self.session.add(history)

            self.session.commit()
            return dossier

        except IntegrityError as e:
            self.session.rollback()
            msg = str(getattr(e, "orig", e))
            if any(k in msg for k in ("uq_toxico_stays_one_open", "uq_toxico_stays_dossier_number",
                                      "uq_toxico_patient", "toxico_dossiers_patient_id_key")):
                raise ToxicoConflictError(
                    "Une admission est déjà en cours pour ce patient (doublon refusé).") from e
            raise
        except Exception as e:
            self.session.rollback()
            raise e

    def _validate_psychologist(self, psychologist_id):
        if not psychologist_id:
            raise ToxicoValidationError("Le psychologue est obligatoire à chaque admission.")
        user = (
            self.session.query(User)
            .join(ApplicationRole, User.role_id == ApplicationRole.role_id)
            .filter(User.user_id == psychologist_id)
            .filter(User.is_active == True)
            .filter(ApplicationRole.role_name.in_(RESPONSIBLE_ROLES))
            .first()
        )
        if user is None:
            raise ToxicoValidationError(
                "Le responsable choisi est introuvable, inactif ou n'a pas un rôle autorisé.")

    def get_open_hospitalization(self, dossier_id: int) -> Optional[Hospitalization]:
        """Sejour hospitalier ouvert du patient du dossier (indicateur minimal pour
        le ToxicoManager, qui ne peut pas lire /hospitalizations). Leve ValueError
        si le dossier n'existe pas."""
        dossier = self.session.get(ToxicoDossier, dossier_id)
        if dossier is None:
            raise ValueError("Dossier introuvable")
        return (
            self.session.query(Hospitalization)
            .filter(Hospitalization.patient_id == dossier.patient_id, Hospitalization.discharged_at.is_(None))
            .first()
        )

    def get_open_stay(self, dossier_id: int) -> Optional[ToxicoStay]:
        return (
            self.session.query(ToxicoStay)
            .filter(ToxicoStay.dossier_id == dossier_id, ToxicoStay.discharge_date == None)
            .first()
        )

    def _readmit(self, dossier: ToxicoDossier, toxico_data: dict) -> ToxicoDossier:
        """Réactive un dossier inactif (appelant : verrou + commit/rollback)."""
        last = (
            self.session.query(ToxicoStay)
            .filter(ToxicoStay.dossier_id == dossier.id)
            .order_by(desc(ToxicoStay.stay_number))
            .first()
        )
        new_number = (last.stay_number if last else 0) + 1

        adm = toxico_data['admission_date']
        if isinstance(adm, str):
            adm = date.fromisoformat(adm)
        if isinstance(adm, datetime):
            adm = adm.date()
        if adm > date.today() + timedelta(days=1):
            raise ToxicoValidationError("La date de réadmission ne peut pas être dans le futur.")
        if last is not None and last.discharge_date is not None and adm < last.discharge_date:
            raise ToxicoValidationError(
                "La date de réadmission est antérieure à la sortie du séjour précédent "
                f"({last.discharge_date.isoformat()}).")

        dossier.is_active = True
        dossier.admission_date = toxico_data['admission_date']
        dossier.substance = toxico_data['substance']
        dossier.psychologist_id = toxico_data['psychologist_id']
        dossier.current_phase = 1
        # relapse_count volontairement inchangé (régressions décidées en évaluation)
        if toxico_data.get('guardian_name'):
            dossier.guardian_name = toxico_data['guardian_name']
        if toxico_data.get('guardian_contact'):
            dossier.guardian_contact = toxico_data['guardian_contact']
        if toxico_data.get('notes'):
            dossier.notes_admission = toxico_data['notes']
        if toxico_data.get('consent_file'):
            dossier.consent_file = toxico_data['consent_file']  # sinon on garde l'ancien

        stay = ToxicoStay(
            dossier_id=dossier.id,
            stay_number=new_number,
            admission_date=toxico_data['admission_date'],
            psychologist_id=toxico_data['psychologist_id'],
            substance=toxico_data['substance'],
        )
        self.session.add(stay)
        self.session.flush()  # l'index du séjour ouvert lève ici en cas de doublon

        self.session.add(ToxicoPhaseHistory(
            dossier_id=dossier.id,
            phase=1,
            start_date=toxico_data['admission_date'],
            status="En cours",
            comments=f"Réadmission, séjour {new_number}",
            stay_id=stay.id,
        ))
        return dossier

    def process_evaluation(self, dossier_id: int, data: dict, user_id: int) -> ToxicoEvaluation:
        """
        Gère l'évaluation et la machine à états des phases.
        """
        try:
            dossier = self.session.get(ToxicoDossier, dossier_id)
            if not dossier: raise ValueError("Dossier introuvable")
            if not dossier.is_active:
                raise ToxicoConflictError(
                    "Ce dossier est sorti du programme : le patient doit être réadmis avant toute évaluation.")

            target_phase = data['target_phase']
            decision = data['decision'] # PROGRESS, REGRESS, MAINTAIN
            open_stay = self.get_open_stay(dossier.id)
            stay_id = open_stay.id if open_stay else None

            # 1. Créer l'évaluation
            eval_entry = ToxicoEvaluation(
                dossier_id=dossier.id,
                stay_id=stay_id,
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
                    comments=f"Changement suite évaluation ({decision})",
                    stay_id=stay_id,
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

    def _close_current_phase(self, dossier_id: int, reason: str, end_date: Optional[date] = None):
        """Helper interne pour fermer proprement une phase"""
        current = (
            self.session.query(ToxicoPhaseHistory)
            .filter(ToxicoPhaseHistory.dossier_id == dossier_id)
            .filter(ToxicoPhaseHistory.end_date == None)
            .first()
        )
        if current:
            current.end_date = end_date or date.today()
            current.status = "Terminé" if reason == 'PROGRESS' else "Interrompu"

    def discharge(self, dossier_id: int, reason: str, note: Optional[str], user_id: Optional[int],
                  discharge_date: Optional[date] = None):
        """Sortie du programme : ferme la phase courante et le séjour ouvert,
        dossier inactif — une seule transaction. discharge_date : jour de sortie (defaut : aujourd'hui) ;
        jamais dans le futur, jamais avant l'admission du sejour."""
        if reason not in DISCHARGE_REASONS:
            raise ToxicoValidationError(
                f"Motif de sortie invalide (attendu : {', '.join(DISCHARGE_REASONS)}).")
        note = (note or "").strip() or None
        if reason == 'autre' and not note:
            raise ToxicoValidationError("Une note est obligatoire pour le motif « autre ».")
        try:
            dossier = (
                self.session.query(ToxicoDossier)
                .filter(ToxicoDossier.id == dossier_id)
                .with_for_update()
                .first()
            )
            if not dossier:
                raise ValueError("Dossier introuvable")
            if not dossier.is_active:
                raise ToxicoConflictError("Ce dossier est déjà sorti du programme.")

            today = date.today()
            stay = self.get_open_stay(dossier.id)
            if stay is None:
                raise ToxicoConflictError("Aucun séjour ouvert pour ce dossier : sortie impossible.")
            out_date = discharge_date or today
            if out_date > today:
                raise ToxicoValidationError("La date de sortie ne peut pas être dans le futur.")
            if stay.admission_date > out_date:
                raise ToxicoValidationError("Sortie impossible avant la date d'admission du séjour.")

            self._close_current_phase(dossier.id, "DISCHARGE", out_date)
            stay.discharge_date = out_date
            stay.discharge_reason = reason
            stay.discharge_note = note
            stay.discharged_by = user_id
            dossier.is_active = False
            self.session.commit()
            return dossier
        except Exception as e:
            self.session.rollback()
            raise e

    def active_stats(self) -> dict:
        """Chiffres GLOBAUX des dossiers actifs (jamais limites a la page ni a la recherche de la liste)."""
        active = ToxicoDossier.is_active == True  # noqa: E712
        total = self.session.query(func.count(ToxicoDossier.id)).filter(active).scalar() or 0
        by_phase = {1: 0, 2: 0, 3: 0, 4: 0}
        for phase, n in (self.session.query(ToxicoDossier.current_phase, func.count(ToxicoDossier.id))
                         .filter(active).group_by(ToxicoDossier.current_phase).all()):
            if phase in by_phase:
                by_phase[phase] = n
        relapse_patients = (self.session.query(func.count(ToxicoDossier.id))
                            .filter(active, ToxicoDossier.relapse_count > 0).scalar() or 0)
        by_substance = {s or "Autre": n for s, n in (
            self.session.query(ToxicoDossier.substance, func.count(ToxicoDossier.id))
            .filter(active).group_by(ToxicoDossier.substance).all())}
        by_psy = {(name or "Non assigné"): n for name, n in (
            self.session.query(User.full_name, func.count(ToxicoDossier.id))
            .select_from(ToxicoDossier).outerjoin(User, User.user_id == ToxicoDossier.psychologist_id)
            .filter(active).group_by(User.full_name).all())}
        week_ago = date.today() - timedelta(days=7)
        new_week = (self.session.query(func.count(ToxicoDossier.id))
                    .filter(active, ToxicoDossier.admission_date >= week_ago).scalar() or 0)
        return {"total_active": total, "by_phase": by_phase, "relapse_patients": relapse_patients,
                "by_substance": by_substance, "by_psychologist": by_psy, "new_this_week": new_week}

    def count_dossiers_created_since(self, start_date, end_date=None):
        """Compte les séjours commencés (admissions + réadmissions, par
        admission_date) dans [start_date, end_date) ; sans end_date : jusqu'à
        aujourd'hui inclus (un séjour daté dans le futur n'est pas compté)."""
        def _d(v):
            return v.date() if isinstance(v, datetime) else v
        start = _d(start_date)
        q = self.session.query(ToxicoStay).filter(ToxicoStay.admission_date >= start)
        if end_date is not None:
            q = q.filter(ToxicoStay.admission_date < _d(end_date))
        else:
            q = q.filter(ToxicoStay.admission_date <= date.today())
        return q.count()