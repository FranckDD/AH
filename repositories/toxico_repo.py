from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_, and_, func, true, exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.elements import ColumnElement
from datetime import date, datetime, timedelta
from typing import List, Literal, NamedTuple, Optional, Tuple

from sqlalchemy.orm import selectinload

from models.toxico import (ToxicoDossier, ToxicoPhaseHistory, ToxicoEvaluation, ToxicoStay,
                           ToxicoPsychologistTransfer, DISCHARGE_REASONS)
from models.patient import Patient
from models.hospitalization import Hospitalization
from models.user import User
from models.application_role import ApplicationRole
from utils.business_time import business_now

TRANSFER_REASON_MAX = 1000
READMISSION_TRANSFER_REASON = "Readmission"


# Rôles proposés par GET /toxico/psychologists ET acceptés comme responsable à l'admission
RESPONSIBLE_ROLES = ('Psychologist', 'ToxicoManager', 'medecin')
# Liste deroulante « psychologue referent » : uniquement le role Psychologue (les autres roles restent acceptes
# par _validate_psychologist pour les dossiers existants, mais ne sont plus proposes).
PSYCHOLOGIST_LIST_ROLES = ('Psychologist',)


class _CodedError(ValueError):
    """ValueError portant un code machine optionnel (detail = {code, message})."""

    def __init__(self, message, code: Optional[str] = None):
        super().__init__(message)
        self.code = code


class ToxicoValidationError(_CodedError):
    """Donnée invalide (mappée en 422)."""


class ToxicoConflictError(_CodedError):
    """État incompatible : déjà sorti, déjà actif, doublon (mappée en 409)."""


class ToxicoForbiddenError(_CodedError):
    """Action refusee a cet utilisateur (mappee en 403)."""


class ToxicoNotFoundError(_CodedError):
    """Dossier introuvable ou hors perimetre (mappee en 404, jamais d'indice d'existence)."""


class ToxicoScope(NamedTuple):
    """Perimetre de lecture toxico. own_psychologist_id renseigne = psychologue
    limite a ses seuls dossiers (referent actuel)."""
    own_psychologist_id: Optional[int] = None

    @property
    def is_limited(self) -> bool:
        return self.own_psychologist_id is not None


UNRESTRICTED_SCOPE = ToxicoScope()


def _user_field(user, name, default=None):
    if isinstance(user, dict):
        return user.get(name, default)
    return getattr(user, name, default)


def scope_for_user(user) -> ToxicoScope:
    """Limite SSI role canonique `psychologist` ET sees_own_toxico_only vrai
    (le drapeau est ignore pour tout autre role)."""
    from api_backend.backend_app.security.role_map import normalize_role_name, PSYCHOLOGIST
    if user is None or not _user_field(user, "sees_own_toxico_only", False):
        return UNRESTRICTED_SCOPE
    names = list(_user_field(user, "roles", None) or [])
    for attr in ("role", "role_name"):
        v = _user_field(user, attr)
        if isinstance(v, str):
            names.append(v)
    app_role = None if isinstance(user, dict) else getattr(user, "application_role", None)
    if app_role is not None and getattr(app_role, "role_name", None):
        names.append(app_role.role_name)
    canon = {normalize_role_name(str(n)) for n in names if n}
    user_id = _user_field(user, "user_id")
    if PSYCHOLOGIST in canon and user_id is not None:
        return ToxicoScope(int(user_id))
    return UNRESTRICTED_SCOPE


class ToxicoRepository:
    def __init__(self, session: Session):
        self.session = session

    def scope_clause(self, scope: ToxicoScope) -> ColumnElement[bool]:
        """SEUL endroit qui encode la regle de perimetre (referent actuel du dossier)."""
        if scope.is_limited:
            return ToxicoDossier.psychologist_id == scope.own_psychologist_id
        return true()

    # =========================================================================
    # 1. LECTURE & RECHERCHE AVANCÉE
    # =========================================================================

    def search_dossiers(
        self, 
        search_query: str = None, 
        phase: int = None, 
        page: int = 1, 
        per_page: int = 20,
        scope: ToxicoScope = UNRESTRICTED_SCOPE,
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
            .filter(self.scope_clause(scope))
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
        scope: ToxicoScope = UNRESTRICTED_SCOPE,
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
            # Referent ACTUEL du dossier (pas le psychologue du dernier sejour).
            .filter(self.scope_clause(scope))
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

    def involvement_clause(self, user_id: int) -> ColumnElement[bool]:
        """Dossier "suivi auparavant" par user_id : il n'en est PAS le referent
        actuel ET un transfert depuis lui, un sejour ou une evaluation est a son nom."""
        return and_(
            ToxicoDossier.psychologist_id.is_distinct_from(user_id),
            or_(
                exists().where(ToxicoPsychologistTransfer.dossier_id == ToxicoDossier.id,
                               ToxicoPsychologistTransfer.from_psychologist_id == user_id),
                exists().where(ToxicoStay.dossier_id == ToxicoDossier.id,
                               ToxicoStay.psychologist_id == user_id),
                exists().where(ToxicoEvaluation.dossier_id == ToxicoDossier.id,
                               ToxicoEvaluation.created_by == user_id),
            ),
        )

    def get_referent_id(self, dossier_id: int) -> Optional[int]:
        """Psychologue referent courant du dossier (None s'il n'en a pas).
        ValueError si le dossier n'existe pas."""
        row = self.session.query(ToxicoDossier.psychologist_id).filter(
            ToxicoDossier.id == dossier_id).first()
        if row is None:
            raise ValueError("Dossier introuvable")
        return row[0]

    def get_dossier_access(self, dossier_id: int, scope: ToxicoScope) -> Literal['full', 'readonly', 'none']:
        """'none' si le dossier n'existe pas OU est hors perimetre (indiscernables),
        'readonly' pour un dossier suivi auparavant, 'full' sinon."""
        if dossier_id is None:
            return 'none'
        exists_q = self.session.query(ToxicoDossier.id).filter(ToxicoDossier.id == dossier_id)
        if not scope.is_limited:
            return 'full' if exists_q.first() is not None else 'none'
        if exists_q.filter(self.scope_clause(scope)).first() is not None:
            return 'full'
        if exists_q.filter(self.involvement_clause(scope.own_psychologist_id)).first() is not None:
            return 'readonly'
        return 'none'

    def get_dossier_id_for_patient(self, patient_id: int) -> Optional[int]:
        row = (self.session.query(ToxicoDossier.id)
               .filter(ToxicoDossier.patient_id == patient_id).first())
        return row[0] if row else None

    def list_previously_followed(self, user_id: int, search: Optional[str] = None,
                                 page: int = 1, per_page: int = 20) -> Tuple[List[ToxicoDossier], int]:
        """Dossiers (actifs ou sortis) suivis auparavant par user_id, patient et referent charges."""
        query = (
            self.session.query(ToxicoDossier)
            .join(ToxicoDossier.patient)
            .options(joinedload(ToxicoDossier.patient), joinedload(ToxicoDossier.psychologist))
            .filter(self.involvement_clause(user_id))
        )
        if search and search.strip():
            raw = search.strip()
            esc = raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            term = f"%{esc}%"
            query = query.filter(or_(
                Patient.last_name.ilike(term, escape="\\"),
                Patient.first_name.ilike(term, escape="\\"),
                Patient.code_patient.ilike(term, escape="\\"),
                (Patient.first_name + " " + Patient.last_name).ilike(term, escape="\\"),
                (Patient.last_name + " " + Patient.first_name).ilike(term, escape="\\"),
            ))
        total = query.order_by(None).count()
        items = (query.order_by(Patient.last_name, Patient.first_name, ToxicoDossier.id)
                 .offset((page - 1) * per_page).limit(per_page).all())
        return items, total

    def get_dossier_full(self, patient_id: int,
                         scope: ToxicoScope = UNRESTRICTED_SCOPE) -> Optional[ToxicoDossier]:
        """
        Charge tout le dossier avec l'historique complet pour la vue détaillée.
        Psychologue limite : None si le dossier est hors perimetre (acces 'none').
        """
        if scope.is_limited:
            dossier_id = self.get_dossier_id_for_patient(patient_id)
            if self.get_dossier_access(dossier_id, scope) == 'none':
                return None
        return (
            self.session.query(ToxicoDossier)
            .options(
                joinedload(ToxicoDossier.patient),
                # ✅ CORRECTION : Supprimer order_by sur le joinedload
                joinedload(ToxicoDossier.phase_history), 
                joinedload(ToxicoDossier.evaluations).joinedload(ToxicoEvaluation.evaluator),
                selectinload(ToxicoDossier.stays).joinedload(ToxicoStay.psychologist),
                selectinload(ToxicoDossier.stays).joinedload(ToxicoStay.discharger),
                selectinload(ToxicoDossier.transfers),
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

        # Changement de referent a la readmission : jamais de reassignation non
        # tracee. Une ligne de transfert automatique est ecrite dans la MEME
        # transaction (pas de notification : le nouveau referent voit deja le
        # patient dans sa liste). Meme referent : rien n'est ecrit.
        previous_referent = dossier.psychologist_id
        new_referent = toxico_data['psychologist_id']
        referent_changes = previous_referent != new_referent
        if referent_changes and not toxico_data.get('decided_by'):
            raise ToxicoValidationError(
                "Auteur de la réadmission inconnu : changement de psychologue non traçable.",
                code="transfer_author_required")

        dossier.is_active = True
        dossier.admission_date = toxico_data['admission_date']
        dossier.substance = toxico_data['substance']
        dossier.psychologist_id = new_referent
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
        if referent_changes:
            self.session.add(ToxicoPsychologistTransfer(
                dossier_id=dossier.id,
                from_psychologist_id=previous_referent,
                to_psychologist_id=new_referent,
                decided_by=toxico_data['decided_by'],
                decided_at=business_now(),
                reason=READMISSION_TRANSFER_REASON,
                stay_id=stay.id,
            ))
        return dossier

    def transfer_dossier(self, dossier_id: int, to_psychologist_id: int, reason: str,
                         decided_by: int) -> ToxicoPsychologistTransfer:
        """Transfere le dossier a un autre psychologue : ligne d'historique,
        referent du dossier ET du sejour ouvert (les sejours clos gardent leur
        psychologue), notification du nouveau referent. Un seul commit ; toute
        erreur (notification comprise) annule tout et remonte."""
        from repositories.notification_repo import NotificationRepository
        reason = (reason or "").strip()
        if not reason or len(reason) > TRANSFER_REASON_MAX:
            raise ToxicoValidationError(
                f"Le motif du transfert est obligatoire ({TRANSFER_REASON_MAX} caractères au plus).",
                code="transfer_reason_required")
        try:
            dossier = (self.session.query(ToxicoDossier)
                       .filter(ToxicoDossier.id == dossier_id)
                       .with_for_update().first())
            if dossier is None:
                raise ToxicoNotFoundError("Dossier introuvable")
            target = (
                self.session.query(User)
                .join(ApplicationRole, User.role_id == ApplicationRole.role_id)
                .filter(User.user_id == to_psychologist_id, User.is_active == True)  # noqa: E712
                .filter(ApplicationRole.role_name == 'Psychologist')
                .first()
            )
            if target is None:
                raise ToxicoValidationError(
                    "Le destinataire doit être un psychologue actif.", code="transfer_target_invalid")
            if dossier.psychologist_id == target.user_id:
                raise ToxicoConflictError(
                    "Ce psychologue est déjà le référent de ce patient.", code="transfer_same_referent")

            stay = self.get_open_stay(dossier.id)
            previous = self.session.get(User, dossier.psychologist_id) if dossier.psychologist_id else None
            decider = self.session.get(User, decided_by)
            patient = self.session.get(Patient, dossier.patient_id)
            transfer = ToxicoPsychologistTransfer(
                dossier_id=dossier.id,
                from_psychologist_id=dossier.psychologist_id,
                to_psychologist_id=target.user_id,
                decided_by=decided_by,
                decided_at=business_now(),
                reason=reason,
                stay_id=stay.id if stay else None,
            )
            self.session.add(transfer)
            dossier.psychologist_id = target.user_id
            if stay is not None:
                stay.psychologist_id = target.user_id
            self.session.flush()

            NotificationRepository(self.session).create(
                recipient_user_id=target.user_id,
                type="toxico_transfer",
                payload={
                    "dossier_id": dossier.id,
                    "patient_id": dossier.patient_id,
                    "patient_name": (f"{patient.first_name or ''} {patient.last_name or ''}".strip()
                                     if patient else None),
                    "from_name": previous.full_name if previous else None,
                    "decided_by_name": decider.full_name if decider else None,
                },
            )
            self.session.commit()
            return transfer
        except Exception:
            self.session.rollback()
            raise

    def process_evaluation(self, dossier_id: int, data: dict, user_id: int) -> ToxicoEvaluation:
        """
        Gère l'évaluation et la machine à états des phases.
        """
        try:
            # Verrou de ligne : un transfert concurrent est serialise avec nous.
            dossier = (self.session.query(ToxicoDossier)
                       .filter(ToxicoDossier.id == dossier_id)
                       .with_for_update().first())
            if not dossier: raise ValueError("Dossier introuvable")
            if dossier.psychologist_id != user_id:
                raise ToxicoForbiddenError(
                    "Seul le psychologue référent de ce dossier peut ajouter une évaluation.",
                    code="not_referent")
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

    def active_stats(self, scope: ToxicoScope = UNRESTRICTED_SCOPE) -> dict:
        """Chiffres des dossiers actifs du perimetre (jamais limites a la page ni a la
        recherche de la liste). Psychologue limite : by_psychologist toujours vide."""
        active = and_(ToxicoDossier.is_active == True, self.scope_clause(scope))  # noqa: E712
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
        by_psy = {} if scope.is_limited else {(name or "Non assigné"): n for name, n in (
            self.session.query(User.full_name, func.count(ToxicoDossier.id))
            .select_from(ToxicoDossier).outerjoin(User, User.user_id == ToxicoDossier.psychologist_id)
            .filter(active).group_by(User.full_name).all())}
        week_ago = date.today() - timedelta(days=7)
        new_week = (self.session.query(func.count(ToxicoDossier.id))
                    .filter(active, ToxicoDossier.admission_date >= week_ago).scalar() or 0)
        return {"total_active": total, "by_phase": by_phase, "relapse_patients": relapse_patients,
                "by_substance": by_substance, "by_psychologist": by_psy, "new_this_week": new_week}

    def count_dossiers_created_since(self, start_date, end_date=None,
                                     scope: ToxicoScope = UNRESTRICTED_SCOPE):
        """Compte les séjours commencés (admissions + réadmissions, par
        admission_date) dans [start_date, end_date) ; sans end_date : jusqu'à
        aujourd'hui inclus (un séjour daté dans le futur n'est pas compté).
        Perimetre : referent ACTUEL du dossier du sejour."""
        def _d(v):
            return v.date() if isinstance(v, datetime) else v
        start = _d(start_date)
        q = (self.session.query(ToxicoStay)
             .join(ToxicoDossier, ToxicoDossier.id == ToxicoStay.dossier_id)
             .filter(self.scope_clause(scope))
             .filter(ToxicoStay.admission_date >= start))
        if end_date is not None:
            q = q.filter(ToxicoStay.admission_date < _d(end_date))
        else:
            q = q.filter(ToxicoStay.admission_date <= date.today())
        return q.count()