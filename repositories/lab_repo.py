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
    LabResult, LabResultDetail
)
from models.prescription import Prescription
from models.patient import Patient

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
            self.session.delete(examen)
            self.session.commit()
            return True
        return False

    def list_all_examens(self) -> List[Examen]:
        return self.session.query(Examen).order_by(Examen.nom).all()

    def get_examen_by_id(self, examen_id: int) -> Optional[Examen]:
        return self.session.get(Examen, examen_id)

    # --- Paramètres ---
    def create_parametre(self, data: Dict[str, Any]) -> Parametre:
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
            .order_by(Parametre.id)\
            .all()
    
    def update_parametre(self, param_id: int, data: Dict[str, Any]) -> Optional[Parametre]:
        p = self.session.get(Parametre, param_id)
        if p:
            for k, v in data.items():
                setattr(p, k, v)
            self.session.commit()
            self.session.refresh(p)
            return p
        return None

    def delete_parametre(self, parametre_id: int) -> bool:
        p = self.session.get(Parametre, parametre_id)
        if p:
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

    def get_paginated_history(self, skip: int = 0, limit: int = 20, search_query: Optional[str] = None, status: Optional[str] = None) -> Tuple[int, List[LabResult]]:
        """
        Récupère l'historique des résultats de laboratoire avec pagination.
        Retourne le nombre total d'éléments (pour le front) et la liste de la page demandée.
        """
        query = self.session.query(LabResult)\
            .options(joinedload(LabResult.patient), joinedload(LabResult.examen))\
            .outerjoin(LabResult.patient)

        # 1. Filtre par recherche texte (si renseigné)
        if search_query:
            q_term = f"%{search_query.lower()}%"
            query = query.filter(
                or_(
                    LabResult.code_lab_patient.ilike(q_term),
                    LabResult.patient.has(Patient.last_name.ilike(q_term)),
                    LabResult.patient.has(Patient.first_name.ilike(q_term)),
                    cast(LabResult.external_patient_info['nom'], String).ilike(q_term),
                    cast(LabResult.external_patient_info['name'], String).ilike(q_term)
                )
            )

        # 2. Filtre par statut (ex: 'completed', 'pending')
        if status:
            query = query.filter(LabResult.status == status)

        # 3. Compter le total d'éléments correspondant aux filtres (AVANT la pagination)
        total_count = query.count()

        # 4. Appliquer le tri (le plus récent en premier) et la pagination (offset/limit)
        results = query.order_by(desc(LabResult.test_date))\
                       .offset(skip)\
                       .limit(limit)\
                       .all()

        return total_count, results

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
                params = self.list_parametres_for_examen(result.examen_id)
                
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

    def get_internal_with_active_prescription(self, search_term: str):
        """
        JOINTURE SQL UNIQUE : Lie Patient et Prescription.
        Optimisation : Filtre directement les prescriptions 'active' de type 'lab'.
        """
        term = f"%{search_term.lower()}%"
        
        return self.session.query(
            Patient, 
            Prescription
        ).join(
            Prescription, 
            Patient.patient_id == Prescription.patient_id
        ).filter(
            or_(
                func.lower(Patient.last_name).like(term),
                Patient.code_patient .ilike(term)
            ),
            Prescription.status == 'active',
            Prescription.is_lab_order == True
        ).all()

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

    def _interpret_single_detail(self, detail: LabResultDetail, age: int, sex: str):
        if detail.valeur_num is None: return
        ref = self.session.query(ReferenceRange).filter(
            ReferenceRange.parametre_id == detail.parametre_id,
            ReferenceRange.sexe.in_(['X', sex]),
            ReferenceRange.age_min <= age, ReferenceRange.age_max >= age
        ).first()

        if ref:
            if Decimal(str(ref.valeur_min)) <= detail.valeur_num <= Decimal(str(ref.valeur_max)):
                detail.interpretation, detail.flagged = "normal", False
            else:
                detail.interpretation, detail.flagged = "abnormal", True

    
    def save_results_values(self, result_id: int, values_map: Dict[int, Any], mark_completed: bool = False, global_note: Optional[str] = None) -> LabResult:
        try:
            result = self.session.query(LabResult)\
                .options(joinedload(LabResult.patient))\
                .filter(LabResult.result_id == result_id)\
                .first()

            if not result:
                raise ValueError(f"Dossier {result_id} introuvable.")

            # 🟢 NOUVEAU : Sauvegarde de l'interprétation globale
            if global_note is not None:
                result.note = global_note

            # --- Détermination du sexe du patient (Interne vs Externe) ---
            patient_sexe = "X" # Valeur par défaut
            if result.patient:
                # Patient interne : l'attribut du modèle est 'gender'
                patient_sexe = getattr(result.patient, 'gender', 'X') or 'X'
            elif result.external_patient_info:
                # Patient externe : on fouille dans le JSONB
                info = result.external_patient_info
                patient_sexe = info.get('sexe') or info.get('gender') or 'X'

            for raw_key, data in values_map.items():
                try:
                    d_id = int(raw_key)
                except (TypeError, ValueError):
                    continue

                # 🟢 NOUVEAU : Extraction depuis le dict normalisé par le controller
                val = data.get("valeur")
                manual_flag = data.get("flag")
                manual_interp = data.get("interpretation")

                if d_id < 0:
                    # Cle negative = "-parametre_id" : convention du client
                    # hors ligne (labGateway.js::getResultDetail) pour une
                    # ligne creee hors ligne, sans vrai detail_id connu. Un
                    # serial Postgres etant toujours positif, aucune
                    # ambiguite avec un detail_id : resolution directe par
                    # parametre_id, sans passer par la recherche detail_id.
                    detail = self.session.query(LabResultDetail).filter(
                        LabResultDetail.parametre_id == -d_id,
                        LabResultDetail.result_id == result_id
                    ).first()
                    if not detail:
                        continue
                else:
                    detail = self.session.query(LabResultDetail).filter(
                        LabResultDetail.detail_id == d_id,
                        LabResultDetail.result_id == result_id
                    ).first()

                if not detail:
                    # 🟢 NOUVEAU (chantier 4 sous-projet 5) : dossier cree
                    # hors ligne - le client ne connait jamais le detail_id
                    # genere par le serveur a la creation, seulement le
                    # parametre_id du catalogue (Approche A de la spec).
                    detail = self.session.query(LabResultDetail).filter(
                        LabResultDetail.parametre_id == d_id,
                        LabResultDetail.result_id == result_id
                    ).first()

                if not detail:
                    # Valeur orpheline (parametre retire du catalogue
                    # entre-temps) : on ignore plutot que de faire echouer
                    # tout le dossier.
                    continue

                param = detail.parametre
                if param.input_type == 'numeric':
                    try:
                        detail.valeur_num = Decimal(str(val)) if val is not None else None
                        detail.valeur_text = str(val) if val is not None else ""
                        
                        # 🟢 MODIFIÉ : Priorité au manuel, sinon Auto-interprétation
                        if manual_flag or manual_interp:
                            # Si le tech a forcé un flag (H, L, A)
                            detail.flagged = bool(manual_flag and manual_flag not in ['N', '']) 
                            detail.interpretation = manual_interp or ""
                        elif detail.valeur_num is not None:
                            # --- AUTO-INTERPRÉTATION EXISTANTE ---
                            norme = next((r for r in param.reference_ranges if r.sexe == patient_sexe), None)
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
                    except:
                        detail.valeur_num = None 
                else:
                    detail.valeur_text = str(val) if val is not None else ""
                    detail.valeur_num = None
                    # 🟢 NOUVEAU : On permet aussi de flagger manuellement du texte
                    if manual_flag or manual_interp:
                        detail.flagged = bool(manual_flag and manual_flag not in ['N', ''])
                        detail.interpretation = manual_interp or ""
                    else:
                        detail.flagged = False

            if mark_completed:
                result.status = "completed"
                result.test_date = func.now() 
            else:
                result.status = "partial" 

            self.session.commit()
            self.session.refresh(result)
            return result

        except Exception as e:
            self.session.rollback()
            raise e

    def _get_patient_bio_info(self, result: LabResult) -> Tuple[int, str]:
        """Calcule l'âge réel et récupère le sexe de manière sécurisée."""
        # 1. Cas Patient Interne (Hôpital)
        if result.patient:
            sexe = getattr(result.patient, 'sexe', 'X') or 'X' # Sécurité si None
            age = 0
            if result.patient.birth_date:
                today = date.today()
                dob = result.patient.birth_date
                # Calcul précis de l'âge
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return age, sexe

        # 2. Cas Patient Externe (JSON)
        if result.external_patient_info:
            info = result.external_patient_info
            # Sécurité : cast en int avec fallback
            try:
                age = int(info.get('age', 0))
            except (ValueError, TypeError):
                age = 0
            return age, info.get('sexe', 'X')

        # 3. Fallback
        return 0, 'X'
    
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
        pending = self.session.query(func.count(LabResult.result_id))\
            .filter(LabResult.status.in_(['pending', 'partial'])).scalar() or 0
        
        completed = self.session.query(func.count(LabResult.result_id))\
            .filter(and_(LabResult.status == 'completed', LabResult.test_date >= start_date)).scalar() or 0

        critical = self.session.query(func.count(func.distinct(LabResultDetail.result_id))).join(LabResult)\
            .filter(and_(LabResultDetail.flagged == True, LabResult.status != 'completed')).scalar() or 0

        # --- 3. Top 7 Examens (Group By) ---
        top_exams_query = (self.session.query(Examen.nom, func.count(LabResult.result_id).label('total'))
            .join(LabResult, LabResult.examen_id == Examen.id)
            .filter(LabResult.test_date >= start_date)
            .group_by(Examen.nom)
            .order_by(desc('total'))
            .limit(7).all())
        
        top_exams = {name: count for name, count in top_exams_query}
        max_val = max(top_exams.values()) if top_exams else 1

        # --- 4. Les 3 derniers prélèvements (La liste manquante) ---
        recent = (self.session.query(LabResult)
            .order_by(LabResult.test_date.desc())
            .limit(3).all())

        return {
            "pending": pending,
            "completed_today": completed, # Adapté selon le filtre
            "critical": critical,
            "total_month": completed + pending, # Activité totale sur la période
            "top_exams": top_exams,
            "max_exam_count": max_val,
            "recent_pending": [
                {
                    "id": r.result_id,
                    "patient_name": r.patient.last_name if r.patient else "Patient Externe",
                    "code_patient": r.patient.code_patient if r.patient else "EXT",
                    "test_type": r.examen.nom
                } for r in recent
            ]
        }
    
    def delete_lab_result(self, result_id: int) -> bool:
        res = self.session.get(LabResult, result_id)
        if res:
            self.session.delete(res)
            self.session.commit()
            return True
        return False