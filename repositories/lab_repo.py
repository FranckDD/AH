#lab_repo.py

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import desc, or_, cast, String, func, and_
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
import uuid

# Assure-toi que ces imports correspondent à tes modèles
from models.lab import (
    Examen, Parametre, ReferenceRange,
    LabResult, LabResultDetail, LabResultAmendment, LabExternalPrescriber
)
from repositories.notification_repo import NotificationRepository
from typing import NamedTuple
from utils.business_time import business_now, business_today, BUSINESS_TZ
from utils.lab_age import age_in_days, format_age, parse_external_age
from utils.lab_reference import normalize_sex, select_range, flag_word
from utils.lab_dossier import DossierNotAssignedError, ensure_dossier_assigned
from utils.lab_snapshot import build_print_snapshot
from models.prescription import Prescription
from models.caisse import Caisse
from models.caisse_item import CaisseItem
from models.patient import Patient

class PatientBio(NamedTuple):
    """Age en jours (None si inconnu), code sexe 'M'/'F'/'X', SA du resultat (None si inconnue) et
    libelle d'age pour l'affichage (None si age inconnu)."""
    age_days: Optional[int]
    sex: str
    ga_weeks: Optional[int]
    age_label: Optional[str]


def reference_date_for(result) -> date:
    """Date de reference de l'age : jour de reception (test_date) converti en date de Douala,
    a defaut le jour metier courant. Un horodatage naif est une heure de Douala (c'est ainsi que
    les dossiers sont enregistres) : il ne depend jamais du fuseau du processus."""
    td = getattr(result, "test_date", None)
    if isinstance(td, datetime):
        if td.tzinfo is None:
            return td.date()
        return td.astimezone(BUSINESS_TZ).date()
    return business_today()


def patient_bio(result) -> PatientBio:
    """Age en jours exacts a la date de reception, sexe, SA et libelle d'age. Patient interne
    (date de naissance, genre) ou externe (JSON : age_days, sinon age en annees). Date de
    naissance absente ou future : age inconnu (None), jamais 0."""
    ref = reference_date_for(result)
    ga = getattr(result, "gestational_age_weeks", None)
    days = None
    if result.patient:
        dob = result.patient.birth_date
        if dob:
            try:
                days = age_in_days(dob, ref)
            except ValueError:
                days = None
        sex = normalize_sex(getattr(result.patient, 'gender', None))
    elif result.external_patient_info:
        info = result.external_patient_info
        days = parse_external_age(info)
        sex = normalize_sex(info.get('sexe') or info.get('gender'))
    else:
        sex = 'X'
    return PatientBio(days, sex, ga, format_age(days) if days is not None else None)



class LabResultLockedError(Exception):
    """Resultat valide : lecture seule, toute modification passe par la correction avec motif."""
    def __init__(self, result_id):
        super().__init__(f"Le resultat {result_id} est valide : utilisez la correction avec motif.")
        self.result_id = result_id


class LabResultNotValidatedError(Exception):
    """On ne corrige qu'un resultat deja valide ; avant cela on le saisit normalement."""
    def __init__(self, result_id):
        super().__init__(f"Le resultat {result_id} n'est pas encore valide : saisie normale.")
        self.result_id = result_id


class LabRepository:
    def __init__(self, session: Session):
        self.session = session

    # =========================================================================
    # 1. CATALOGUE (Examens, Paramètres, Valeurs de référence)
    # =========================================================================

    def get_exams_by_ids(self, ids: List[int]) -> List[Examen]:
        """Récupère plusieurs examens en une seule requête (Optimisation Batch)"""
        return self.session.query(Examen).filter(Examen.id.in_(ids)).all()
    
    # --- Examens ---
    def create_examen(self, data: Dict[str, Any]) -> Examen:
        examen = Examen(**data)
        self.session.add(examen)
        self.session.commit()
        self.session.refresh(examen)
        return examen

    def update_examen(self, examen_id: int, data: Dict[str, Any]) -> Optional[Examen]:
        examen = self.session.get(Examen, examen_id)
        if examen:
            for k, v in data.items():
                setattr(examen, k, v)
            self.session.commit()
            self.session.refresh(examen)
            return examen
        return None

    def delete_examen(self, examen_id: int) -> bool:
        examen = self.session.get(Examen, examen_id)
        if examen:
            # Les parametres et leurs plages n'ont de sens que pour l'examen : suppression en cascade
            # (le controleur a deja refuse si des resultats l'utilisent).
            param_ids = [r[0] for r in self.session.query(Parametre.id).filter(Parametre.examen_id == examen_id).all()]
            if param_ids:
                self.session.query(ReferenceRange).filter(
                    ReferenceRange.parametre_id.in_(param_ids)).delete(synchronize_session=False)
                self.session.query(Parametre).filter(
                    Parametre.id.in_(param_ids)).delete(synchronize_session=False)
            self.session.expire(examen)
            self.session.delete(examen)
            self.session.commit()
            return True
        return False

    def list_all_examens(self) -> List[Examen]:
        # Examens inactifs (catalogue) jamais proposes pour un nouveau resultat / une facture.
        return self.session.query(Examen).filter(Examen.is_active.is_(True)).order_by(Examen.nom).all()

    def get_examen_by_id(self, examen_id: int) -> Optional[Examen]:
        return self.session.get(Examen, examen_id)

    # --- Paramètres ---
    def create_parametre(self, data: Dict[str, Any]) -> Parametre:
        if not data.get('ordre'):
            top = self.session.query(func.max(Parametre.ordre)).filter(
                Parametre.examen_id == data.get('examen_id')).scalar()
            data = {**data, 'ordre': (top or 0) + 1}
        param = Parametre(**data)
        self.session.add(param)
        self.session.commit()
        self.session.refresh(param)
        return param
    
    def get_parametre(self, param_id: int) -> Optional[Parametre]:
        return self.session.get(Parametre, param_id)

    def list_parametres_for_examen(self, examen_id: int) -> List[Parametre]:
        """
        Optimisation : On charge immédiatement les reference_ranges 
        pour éviter le problème N+1 (une requête par paramètre).
        """
        return self.session.query(Parametre)\
            .options(joinedload(Parametre.reference_ranges))\
            .filter(Parametre.examen_id == examen_id)\
            .order_by(Parametre.ordre, Parametre.id)\
            .all()

    def reorder_parametres(self, examen_id: int, ids: List[int]) -> bool:
        """Applique l'ordre donne (1..n). False si la liste n'est pas exactement
        l'ensemble des parametres de l'examen."""
        params = {p.id: p for p in self.session.query(Parametre).filter(Parametre.examen_id == examen_id).all()}
        if len(ids) != len(set(ids)) or set(ids) != set(params):
            return False
        for pos, pid in enumerate(ids, start=1):
            params[pid].ordre = pos
        self.session.commit()
        return True
    
    def update_parametre(self, param_id: int, data: Dict[str, Any]) -> Optional[Parametre]:
        p = self.session.get(Parametre, param_id)
        if p:
            for k, v in data.items():
                setattr(p, k, v)
            self.session.commit()
            self.session.refresh(p)
            return p
        return None

    def examen_has_results(self, examen_id: int) -> bool:
        if self.session.query(LabResult.result_id).filter(LabResult.examen_id == examen_id).first() is not None:
            return True
        return self.session.query(LabResultDetail.detail_id).join(
            Parametre, Parametre.id == LabResultDetail.parametre_id
        ).filter(Parametre.examen_id == examen_id).first() is not None

    def parametre_has_results(self, parametre_id: int) -> bool:
        return self.session.query(LabResultDetail.detail_id).filter(
            LabResultDetail.parametre_id == parametre_id).first() is not None

    def delete_parametre(self, parametre_id: int) -> bool:
        p = self.session.get(Parametre, parametre_id)
        if p:
            self.session.query(ReferenceRange).filter(
                ReferenceRange.parametre_id == parametre_id).delete(synchronize_session=False)
            self.session.delete(p)
            self.session.commit()
            return True
        return False

    # --- Reference Ranges ---
    def create_reference_range(self, data: Dict[str, Any]) -> ReferenceRange:
        rr = ReferenceRange(**data)
        self.session.add(rr)
        self.session.commit()
        self.session.refresh(rr)
        return rr

    def list_reference_ranges(self, parametre_id: Optional[int] = None) -> List[ReferenceRange]:
        q = self.session.query(ReferenceRange)
        if parametre_id:
            q = q.filter(ReferenceRange.parametre_id == parametre_id)
        return q.all()
    
    def get_reference_range(self, range_id: int) -> Optional[ReferenceRange]:
        return self.session.get(ReferenceRange, range_id)
    
    def update_reference_range(self, range_id: int, data: Dict) -> Optional[ReferenceRange]:
        rr = self.session.get(ReferenceRange, range_id)
        if rr:
            for k, v in data.items():
                setattr(rr, k, v)
            self.session.commit()
            self.session.refresh(rr)
            return rr
        return None

    def delete_reference_range(self, range_id: int) -> bool:
        rr = self.session.get(ReferenceRange, range_id)
        if rr:
            self.session.delete(rr)
            self.session.commit()
            return True
        return False

    # =========================================================================
    # 2. FILE D'ATTENTE (WORKLIST) - PONT MÉDICAL
    # =========================================================================

    def get_active_worklist(self) -> List[LabResult]:
        """
        Récupère uniquement les dossiers présents dans la table LAB_RESULTS
        qui sont en cours de traitement (PENDING ou PARTIAL).
        C'est ça que la 'Paillasse' doit afficher.
        """
        return self.session.query(LabResult)\
            .options(
                joinedload(LabResult.patient), # Pour afficher le nom
                joinedload(LabResult.examen)   # Pour afficher le type d'examen
            )\
            .filter(LabResult.status.in_(['pending', 'partial']))\
            .order_by(desc(LabResult.test_date))\
            .all()

    def get_lab_worklist(self) -> List[Dict[str, Any]]:
        """Récupère les prescriptions médicales en attente de traitement."""
        subquery = self.session.query(LabResult.origin_prescription_id).filter(
            LabResult.origin_prescription_id.isnot(None)
        )
        query = self.session.query(Prescription).options(joinedload(Prescription.patient)).filter(
            and_(
                Prescription.is_lab_order == True,
                Prescription.status == 'active',
                ~Prescription.prescription_id.in_(subquery)
            )
        ).order_by(desc(Prescription.start_date))

        return [{
            "prescription_id": p.prescription_id,
            "date": p.start_date,
            "patient_id": p.patient_id,
            "patient_name": f"{p.patient.last_name} {p.patient.first_name}" if p.patient else "Inconnu",
            "exams_requested": p.lab_exams_list,
            "doctor": p.prescribed_by_name,
            "notes": p.notes
        } for p in query.all()]

    # =========================================================================
    # 3. GESTION DES RÉSULTATS (Cœur du métier Laborantin)
    # =========================================================================

    @staticmethod
    def period_start(filter_type: str = "month") -> datetime:
        """Debut de la periode du dashboard ('day' | 'month' | 'year')."""
        now = datetime.now()
        if filter_type == "day":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        if filter_type == "year":
            return now.replace(month=1, day=1, hour=0, minute=0, second=0)
        return now.replace(day=1, hour=0, minute=0, second=0)

    def get_paginated_history(self, skip: int = 0, limit: int = 20, search_query: Optional[str] = None, status: Optional[str] = None,
                              abnormal_only: bool = False, period: Optional[str] = None,
                              group_by_batch: bool = False) -> Tuple[int, List[LabResult]]:
        """
        Récupère l'historique des résultats de laboratoire avec pagination.
        Retourne le nombre total d'éléments (pour le front) et la liste de la page demandée.

        group_by_batch=True : la pagination porte sur les PASSAGES patient (un batch_id = un passage ;
        un examen sans batch_id est son propre passage). Le total est le nombre de passages et
        un passage n'est jamais coupe entre deux pages.
        """
        conditions = []

        # 1. Filtre par recherche texte (si renseigné)
        if search_query:
            q_term = f"%{search_query.lower()}%"
            conditions.append(
                or_(
                    LabResult.code_lab_patient.ilike(q_term),
                    LabResult.patient.has(Patient.last_name.ilike(q_term)),
                    LabResult.patient.has(Patient.first_name.ilike(q_term)),
                    cast(LabResult.external_patient_info['nom'], String).ilike(q_term),
                    cast(LabResult.external_patient_info['name'], String).ilike(q_term)
                )
            )

        # 2. Filtre par statut (ex: 'completed', 'pending')
        # 'pending' = tout ce qui n'est pas termine (pending, partial, analyzed) : une demande "en cours"
        # recue aujourd'hui doit apparaitre dans ce filtre.
        if status == 'pending':
            conditions.append(LabResult.status != 'completed')
        elif status:
            conditions.append(LabResult.status == status)

        # 2b. Cas anormaux : au moins un parametre flagge. `period` reprend
        # exactement la fenetre du dashboard (carte "Pathologiques") pour que
        # le total affiche ici soit celui de la carte cliquee.
        if abnormal_only:
            conditions.append(LabResult.details.any(LabResultDetail.flagged == True))
        if period:
            conditions.append(LabResult.test_date >= self.period_start(period))

        if group_by_batch:
            return self._paginated_history_by_passage(conditions, skip, limit)

        query = self.session.query(LabResult)\
            .options(joinedload(LabResult.patient), joinedload(LabResult.examen))\
            .outerjoin(LabResult.patient)\
            .filter(*conditions)

        # 3. Compter le total d'éléments correspondant aux filtres (AVANT la pagination)
        total_count = query.count()

        # 4. Appliquer le tri (le plus récent en premier) et la pagination (offset/limit)
        results = query.order_by(desc(LabResult.test_date))\
                       .offset(skip)\
                       .limit(limit)\
                       .all()

        return total_count, results

    @staticmethod
    def _passage_key():
        """Cle d'un passage : le batch_id, ou l'identifiant du resultat quand il n'y en a pas."""
        return func.coalesce(cast(LabResult.batch_id, String), cast(LabResult.result_id, String))

    def _paginated_history_by_passage(self, conditions, skip: int, limit: int) -> Tuple[int, List[LabResult]]:
        key = self._passage_key()
        base = self.session.query(LabResult).outerjoin(LabResult.patient).filter(*conditions)

        total_passages = (self.session.query(func.count(func.distinct(key)))
                          .select_from(LabResult).outerjoin(LabResult.patient).filter(*conditions).scalar() or 0)

        page_keys = [k for k, _ in (
            self.session.query(key.label('k'), func.max(LabResult.test_date).label('d'))
            .select_from(LabResult).outerjoin(LabResult.patient).filter(*conditions)
            .group_by(key).order_by(desc('d'), desc('k')).offset(skip).limit(limit).all())]
        if not page_keys:
            return total_passages, []

        rows = (base.options(joinedload(LabResult.patient), joinedload(LabResult.examen))
                .filter(key.in_(page_keys)).all())
        rank = {k: i for i, k in enumerate(page_keys)}
        rows.sort(key=lambda r: (rank[str(r.batch_id) if r.batch_id else str(r.result_id)], r.result_id))
        return total_passages, rows

    def get_batch_exams(self, batch_ids: List[uuid.UUID]) -> Dict[str, List[Dict[str, Any]]]:
        """Examens de chaque passage (termines compris), par batch_id : [{result_id, examen_nom, status}]."""
        out: Dict[str, List[Dict[str, Any]]] = {}
        if not batch_ids:
            return out
        for r in sorted(self.get_results_by_batch_ids(list(batch_ids)), key=lambda x: x.result_id):
            out.setdefault(str(r.batch_id), []).append({
                'result_id': r.result_id,
                'examen_nom': r.examen.nom if r.examen else 'Inconnu',
                'status': r.status,
            })
        return out

    def _generate_analysis_code(self, is_external: bool, result_id: int) -> str:
        now = datetime.now()
        month_day = now.strftime("%m%d")
        suffix = f"{result_id:04d}" 
        prefix = "EXT" if is_external else "LAB"
        return f"{prefix}-{month_day}-{suffix}"

    def create_lab_result(self, data: Dict[str, Any]) -> LabResult:
        # 1. On sépare les détails (s'ils sont fournis manuellement) du reste
        details_data = data.pop('details', [])
        # uuid client (dossier cree hors ligne) : sorti de `data` AVANT la
        # construction du modele - voir commentaire plus bas.
        client_uuid = data.pop('uuid', None)
        passed_code = data.get('code_lab_patient')

        try:
            # --- Initialisation des valeurs par défaut ---
            if not data.get('test_type'):
                data['test_type'] = "Analyse Labo"

            # Gestion du code temporaire si non fourni
            if not passed_code:
                data['code_lab_patient'] = "TEMP_GENERATING"

            # 2. Création de l'entête (Table LAB_RESULTS)
            result = LabResult(**data)
            self.session.add(result)
            self.session.flush() # CRUCIAL : Génère l'ID (result.result_id) sans valider la transaction

            # Explicite APRES flush uniquement : un uuid=None passe au
            # constructeur ecraserait le DEFAULT gen_random_uuid() de la
            # colonne (piege deja documente sur patients/medical_records/
            # prescriptions - Postgres traite une valeur explicitement NULL
            # differemment d'une colonne absente).
            if client_uuid:
                result.uuid = uuid.UUID(str(client_uuid))

            # --- Logique de génération du Code (inchangée) ---
            if result.code_lab_patient == "TEMP_GENERATING":
                is_external = (result.patient_id is None)
                generated_code = self._generate_analysis_code(is_external, result.result_id)
                
                # Vérification unicité simple
                exists = self.session.query(LabResult).filter(LabResult.code_lab_patient == generated_code).first()
                if exists:
                    generated_code = f"{generated_code}-{result.result_id}"
                
                result.code_lab_patient = generated_code
            else:
                result.code_lab_patient = passed_code # type: ignore

            # =================================================================
            # 3. CRÉATION AUTOMATIQUE DES DÉTAILS (Table LAB_RESULT_DETAILS)
            # =================================================================
            
            # CAS A : L'examen est défini (ex: ID 5 = NFS) mais pas de détails fournis
            # -> On va chercher la définition de l'examen pour créer les lignes vides
            if result.examen_id and not details_data:
                # Récupère tous les paramètres de cet examen (Hgb, GB, PLT...)
                params = [p for p in self.list_parametres_for_examen(result.examen_id) if p.is_active]
                
                if not params:
                    print(f"ATTENTION: L'examen ID {result.examen_id} n'a aucun paramètre configuré !")
                
                new_details = []
                for p in params:
                    # On crée une ligne vide pour chaque paramètre
                    detail = LabResultDetail(
                        result_id=result.result_id,  # Lien avec le dossier parent
                        parametre_id=p.id,           # Lien avec la définition (Hgb)
                        valeur_num=None,
                        valeur_text="",             # Vide par défaut
                        flagged=False
                    )
                    self.session.add(detail)
            
            # CAS B : Des détails spécifiques sont fournis (ex: Importation, ou reprise)
            elif details_data:
                for d in details_data:
                    # Conversion Pydantic -> Dict si nécessaire
                    d_dict = d.model_dump() if hasattr(d, 'model_dump') else d
                    d_dict['result_id'] = result.result_id # On force le lien parent
                    
                    self.session.add(LabResultDetail(**d_dict))

            # Resultat cree deja valide (import, reprise) : meme copie figee que la validation par le banc.
            if result.status == "completed":
                self.session.flush()
                self.session.refresh(result, attribute_names=['details', 'examen'])
                self.freeze_print_snapshot(result, data.get('last_updated_by') or data.get('created_by'))

            # 4. Validation finale
            self.session.commit()
            self.session.refresh(result)
            
            # Petite astuce : on recharge les détails pour être sûr qu'ils sont dispos de suite
            # si l'appelant veut les lire immédiatement
            self.session.refresh(result, attribute_names=['details'])
            
            return result

        except Exception as e:
            self.session.rollback()
            print(f"ERREUR create_lab_result: {str(e)}") # Log serveur utile
            raise e

    def get_lab_result_by_uuid(self, client_uuid: str) -> Optional[LabResult]:
        """Rejeu idempotent d'un dossier labo cree hors ligne - meme motif
        que la resolution patient/consultation par uuid (chantier 4 sous-
        projet 4)."""
        return self.session.query(LabResult).filter(
            LabResult.uuid == uuid.UUID(str(client_uuid))
        ).first()

    def upsert_external_prescriber(self, title: str, name: str) -> None:
        """Memorise un prescripteur externe (ou rafraichit sa date d'usage). Insertion sans doublon, titre + nom insensible a la casse."""
        existing = self.session.query(LabExternalPrescriber).filter(
            LabExternalPrescriber.title == title,
            # lower() cote base des DEUX cotes : meme fonction que l'index unique (title, lower(name)),
            # donc un nom accentue ne peut jamais echapper a la recherche puis violer l'index.
            func.lower(LabExternalPrescriber.name) == func.lower(name),
        ).first()
        if existing:
            existing.last_used_at = business_now()
        else:
            self.session.add(LabExternalPrescriber(title=title, name=name, last_used_at=business_now()))
        self.session.flush()

    def search_external_prescribers(self, q: str = "", limit: int = 20) -> List[LabExternalPrescriber]:
        """Suggestions : les plus recemment utilises d'abord, filtre insensible a la casse sur le nom."""
        query = self.session.query(LabExternalPrescriber)
        term = (q or "").strip()
        if term:
            escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.filter(LabExternalPrescriber.name.ilike(f"%{escaped}%", escape="\\"))
        return query.order_by(desc(LabExternalPrescriber.last_used_at), desc(LabExternalPrescriber.id)).limit(limit).all()

    def get_lab_result_by_batch_uuid(self, batch_uuid: str) -> Optional[LabResult]:
        """Premier dossier deja cree pour ce lot hors ligne (batch_uuid
        client) - permet de reutiliser le meme code_lab_patient quand les
        items d'un meme lot arrivent dans des appels HTTP separes (chaque
        ligne locale genere sa propre operation d'envoi PowerSync,
        contrairement a la creation en ligne qui envoie tout le lot en un
        seul appel synchrone)."""
        return self.session.query(LabResult).filter(
            LabResult.batch_uuid == batch_uuid
        ).order_by(LabResult.result_id.asc()).first()

    def get_full_lab_result(self, result_id: int) -> Optional[LabResult]:
        return self.session.query(LabResult).options(
            # On chaîne jusqu'aux reference_ranges pour tout charger en 1 seule requête SQL
            joinedload(LabResult.details)\
                .joinedload(LabResultDetail.parametre)\
                .joinedload(Parametre.reference_ranges), # <-- L'AJOUT EST ICI
            joinedload(LabResult.examen),
            joinedload(LabResult.patient)
        ).filter(LabResult.result_id == result_id).first()

    def list_results(self, status: Optional[str] = None) -> List[LabResult]:
        query = self.session.query(LabResult).options(joinedload(LabResult.patient), joinedload(LabResult.examen))
        if status: query = query.filter(LabResult.status == status)
        return query.order_by(desc(LabResult.test_date)).all()

    def list_results_for_patient(self, patient_id: int) -> List[LabResult]:
        return self.session.query(LabResult).filter(LabResult.patient_id == patient_id)\
            .options(joinedload(LabResult.examen)).order_by(desc(LabResult.test_date)).all()
    
    def list_results_by_date(self, start_date: datetime, end_date: datetime) -> List[LabResult]:
        return self.session.query(LabResult).filter(LabResult.test_date >= start_date, LabResult.test_date <= end_date).all()

    # =========================================================================
    # 4. RECHERCHE & INTERPRÉTATION
    # =========================================================================

    @staticmethod
    def _norm_name(value: Any) -> str:
        return str(value or "").strip().lower()

    def get_reception_candidates(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Patients internes a recevoir au labo : ordonnances d'examens actives (lignes restantes
        seulement) et examens factures a la caisse non encore recus. Une ligne deja recue (dossier
        labo existant, quel que soit son statut) n'est plus jamais proposee.

        Une entree par ordonnance qui garde des lignes ; un patient qui n'a que des lignes de
        facture a une entree sans ordonnance (prescription_id None). Les lignes de facture sont
        portees par la premiere entree du patient."""
        term = f"%{search_term.lower()}%"
        patients = self.session.query(Patient).filter(
            or_(func.lower(Patient.last_name).like(term), func.lower(Patient.first_name).like(term),
                Patient.code_patient.ilike(term))
        ).order_by(Patient.last_name, Patient.first_name).limit(limit).all()
        if not patients:
            return []
        pids = [p.patient_id for p in patients]

        prescriptions = self.session.query(Prescription).filter(
            Prescription.patient_id.in_(pids), Prescription.status == 'active',
            Prescription.is_lab_order == True).order_by(Prescription.prescription_id).all()

        # Lignes d'ordonnance deja recues : prescription_id -> noms d'examens normalises
        received_by_presc: Dict[int, set] = {}
        if prescriptions:
            rows = self.session.query(LabResult.origin_prescription_id, Examen.nom).join(
                Examen, Examen.id == LabResult.examen_id).filter(
                LabResult.origin_prescription_id.in_([pr.prescription_id for pr in prescriptions])).all()
            for pid_, nom in rows:
                received_by_presc.setdefault(pid_, set()).add(self._norm_name(nom))

        invoiced = self.session.query(CaisseItem, Caisse.patient_id, Examen).join(
            Caisse, Caisse.transaction_id == CaisseItem.transaction_id).join(
            Examen, Examen.id == CaisseItem.item_ref_id).filter(
            Caisse.patient_id.in_(pids), Caisse.status == 'active', CaisseItem.status == 'active',
            CaisseItem.item_type.ilike('%exam%'),
            ~self.session.query(LabResult.result_id).filter(
                LabResult.origin_caisse_item_id == CaisseItem.item_id).exists()
        ).order_by(CaisseItem.item_id).all()
        invoiced_by_patient: Dict[int, List[Dict[str, Any]]] = {}
        for item, pid_, ex in invoiced:
            invoiced_by_patient.setdefault(pid_, []).append({
                "item_id": item.item_id, "examen_id": ex.id, "nom": ex.nom, "transaction_id": item.transaction_id})

        out: List[Dict[str, Any]] = []
        for p in patients:
            entries: List[Dict[str, Any]] = []
            # Identite utile a l'ecran de reception : age exact (naissance), sexe, et suivi de grossesse du dossier
            # (ces trois derniers champs sont retires par le filtre central pour tout role non autorise).
            card = {
                "birth_date": p.birth_date.isoformat() if p.birth_date else None,
                "gender": p.gender,
                "pregnancy_status": p.pregnancy_status or "inconnu",
                "expected_delivery_date": p.expected_delivery_date.isoformat() if p.expected_delivery_date else None,
                "pregnancy_program_number": p.pregnancy_program_number,
            }
            for pr in [x for x in prescriptions if x.patient_id == p.patient_id]:
                done = received_by_presc.get(pr.prescription_id, set())
                remaining = [n for n in (pr.lab_exams_list or []) if self._norm_name(n) not in done]
                if remaining:
                    entries.append({"id": p.patient_id, "nom": f"{p.last_name or ''} {p.first_name or ''}".strip(), "patient_code": p.code_patient,
                                    "prescription_id": pr.prescription_id, "exams_prescribed": remaining,
                                    "has_active_prescription": True, "invoiced_exams": [], **card})
            lines = invoiced_by_patient.get(p.patient_id, [])
            if lines and not entries:
                entries.append({"id": p.patient_id, "nom": f"{p.last_name or ''} {p.first_name or ''}".strip(), "patient_code": p.code_patient,
                                "prescription_id": None, "exams_prescribed": [],
                                "has_active_prescription": False, "invoiced_exams": [], **card})
            if entries:
                entries[0]["invoiced_exams"] = lines
            out.extend(entries)
        return out

    def lab_result_exists_for_caisse_item(self, caisse_item_id: int) -> bool:
        return self.session.query(LabResult.result_id).filter(
            LabResult.origin_caisse_item_id == caisse_item_id).first() is not None

    def lab_result_exists_for_prescription_exam(self, prescription_id: int, examen_id: int) -> bool:
        return self.session.query(LabResult.result_id).filter(
            LabResult.origin_prescription_id == prescription_id, LabResult.examen_id == examen_id).first() is not None

    def get_caisse_item(self, item_id: int) -> Optional[CaisseItem]:
        return self.session.get(CaisseItem, item_id)

    def search_results_unified(self, query_str: str) -> List[LabResult]:
        q = f"%{query_str}%"
        # AJOUT ICI : .options(...) pour charger Patient et Examen
        return self.session.query(LabResult)\
            .options(joinedload(LabResult.patient), joinedload(LabResult.examen))\
            .outerjoin(LabResult.patient)\
            .filter(
                or_(
                    LabResult.code_lab_patient.ilike(q),
                    LabResult.patient.has(Patient.last_name.ilike(q)),
                    LabResult.patient.has(Patient.first_name.ilike(q)),
                    cast(LabResult.external_patient_info['nom'], String).ilike(q),
                    cast(LabResult.external_patient_info['name'], String).ilike(q)
                )
            ).order_by(desc(LabResult.test_date)).limit(20).all()

    def _interpret_single_detail(self, detail: LabResultDetail, age: Optional[int], sex: str, ga: Optional[int] = None):
        """`age` en JOURS ; meme regle de selection que le banc et la fiche (utils.lab_reference)."""
        if detail.valeur_num is None: return
        ref = select_range(
            self.session.query(ReferenceRange).filter(ReferenceRange.parametre_id == detail.parametre_id).all(),
            sex, age, ga)

        if ref:
            if Decimal(str(ref.valeur_min)) <= detail.valeur_num <= Decimal(str(ref.valeur_max)):
                detail.interpretation, detail.flagged = "normal", False
            else:
                detail.interpretation, detail.flagged = "abnormal", True

    
    # ------------------------------------------------------------------ saisie des valeurs

    def _resolve_detail(self, result_id: int, raw_key) -> Optional[LabResultDetail]:
        """Ligne de resultat visee par une cle du client : detail_id, ou -parametre_id (ligne creee
        hors ligne, voir labGateway.js::getResultDetail), ou parametre_id (dossier cree hors ligne)."""
        try:
            d_id = int(raw_key)
        except (TypeError, ValueError):
            return None
        if d_id < 0:
            # Un serial Postgres est toujours positif : aucune ambiguite avec un detail_id.
            return self.session.query(LabResultDetail).filter(
                LabResultDetail.parametre_id == -d_id, LabResultDetail.result_id == result_id).first()
        detail = self.session.query(LabResultDetail).filter(
            LabResultDetail.detail_id == d_id, LabResultDetail.result_id == result_id).first()
        if not detail:
            detail = self.session.query(LabResultDetail).filter(
                LabResultDetail.parametre_id == d_id, LabResultDetail.result_id == result_id).first()
        return detail

    def _patient_bio(self, result: LabResult) -> PatientBio:
        return patient_bio(result)

    @staticmethod
    def _value_unchanged(detail: LabResultDetail, data: Dict[str, Any]) -> bool:
        """Vrai si la valeur (et un eventuel drapeau explicite) renvoyee est celle deja enregistree :
        le rejeu d'une operation deja appliquee ne doit pas etre pris pour une modification."""
        val = data.get("valeur")
        param = detail.parametre
        if param is not None and param.input_type == 'numeric':
            try:
                same = (Decimal(str(val)) == Decimal(str(detail.valeur_num))) if val not in (None, "") else detail.valeur_num is None
            except InvalidOperation:
                same = False
        else:
            same = (str(val) if val is not None else "") == (detail.valeur_text or "")
        if not same:
            return False
        flag = data.get("flag")
        if flag:
            return bool(flag not in ['N', '']) == bool(detail.flagged)
        return True

    def _apply_values(self, result: LabResult, values_map: Dict[Any, Any]) -> None:
        """Ecrit les valeurs saisies dans les lignes du dossier et calcule l'interpretation.
        Ne touche ni au statut ni a la note. Priorite au drapeau manuel (H/L/A/N), sinon jugement
        automatique avec la plage du sexe du patient."""
        bio = self._patient_bio(result)
        age, sex, ga = bio.age_days, bio.sex, bio.ga_weeks
        for raw_key, data in values_map.items():
            detail = self._resolve_detail(result.result_id, raw_key)
            if not detail:
                # Valeur orpheline (parametre retire du catalogue entre-temps) : on ignore plutot
                # que de faire echouer tout le dossier.
                continue
            val = data.get("valeur")
            manual_flag = data.get("flag")
            manual_interp = data.get("interpretation")

            param = detail.parametre
            if param.input_type == 'numeric':
                try:
                    detail.valeur_num = Decimal(str(val)) if val is not None else None
                    detail.valeur_text = str(val) if val is not None else ""

                    if manual_flag or manual_interp:
                        # Drapeau force par le technicien (H, L, A, N) : sans texte libre, on
                        # enregistre le mot du drapeau pour que la fiche ne soit jamais muette.
                        detail.flagged = bool(manual_flag and manual_flag not in ['N', ''])
                        detail.interpretation = manual_interp or flag_word(manual_flag)
                    elif detail.valeur_num is not None:
                        norme = select_range(param.reference_ranges, sex, age, ga)
                        if norme:
                            if detail.valeur_num < norme.valeur_min:
                                detail.interpretation = "Bas"
                                detail.flagged = True
                            elif detail.valeur_num > norme.valeur_max:
                                detail.interpretation = "Haut"
                                detail.flagged = True
                            else:
                                detail.interpretation = "Normal"
                                detail.flagged = False
                except Exception:
                    detail.valeur_num = None
            else:
                detail.valeur_text = str(val) if val is not None else ""
                detail.valeur_num = None
                if manual_flag or manual_interp:
                    detail.flagged = bool(manual_flag and manual_flag not in ['N', ''])
                    detail.interpretation = manual_interp or flag_word(manual_flag)
                else:
                    detail.flagged = False

    def freeze_print_snapshot(self, result: LabResult, user_id: Optional[int] = None) -> bool:
        """Ecrit la copie figee d'impression (utils/lab_snapshot.py) UNE seule fois : sans effet si elle existe
        deja. A appeler quand le resultat devient valide, valeurs deja appliquees, AVANT de toucher test_date
        (l'age de la copie est celui de la reception). Ne commit pas. Retourne True si elle vient d'etre faite."""
        if result.print_snapshot is not None:
            return False
        self._ensure_dossier(result)
        result.print_snapshot = self._make_snapshot(result)
        result.print_snapshot_at = business_now()
        result.print_snapshot_by = user_id
        return True

    def _ensure_dossier(self, result: LabResult) -> None:
        """Numero de dossier manquant (ancien resultat) : attribue avant de figer la copie. Ne bloque jamais la
        validation ; ne commit pas (la transaction de l'appelant s'en charge)."""
        try:
            ensure_dossier_assigned(result)
        except DossierNotAssignedError:
            pass

    def _make_snapshot(self, result: LabResult) -> Dict[str, Any]:
        return build_print_snapshot(result, result.examen, list(result.details), self._patient_bio(result))

    def save_results_values(self, result_id: int, values_map: Dict[int, Any], mark_completed: bool = False, global_note: Optional[str] = None,
                            global_conclusion: Optional[str] = None, user_id: Optional[int] = None) -> LabResult:
        try:
            result = self.session.query(LabResult)\
                .options(joinedload(LabResult.patient))\
                .filter(LabResult.result_id == result_id)\
                .first()

            if not result:
                raise ValueError(f"Dossier {result_id} introuvable.")

            if result.status == "completed":
                # Resultat valide : lecture seule pour le technicien. Un rejeu strictement identique
                # (connecteur hors ligne qui renvoie une operation deja appliquee) reste sans effet ;
                # toute vraie modification passe par la correction avec motif (amend_result).
                resolved = [(self._resolve_detail(result_id, k), v) for k, v in values_map.items()]
                unchanged = all(d is None or self._value_unchanged(d, v) for d, v in resolved)
                note_same = global_note is None or global_note == (result.note or "")
                concl_same = global_conclusion is None or global_conclusion == (result.conclusion or "")
                if unchanged and note_same and concl_same:
                    return result
                raise LabResultLockedError(result_id)

            if global_note is not None:
                result.note = global_note
            if global_conclusion is not None:
                result.conclusion = global_conclusion

            self._apply_values(result, values_map)

            if mark_completed:
                self.freeze_print_snapshot(result, user_id)
                result.status = "completed"
                result.test_date = func.now()
            else:
                result.status = "partial"

            self.session.commit()
            self.session.refresh(result)
            return result

        except LabResultLockedError:
            raise  # rien n'a ete modifie : pas de rollback
        except Exception as e:
            self.session.rollback()
            raise e

    def amend_result(self, result_id: int, values_map: Dict[Any, Any], global_note: Optional[str], reason: str,
                     user_id: Optional[int], user_name: Optional[str], global_conclusion: Optional[str] = None) -> LabResult:
        """Correction d'un resultat VALIDE : motif obligatoire, valeurs d'avant conservees
        (lab_result_amendments), resultat marque 'corrige', medecin prescripteur notifie.
        Le statut reste 'completed'."""
        reason = (reason or "").strip()
        if not reason:
            raise ValueError("Le motif de la correction est obligatoire.")
        try:
            result = self.session.query(LabResult)\
                .options(joinedload(LabResult.patient), joinedload(LabResult.examen))\
                .filter(LabResult.result_id == result_id).first()
            if not result:
                raise ValueError(f"Dossier {result_id} introuvable.")
            if result.status != "completed":
                raise LabResultNotValidatedError(result_id)

            previous = [{
                "detail_id": d.detail_id, "parametre_id": d.parametre_id,
                "parametre_nom": d.parametre.nom_parametre if d.parametre else None,
                "valeur_text": d.valeur_text, "valeur_num": float(d.valeur_num) if d.valeur_num is not None else None,
                "interpretation": d.interpretation, "flagged": bool(d.flagged),
            } for d in result.details]
            previous_note = result.note

            if global_note is not None:
                result.note = global_note
            if global_conclusion is not None:
                result.conclusion = global_conclusion
            self._apply_values(result, values_map)

            # Nouvelle copie figee : l'ancienne est archivee (print_snapshot_history, la plus ancienne en
            # premier) avec qui/quand/pourquoi ; un ancien resultat sans copie en recoit une ici.
            now = business_now()
            old_snap = result.print_snapshot
            result._snapshot_rewrite_ok = True
            if old_snap is not None:
                result.print_snapshot_history = list(result.print_snapshot_history or []) + [{
                    "snapshot": old_snap,
                    "snapshot_at": result.print_snapshot_at.isoformat() if result.print_snapshot_at else None,
                    "snapshot_by": result.print_snapshot_by, "replaced_at": now.isoformat(),
                    "replaced_by": user_id, "replaced_by_name": user_name, "reason": reason}]
            self._ensure_dossier(result)
            result.print_snapshot = self._make_snapshot(result)
            result.print_snapshot_at = now
            result.print_snapshot_by = user_id

            self.session.add(LabResultAmendment(
                result_id=result_id, amended_by=user_id, amended_by_name=user_name,
                amended_at=business_now(), reason=reason, previous_values=previous, previous_note=previous_note))
            result.corrected = True
            result.corrected_at = business_now()
            result.last_updated_by = user_id
            result.last_updated_by_name = user_name

            notify_user_id = result.prescribed_by
            if notify_user_id and notify_user_id != user_id:
                patient_name = (f"{result.patient.last_name} {result.patient.first_name}" if result.patient
                                else (result.external_patient_info or {}).get('nom', ''))
                NotificationRepository(self.session).create(notify_user_id, "lab_result_corrected", {
                    "result_id": result.result_id, "code": result.code_lab_patient,
                    "patient_name": patient_name, "examen_nom": result.examen.nom if result.examen else "",
                    "reason": reason, "amended_by_name": user_name,
                })

            self.session.commit()
            result._snapshot_rewrite_ok = False
            self.session.refresh(result)
            return result
        except (LabResultNotValidatedError, ValueError):
            raise  # rien n'a ete modifie : pas de rollback
        except Exception:
            self.session.rollback()
            raise

    def list_amendments(self, result_id: int) -> List[LabResultAmendment]:
        return self.session.query(LabResultAmendment)\
            .filter(LabResultAmendment.result_id == result_id)\
            .order_by(LabResultAmendment.amended_at.desc(), LabResultAmendment.amendment_id.desc()).all()

    def _get_patient_bio_info(self, result: LabResult) -> Tuple[int, str]:
        """(age en JOURS, code sexe 'M'/'F'/'X'). Age inconnu = 0 (affichage) ; pour choisir une plage
        de reference utiliser _patient_bio, qui distingue age inconnu (None) d'un nouveau-ne."""
        bio = self._patient_bio(result)
        return (bio.age_days if bio.age_days is not None else 0), bio.sex

    def get_results_by_batch_id(self, batch_id: uuid.UUID) -> List[LabResult]:
        """Récupère tous les examens d'un lot spécifique avec les infos Patient/Examen."""
        return self.session.query(LabResult)\
            .options(joinedload(LabResult.patient), joinedload(LabResult.examen))\
            .filter(LabResult.batch_id == batch_id)\
            .all()

    def get_results_by_batch_ids(self, batch_ids: List[uuid.UUID]) -> List[LabResult]:
        """
        Optimisation pour la recherche : 
        Récupère tous les frères/sœurs de plusieurs lots en une seule requête SQL.
        """
        return self.session.query(LabResult)\
            .options(joinedload(LabResult.patient), joinedload(LabResult.examen))\
            .filter(LabResult.batch_id.in_(batch_ids))\
            .all()

    # =========================================================================
    # 5. DASHBOARD & SUPPRESSION
    # =========================================================================

    def get_stats_counts(self, start_date: datetime) -> Dict[str, Any]:
        pending = self.session.query(func.count(LabResult.result_id))\
            .filter(LabResult.status.in_(['pending', 'partial', 'analyzed'])).scalar() or 0
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        completed_today = self.session.query(func.count(LabResult.result_id))\
            .filter(and_(LabResult.status == 'completed', LabResult.test_date >= today_start)).scalar() or 0
        revenue = self.session.query(func.sum(Examen.prix)).join(LabResult.examen)\
            .filter(and_(LabResult.status == 'completed', LabResult.test_date >= start_date)).scalar() or 0.0
        critical = self.session.query(func.count(func.distinct(LabResultDetail.result_id))).join(LabResult)\
            .filter(and_(LabResultDetail.flagged == True, LabResult.status.in_(['pending', 'partial']))).scalar() or 0

        return {"pending": pending, "completed_today": completed_today, "revenue_month": float(revenue), "critical": critical}


    def get_advanced_stats(self, filter_type: str = "month") -> Dict[str, Any]:
        # --- 1. Gestion des dates ---
        now = datetime.now()
        if filter_type == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_type == "year":
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0)
        else:  # Default: month
            start_date = now.replace(day=1, hour=0, minute=0, second=0)

        # --- 2. Comptes de base (KPIs) ---
        # "En attente" = meme definition que get_stats_counts (inclut
        # 'analyzed') et reste sans filtre de periode : c'est un stock a
        # traiter, pas un flux.
        pending_statuses = ['pending', 'partial', 'analyzed']
        pending = (self.session.query(func.count(LabResult.result_id))
            .filter(LabResult.status.in_(pending_statuses)).scalar() or 0)

        completed = (self.session.query(func.count(LabResult.result_id))
            .filter(and_(LabResult.status == 'completed', LabResult.test_date >= start_date)).scalar() or 0)

        # Pathologiques = dossiers de la periode avec au moins un parametre
        # flagge, quel que soit leur statut (un resultat anormal valide reste
        # pertinent a suivre).
        critical = (self.session.query(func.count(func.distinct(LabResultDetail.result_id))).join(LabResult)
            .filter(and_(LabResultDetail.flagged == True, LabResult.test_date >= start_date)).scalar() or 0)

        # Activite totale = dossiers crees sur la periode (libelle UI :
        # "Dossiers crees"), sans melanger avec le stock "en attente".
        total_period = (self.session.query(func.count(LabResult.result_id))
            .filter(LabResult.test_date >= start_date).scalar() or 0)

        # --- 3. Top 7 Examens (Group By) ---
        top_exams_query = (self.session.query(Examen.nom, func.count(LabResult.result_id).label('total'))
            .join(LabResult, LabResult.examen_id == Examen.id)
            .filter(LabResult.test_date >= start_date)
            .group_by(Examen.nom)
            .order_by(desc('total'))
            .limit(7).all())
        
        top_exams = {name: count for name, count in top_exams_query}
        max_val = max(top_exams.values()) if top_exams else 1

        # --- 4. Les 3 derniers dossiers encore a traiter ---
        recent = (self.session.query(LabResult)
            .options(joinedload(LabResult.patient), joinedload(LabResult.examen))
            .filter(LabResult.status.in_(pending_statuses))
            .order_by(LabResult.test_date.desc())
            .limit(3).all())

        def _patient_name(r):
            # Meme forme partout : "Nom Prenom" ; un patient externe garde le nom declare a la reception.
            if r.patient:
                full = f"{r.patient.last_name or ''} {r.patient.first_name or ''}".strip()
                return full or "Patient Externe"
            info = r.external_patient_info or {}
            declared = info.get('nom_complet') or f"{info.get('nom') or info.get('name') or ''} {info.get('prenom') or info.get('first_name') or ''}"
            return declared.strip() or "Patient Externe"

        # --- 4b. Les 3 derniers PASSAGES encore a traiter : un patient une seule fois, avec tous ses examens ---
        candidates = (self.session.query(LabResult)
            .options(joinedload(LabResult.patient), joinedload(LabResult.examen))
            .filter(LabResult.status.in_(pending_statuses))
            .order_by(LabResult.test_date.desc(), LabResult.result_id.desc())
            .limit(60).all())
        passages: Dict[str, Dict[str, Any]] = {}
        for r in candidates:
            k = str(r.batch_id) if r.batch_id else str(r.result_id)
            if k not in passages:
                if len(passages) == 3:
                    continue
                passages[k] = {
                    "batch_id": str(r.batch_id) if r.batch_id else None,
                    "patient_name": _patient_name(r),
                    "code_patient": r.patient.code_patient if r.patient else "EXT",
                    "first_pending_id": r.result_id,
                    "_own": [],
                }
            passages[k]["_own"].append(r)
        siblings = self.get_batch_exams([p_r["_own"][0].batch_id for p_r in passages.values() if p_r["batch_id"]])
        recent_passages = []
        for p_r in passages.values():
            own = p_r.pop("_own")
            p_r["exams"] = siblings.get(p_r["batch_id"]) if p_r["batch_id"] else [
                {"result_id": o.result_id, "examen_nom": o.examen.nom if o.examen else (o.test_type or ""), "status": o.status} for o in own]
            recent_passages.append(p_r)

        return {
            "pending": pending,
            "completed_today": completed, # Adapté selon le filtre
            "critical": critical,
            "total_month": total_period,
            "top_exams": top_exams,
            "max_exam_count": max_val,
            "recent_pending": [
                {
                    "id": r.result_id,
                    "patient_name": _patient_name(r),
                    "code_patient": r.patient.code_patient if r.patient else "EXT",
                    "test_type": r.examen.nom if r.examen else (r.test_type or "")
                } for r in recent
            ],
            "recent_passages": recent_passages
        }

    def count_flagged_by_result(self, result_ids: List[int]) -> Dict[int, int]:
        """Nombre de parametres flagges par dossier, en une seule requete."""
        if not result_ids:
            return {}
        rows = (self.session.query(LabResultDetail.result_id, func.count(LabResultDetail.detail_id))
            .filter(and_(LabResultDetail.result_id.in_(result_ids), LabResultDetail.flagged == True))
            .group_by(LabResultDetail.result_id).all())
        return {rid: n for rid, n in rows}
    
    def delete_lab_result(self, result_id: int) -> bool:
        res = self.session.get(LabResult, result_id)
        if res:
            self.session.delete(res)
            self.session.commit()
            return True
        return False