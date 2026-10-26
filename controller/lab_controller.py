# controller/lab_controller.py

import logging
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, date

from flask_login import current_user
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

# --- IMPORTS MODÈLES & REPO ---
# Vérifie tes chemins d'import
from models.lab import Examen, Parametre, LabResult, ReferenceRange
from models.user import User
from repositories.lab_repo import LabRepository, LabResultLockedError, LabResultNotValidatedError
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
from api_backend.backend_app.utils.patient_resolution import resolve_patient_id
from utils.lab_reference import SEX_LABELS_FR, ABNORMAL_FALLBACK, select_range, normalize_sex

class LabController:
    def __init__(self, repo: LabRepository, current_user=None):
        self.repo = repo
        self.user = current_user
        self.logger = logging.getLogger(__name__)

    def _est_medical_lecture_seule(self) -> bool:
        """medecin/nurse : lecture seule, uniquement les examens
        'completed' - decision utilisateur 2026-09-22 (chantier perimetre
        medical). laborantin/admin/ToxicoManager ne sont jamais concernes."""
        roles = set(getattr(self.user, "roles", []) or [])
        return bool(roles & {"medecin", "nurse"})

    # ====================================================================
    # 🛠️ HELPERS PRIVÉS (Formatage)
    # ====================================================================

    def _format_patient_name(self, result: LabResult) -> str:
        """Formate le nom (Patient Interne ou Externe)."""
        if result.patient:
            return f"{result.patient.last_name} {result.patient.first_name}"
        
        if result.external_patient_info:
            info = result.external_patient_info
            # On essaie plusieurs clés possibles pour la robustesse
            nom = info.get('nom') or info.get('name') or 'Inconnu'
            prenom = info.get('prenom') or info.get('first_name') or ''
            return f"{nom} {prenom} (Ext.)".strip()
            
        return "Patient Inconnu"

    def _serialize_examen(self, ex: Examen) -> Dict:
        """Convertit l'objet Examen en Dictionnaire API."""
        return {
            "id": ex.id,
            "code": ex.code,
            "nom": ex.nom,
            "categorie": ex.categorie,
            "prix": float(ex.prix) if ex.prix is not None else 0.0,
            # Compte le nombre de paramètres associés (utile pour la liste)
            "nb_params": len(ex.parametres) if ex.parametres else 0
        }
    
    def _calculate_age(self, dob: Optional[date]) -> int:
        """Calcule l'âge précis à partir de la date de naissance."""
        if not dob:
            return 0
        today = date.today()
        # Soustrait 1 si l'anniversaire n'est pas encore passé cette année
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    
    def _format_patient_info(self, r: LabResult) -> Dict:
        """
        Transforme les données brutes (ORM ou JSON) en dictionnaire propre pour le Frontend.
        Gère la différence entre Patient Interne (SQL) et Externe (JSON).
        """
        # --- CAS 1 : PATIENT INTERNE (Table SQL) ---
        if r.patient:
            # On récupère les attributs de l'objet Patient (déjà chargé par joinedload)
            nom_complet = f"{r.patient.last_name} {r.patient.first_name}"
            
            # ATTENTION : Adaptez 'gender' ou 'sexe' selon votre modèle Patient exact
            sexe = getattr(r.patient, 'gender', None) or getattr(r.patient, 'sexe', 'X')
            
            # Calcul de l'âge
            age = self._calculate_age(r.patient.birth_date)
            
            return {
                "nom": nom_complet,
                "sexe": sexe,
                "age": age,
                "is_external": False
            }

        # --- CAS 2 : PATIENT EXTERNE (JSONB) ---
        elif r.external_patient_info:
            info = r.external_patient_info
            # Fallback sur différents noms de clés possibles
            nom = info.get('nom_complet') or f"{info.get('nom', '')} {info.get('prenom', '')}"
            sexe = info.get('sexe') or info.get('gender') or 'X'
            age = info.get('age', 0)
            
            return {
                "nom": nom.strip(),
                "sexe": sexe,
                "age": age,
                "is_external": True
            }

        # --- CAS 3 : ERREUR / ORPHELIN ---
        return {"nom": "Inconnu", "sexe": "?", "age": "?", "is_external": True}
    
    # ====================================================================
    # 1. WORKLIST (PONT MÉDICAL) - [NOUVEAU]
    # ====================================================================
    def get_worklist(self) -> List[Dict]:
        """Récupère les prescriptions en attente."""
        return self.repo.get_lab_worklist()

    # ====================================================================
    # ⚙️ CONFIGURATION (Examens, Paramètres, Valeurs Réf)
    # ====================================================================

    def list_examens(self) -> List[Dict]:
        """Liste tous les examens configurés."""
        examens = self.repo.list_all_examens()
        return [self._serialize_examen(ex) for ex in examens]

    def _audit_exam(self, action: str, examen_id: int, old: Dict[str, Any], new: Dict[str, Any]):
        """Trace les changements du catalogue (surtout les prix). Ne bloque jamais l'operation."""
        if self.user is None:
            return
        try:
            from repositories.audit_repo import AuditRepository
            audit = AuditRepository(self.repo.session)
            old = {k: (float(v) if k == "prix" and v is not None else v) for k, v in old.items()}
            new = {k: (float(v) if k == "prix" and v is not None else v) for k, v in new.items()}
            audit.log_user_action(current_user=self.user, resource_type="Examen", action_performed=action,
                                  resource_id=examen_id, old_values=old or None, new_values=new or None,
                                  details=audit.summarize_changes(old, new) or None)
            self.repo.session.commit()
        except Exception:
            self.logger.exception("Échec de l'écriture d'audit (Examen)")
            try:
                self.repo.session.rollback()
            except Exception:
                pass

    def create_examen(self, data: Dict[str, Any]) -> Dict:
        """Crée un nouvel examen."""
        ex = self.repo.create_examen(data)
        self._audit_exam("CREATE", ex.id, {}, {"code": ex.code, "nom": ex.nom, "categorie": ex.categorie, "prix": ex.prix})
        return self._serialize_examen(ex)

    def update_examen(self, examen_id: int, data: Dict[str, Any]) -> Optional[Dict]:
        """Met à jour un examen."""
        clean_data = {k: v for k, v in data.items() if v is not None}
        current = self.repo.get_examen_by_id(examen_id)
        before = {k: getattr(current, k) for k in clean_data} if current else {}
        ex = self.repo.update_examen(examen_id, clean_data)
        if ex:
            after = {k: getattr(ex, k) for k in clean_data}
            changed = {k for k in clean_data if str(before.get(k)) != str(after.get(k)) and
                       not (k == "prix" and float(before.get(k) or 0) == float(after.get(k) or 0))}
            if changed:
                self._audit_exam("UPDATE", examen_id, {k: before[k] for k in changed}, {k: after[k] for k in changed})
        return self._serialize_examen(ex) if ex else None

    def delete_examen(self, examen_id: int) -> bool:
        """Supprime un examen."""
        current = self.repo.get_examen_by_id(examen_id)
        before = {"code": current.code, "nom": current.nom, "prix": current.prix} if current else {}
        ok = self.repo.delete_examen(examen_id)
        if ok:
            self._audit_exam("DELETE", examen_id, before, {})
        return ok

    # --- Gestion des Paramètres (Leucocytes, Hématies...) ---

    _PARAM_FIELDS = ('nom_parametre', 'unite', 'type_valeur', 'input_type', 'options_list')

    def update_parametre(self, param_id: int, data: Dict[str, Any]) -> Optional[Dict]:
        """Modifie nom, unite, type ou liste d'options d'un parametre (jamais son examen)."""
        clean = {k: v for k, v in data.items() if k in self._PARAM_FIELDS and v is not None}
        p = self.repo.update_parametre(param_id, clean)
        return {"id": p.id, "nom": p.nom_parametre, "unite": p.unite} if p else None

    def add_parametre(self, examen_id: int, data: Dict[str, Any]) -> Dict:
        """Ajoute un paramètre à un examen existant."""
        data = {k: v for k, v in data.items() if k in self._PARAM_FIELDS}
        data.setdefault('unite', '')
        data.setdefault('type_valeur', 'numeric')
        data['examen_id'] = examen_id
        p = self.repo.create_parametre(data)
        return {"id": p.id, "nom": p.nom_parametre, "unite": p.unite}

    @staticmethod
    def _detail_sort_key(d):
        """Ordre d'affichage du catalogue (parametres.ordre), jamais l'ordre physique des lignes."""
        p = d.parametre
        return ((p.ordre if p is not None else 0) or 0, d.parametre_id or 0, d.detail_id or 0)

    def reorder_parametres(self, examen_id: int, ids: List[int]) -> bool:
        return self.repo.reorder_parametres(examen_id, ids)

    def list_parametres(self, examen_id: int) -> List[Dict]:
        """
        Version Robuste : Garantit que chaque champ nécessaire au rendu UI est présent.
        """
        params = self.repo.list_parametres_for_examen(examen_id)
        result = []
        
        for p in params:
            # On s'assure que input_type a une valeur par défaut pour l'UI
            it = p.input_type if p.input_type else "numeric"
            
            result.append({
                "id": p.id,
                "ordre": p.ordre,
                "nom": p.nom_parametre,
                "unite": p.unite or "",
                "type": p.type_valeur,       # Logique métier
                "input_type": it,            # Logique UI (text, numeric, select)
                "options": p.options_list,    # Liste si select
                # Ajout de colonnes d'info pour la sélection
                "info_affichage": f"{p.nom_parametre} ({p.unite})" if p.unite else p.nom_parametre,
                "ranges": [
                    {
                        "id": r.id, 
                        "sexe": r.sexe, 
                        "age_min": r.age_min,
                        "age_max": r.age_max,
                        "min": float(r.valeur_min) if r.valeur_min else None, 
                        "max": float(r.valeur_max) if r.valeur_max else None
                    } for r in p.reference_ranges
                ]
            })
        return result

    def delete_parametre(self, param_id: int) -> bool:
        """Supprime un parametre et ses plages. ValueError si des resultats l'utilisent deja
        (l'historique des dossiers doit rester lisible)."""
        if self.repo.parametre_has_results(param_id):
            raise ValueError("Ce parametre est deja utilise dans des resultats : il ne peut pas etre supprime.")
        return self.repo.delete_parametre(param_id)

    # --- Gestion des Valeurs de Référence (H/F/Enfant) ---

    def add_reference_range(self, param_id: int, data: Dict[str, Any]) -> Dict:
        data['parametre_id'] = param_id
        rr = self.repo.create_reference_range(data)
        return {"id": rr.id, "sexe": rr.sexe, "min": rr.valeur_min, "max": rr.valeur_max}

    def delete_reference_range(self, range_id: int) -> bool:
        return self.repo.delete_reference_range(range_id)

    # ====================================================================
    # 🔬 GESTION DES RÉSULTATS (Création, Lecture, Saisie)
    # ====================================================================

    def get_paginated_results(self, page: int = 1, limit: int = 20, search: Optional[str] = None, status: Optional[str] = None,
                              abnormal_only: bool = False, period: Optional[str] = None,
                              group_by_batch: bool = False) -> Dict[str, Any]:
        """
        Récupère l'historique paginé et formaté pour le frontend.
        """
        if self._est_medical_lecture_seule():
            # Le parametre appelant est ignore pour ce role, jamais fusionne -
            # sinon un appel direct avec ?status=pending contournerait le
            # filtre malgre l'ecran qui ne l'exposerait jamais.
            status = "completed"

        # Sécurité : on évite les pages négatives ou zéro
        if page < 1:
            page = 1
        if limit < 1: 
            limit = 20
            
        # Calcul de l'offset (ex: page 2 avec limit 20 -> skip 20)
        skip = (page - 1) * limit
        
        # 1. Appel au Repository
        total_count, results = self.repo.get_paginated_history(
            skip=skip, 
            limit=limit, 
            search_query=search, 
            status=status,
            abnormal_only=abnormal_only,
            period=period,
            group_by_batch=group_by_batch
        )
        
        # Anomalies par examen, en une requete : visibles des la liste (un resultat anormal ne doit pas etre manque).
        flagged_counts = self.repo.count_flagged_by_result([r.result_id for r in results])

        # 2. Formatage des résultats (réutilisation de ta logique existante)
        formatted_items = []
        for r in results:
            p_infos = self._format_patient_info(r)
            formatted_items.append({
                'result_id': r.result_id,
                'code': r.code_lab_patient,
                'patient_name': p_infos['nom'],
                'patient_sexe': p_infos['sexe'],
                'patient_age': p_infos['age'],
                'is_external': p_infos['is_external'],
                'examen_nom': r.examen.nom if r.examen else 'Inconnu',
                'test_date': r.test_date.isoformat() if r.test_date else "",
                'status': r.status,
                'batch_id': str(r.batch_id) if r.batch_id else None,
                'nb_anormaux': flagged_counts.get(r.result_id, 0),
                'corrected': bool(r.corrected),
            })
            
        # 3. Calcul du nombre total de pages (arrondi au supérieur)
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

        # 4. On retourne l'enveloppe complète pour le frontend
        return {
            "total_items": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "limit": limit,
            "items": formatted_items
        }

    def get_print_data(self, result_id: int, config_ctrl: Any) -> Dict[str, Any]:
        """
        Prépare les données d'impression. 
        Affiche [min - max] pour le numérique, et "-" pour le texte.
        """
        # 1. Récupération complète (avec joinedload)
        r = self.repo.get_full_lab_result(result_id)
        if not r:
            return None

        if self._est_medical_lecture_seule() and r.status != "completed":
            raise PermissionError(
                "Ce resultat n'est pas encore complet - reserve au laboratoire."
            )

        # Resolution nom/logo centralisee (chantier exports, 2026-09-23) -
        # voir api_backend/backend_app/utils/pdf_header.py pour le detail.
        header_ctx = get_pdf_header_context(config_ctrl)

        # 2. Age et sexe : le code sexe (M/F/X) choisit la plage, le libelle francais est affiche
        age_connu, sexe_code = self.repo._patient_bio(r)
        age_patient = age_connu if age_connu is not None else 0

        if r.patient:
            patient_name = f"{r.patient.last_name} {r.patient.first_name}"
        else:
            patient_name = r.external_patient_info.get('nom', 'Inconnu') if r.external_patient_info else 'Inconnu'

        patient_info = {
            "nom": patient_name,
            "age": age_patient,
            "sexe": SEX_LABELS_FR.get(sexe_code, SEX_LABELS_FR["X"]),
        }

        # 3. Traitement des résultats et des normes
        details_format_list = []

        for d in sorted(r.details, key=self._detail_sort_key):
            if not d.parametre:
                continue

            p = d.parametre

            # Norme du sexe du patient (a defaut la norme generique) ; jamais celle de l'autre sexe.
            norme_affichage = "-"
            if p.input_type == 'numeric':
                norme_trouvee = select_range(p.reference_ranges, sexe_code, age_connu)
                if norme_trouvee and norme_trouvee.valeur_min is not None and norme_trouvee.valeur_max is not None:
                    # Sans zeros inutiles : 12.00 -> 12, 15.50 -> 15.5
                    min_val = format(round(float(norme_trouvee.valeur_min), 2), 'g')
                    max_val = format(round(float(norme_trouvee.valeur_max), 2), 'g')
                    norme_affichage = f"[{min_val} - {max_val}]"

            # Extraction de la valeur du résultat saisie
            if p.input_type == 'numeric' and d.valeur_num is not None:
                valeur_resultat = str(round(d.valeur_num, 2))
            else:
                valeur_resultat = d.valeur_text or ""

            details_format_list.append({
                "parametre_nom": p.nom_parametre,
                "valeur": valeur_resultat,
                "unite": p.unite or "",
                "reference_str": norme_affichage,
                "is_abnormal": d.flagged,
                # Un resultat anormal porte toujours un mot (Haut / Bas / Anormal), jamais « * * ».
                "interpretation": d.interpretation or (ABNORMAL_FALLBACK if d.flagged else ""),
            })

        # 4. Assemblage final
        return {
            **header_ctx,
            "patient": patient_info,
            "examen": {
                "nom": r.examen.nom if r.examen else "Analyse",
                "code": r.code_lab_patient, # Utilisé pour le titre
            },
            "result_info": {
                "date_test": r.test_date.strftime("%d/%m/%Y %H:%M") if r.test_date else "",
                "status": r.status or "Complété",
                "prescripteur": r.prescribed_by_name or "-",
                "note": r.note # Utilisé pour la conclusion en bas
            },
            "details": details_format_list,
            "date_impression": datetime.now().strftime("%d/%m/%Y à %H:%M")
        }

    DONE_STATUSES = ("completed", "validated")

    def get_batch_print_data(self, batch_id_str: str, config_ctrl: Any) -> Optional[Dict[str, Any]]:
        """
        Donnees du PDF « dossier complet » d'un passage patient : le patient et l'en-tete une seule fois,
        puis chaque examen TERMINE avec ses resultats. Les examens encore en cours sont comptes (skipped_count)
        mais ne sont jamais imprimes.
        Retourne None si le lot n'existe pas ; leve ValueError si aucun examen n'est termine.
        """
        try:
            batch_uuid = uuid.UUID(batch_id_str)
        except ValueError:
            return None
        rows = self.repo.get_results_by_batch_id(batch_uuid)
        if not rows:
            return None

        # Medecin/infirmier : lecture seule, uniquement les examens 'completed' (meme regle que le PDF d'un examen).
        accepted = ("completed",) if self._est_medical_lecture_seule() else self.DONE_STATUSES
        done = sorted((r for r in rows if r.status in accepted), key=lambda r: r.result_id)
        if not done:
            raise ValueError("Aucun examen termine dans ce dossier.")

        # Reutilise la mise en forme d'un examen (normes, anomalies, droits) : aucune logique dupliquee.
        per_exam = [self.get_print_data(r.result_id, config_ctrl) for r in done]
        first = per_exam[0]
        return {
            **{k: v for k, v in first.items() if k not in ("examen", "result_info", "details")},
            "passage": {
                "code": first["examen"]["code"],
                "date_test": first["result_info"]["date_test"],
                "prescripteur": first["result_info"]["prescripteur"],
            },
            "exams": [
                {
                    "nom": d["examen"]["nom"],
                    "code": d["examen"]["code"],
                    "details": d["details"],
                    "note": d["result_info"]["note"],
                }
                for d in per_exam
            ],
            "skipped_count": len(rows) - len(done),
        }

    def create_result(self, 
                    examen_id: int, 
                    patient_id: Optional[int] = None, 
                    external_patient_info: Optional[dict] = None,
                    origin_prescription_id: Optional[int] = None,
                    code_lab_patient: Optional[str] = None) -> Dict:
        
        user_id = getattr(self.user, "user_id", None)
        username = getattr(self.user, "username", "System")
        
        ex_obj = self.repo.get_examen_by_id(examen_id)
        if not ex_obj:
            raise ValueError(f"Examen {examen_id} introuvable")

        # On prépare juste l'enveloppe, le REPO créera les détails vides
        payload = {
            "examen_id": examen_id,
            "test_type": ex_obj.categorie, 
            "test_date": datetime.now(),
            "prescribed_by": user_id,
            "technician_id": user_id,
            "technician_name": username,
            "patient_id": patient_id,
            "external_patient_info": external_patient_info,
            "origin_prescription_id": origin_prescription_id,
            "code_lab_patient": code_lab_patient,
            "status": "pending"
        }
        
        lr = self.repo.create_lab_result(payload)
        
        return {
            "result_id": lr.result_id, 
            "code": lr.code_lab_patient, 
            "status": lr.status
        }

    def get_result_detail(self, result_id: int) -> Optional[Dict]:
        """Récupère le dossier complet pour affichage/saisie."""
        r = self.repo.get_full_lab_result(result_id)
        if not r: return None

        if self._est_medical_lecture_seule() and r.status != "completed":
            raise PermissionError(
                "Ce resultat n'est pas encore complet - reserve au laboratoire."
            )

        details_out = []
        # Ordre de definition des parametres (jamais l'ordre physique des lignes, qui change apres une mise a jour).
        for d in sorted(r.details, key=self._detail_sort_key):
            if not d.parametre: continue 
            p = d.parametre
            details_out.append({
                "detail_id": d.detail_id,
                "parametre_id": d.parametre_id,
                "nom": p.nom_parametre,
                "unite": p.unite,
                "input_type": p.input_type or "numeric",
                "options": p.options_list,
                "valeur": d.valeur_num if p.input_type == 'numeric' else d.valeur_text,
                "interpretation": d.interpretation,
                "is_abnormal": d.flagged,
                "ranges": [{"sexe": rr.sexe, "min": float(rr.valeur_min), "max": float(rr.valeur_max)} 
                          for rr in p.reference_ranges]
            })

        # --- IMPORTANT : On renvoie result_id ET id pour le frontend ---
        return {
            "result_id": r.result_id, 
            "id": r.result_id,
            "code": r.code_lab_patient,
            "status": r.status,
            "note": r.note,
            "test_date": r.test_date.isoformat() if r.test_date else None,
            "medecin_prescripteur": r.prescribed_by_name or None,
            "patient_info": self._format_patient_info(r),
            "examen_nom": r.examen.nom if r.examen else "Inconnu",
            "details": details_out,
            "corrected": bool(r.corrected),
            "corrected_at": r.corrected_at.isoformat() if r.corrected_at else None,
            "amendments": [{
                "amendment_id": a.amendment_id,
                "amended_at": a.amended_at.isoformat() if a.amended_at else None,
                "amended_by_name": a.amended_by_name,
                "reason": a.reason,
                "previous_note": a.previous_note,
                "previous_values": a.previous_values or [],
            } for a in self.repo.list_amendments(r.result_id)],
        }
    
    # ====================================================================
    # 🧪 PAILLASSE (LISTE TECHNIQUE)
    # ====================================================================
    def get_paillasse_list(self) -> List[Dict]:
        """Récupère les dossiers en attente avec toutes les infos formatées."""
        
        # Récupère les résultats depuis le Repo (avec joinedload !)
        results = self.repo.get_active_worklist() 
        
        # Examens de chaque passage patient (termines compris), pour regrouper l'affichage :
        # la liste reste "un dossier a saisir par ligne", chaque ligne connait juste ses voisins.
        batch_exams = self.repo.get_batch_exams(sorted({r.batch_id for r in results if r.batch_id}, key=str))

        output = []
        for r in results:
            # On utilise le helper pour extraire proprement les infos patient
            p_infos = self._format_patient_info(r)
            
            output.append({
                'result_id': r.result_id,  # L'ID technique du dossier
                'batch_id': str(r.batch_id) if r.batch_id else None,
                'batch_exams': batch_exams.get(str(r.batch_id)) if r.batch_id else [
                    {'result_id': r.result_id, 'examen_nom': r.examen.nom if r.examen else 'Inconnu', 'status': r.status}],
                'code': r.code_lab_patient, # Le code barre (ex: LAB-0212-0084)
                
                # --- INFOS PATIENT APLATIES (Pour l'affichage direct dans le tableau VueJS) ---
                'patient_name': p_infos['nom'],
                'patient_sexe': p_infos['sexe'],
                'patient_age': p_infos['age'],
                'is_external': p_infos['is_external'],
                # -----------------------------------------------------------------------------
                
                'examen_nom': r.examen.nom if r.examen else 'Inconnu',
                'test_date': r.test_date.strftime("%d/%m/%Y %H:%M") if r.test_date else "",
                'status': r.status
            })
            
        return output
    
    

    # 🟢 MODIFIÉ: Ajout du paramètre global_note
    def submit_values(self, result_id: int, values_map: Dict[int, Any], mark_completed: bool, global_note: Optional[str] = None) -> Dict:
        """
        Sauvegarde les valeurs saisies par le technicien.
        Accepte soit { detail_id: valeur }, soit { detail_id: {"valeur": X, "flag": Y, "interpretation": Z} }
        """
        try:
            clean_values = {}
            for k, v in values_map.items():
                # Si le front envoie le nouvel objet complet
                if isinstance(v, dict):
                    val = v.get("valeur")
                    clean_values[k] = {
                        "valeur": None if val == "" else val,
                        "flag": v.get("flag"),
                        "interpretation": v.get("interpretation")
                    }
                # Si un ancien code envoie juste la valeur brute (Rétrocompatibilité)
                else:
                    clean_values[k] = {
                        "valeur": None if v == "" else v,
                        "flag": None,
                        "interpretation": None
                    }
            
            # 🟢 MODIFIÉ: On passe global_note au repo
            updated = self.repo.save_results_values(result_id, clean_values, mark_completed, global_note)
            
            return {
                "id": updated.result_id, 
                "status": updated.status, 
                "message": "Résultats sauvegardés."
            }
        except LabResultLockedError as e:
            # Resultat valide : lecture seule. 409 = refus definitif (le connecteur hors ligne
            # met l'operation en quarantaine au lieu de la rejouer).
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            self.logger.error(f"Erreur submit values {result_id}: {e}")
            raise e

    def _clean_values(self, values_map: Dict[Any, Any]) -> Dict[Any, Dict[str, Any]]:
        clean: Dict[Any, Dict[str, Any]] = {}
        for k, v in (values_map or {}).items():
            if isinstance(v, dict):
                val = v.get("valeur")
                clean[k] = {"valeur": None if val == "" else val, "flag": v.get("flag"), "interpretation": v.get("interpretation")}
            else:
                clean[k] = {"valeur": None if v == "" else v, "flag": None, "interpretation": None}
        return clean

    def amend_values(self, result_id: int, values_map: Dict[Any, Any], global_note: Optional[str], reason: str) -> Dict:
        """Correction explicite d'un resultat valide (motif obligatoire) - voir LabRepository.amend_result."""
        if not (reason or "").strip():
            raise HTTPException(status_code=422, detail="Le motif de la correction est obligatoire.")
        try:
            updated = self.repo.amend_result(
                result_id, self._clean_values(values_map), global_note, reason,
                user_id=getattr(self.user, "user_id", None),
                user_name=getattr(self.user, "full_name", None) or getattr(self.user, "username", None))
        except LabResultNotValidatedError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return {"id": updated.result_id, "status": updated.status, "corrected": bool(updated.corrected),
                "message": "Résultat corrigé."}

    def delete_result(self, result_id: int) -> bool:
        """Supprime définitivement un résultat (Admin/Erreur)."""
        return self.repo.delete_lab_result(result_id)

    # ====================================================================
    # 🚀 BATCH, RECHERCHE & STATS (Fonctions transverses)
    # ====================================================================

    def create_batch_results(self, payload: Dict[str, Any], current_user) -> Dict:
        patient_id = payload.get('patient_id')
        patient_uuid = payload.get('patient_uuid')
        external_info = payload.get('external_patient_info')
        results_list = payload.get('results', [])
        prescribed_by_id = payload.get('prescribed_by_id')
        prescribed_by_name = payload.get('prescribed_by_name')
        origin_prescription_id = payload.get('origin_prescription_id')
        batch_uuid = payload.get('batch_uuid')

        resolved_patient_id = None
        if patient_id or patient_uuid:
            resolved_patient_id = resolve_patient_id(self.repo.session, patient_id, patient_uuid)

        # Un autre item de ce meme lot (batch_uuid) a-t-il deja ete cree
        # (envoye dans une operation CRUD anterieure) ? Si oui, on reutilise
        # son code LAB et son groupement Postgres (batch_id) au lieu d'en
        # generer de nouveaux - remplace la logique "le premier de la
        # boucle genere, les suivants reutilisent" qui supposait un seul
        # appel HTTP synchrone (invalide hors ligne, chaque item part dans
        # sa propre operation).
        existing_sibling = self.repo.get_lab_result_by_batch_uuid(batch_uuid) if batch_uuid else None
        server_batch_id = existing_sibling.batch_id if existing_sibling else uuid.uuid4()
        shared_code = existing_sibling.code_lab_patient if existing_sibling else None

        self._refuse_duplicate_lines(results_list, origin_prescription_id=origin_prescription_id)

        success_count = 0
        for item in results_list:
            item_uuid = item.get('uuid')
            if item_uuid:
                already = self.repo.get_lab_result_by_uuid(item_uuid)
                if already:
                    # Rejeu d'un item deja accepte - idempotent, ne duplique pas.
                    success_count += 1
                    if not shared_code:
                        shared_code = already.code_lab_patient
                    continue

            payload_item = {
                "uuid": item_uuid,
                "batch_uuid": batch_uuid,
                "examen_id": item.get('examen_id'),
                "patient_id": resolved_patient_id,
                "external_patient_info": external_info,
                "batch_id": server_batch_id,
                "code_lab_patient": shared_code,
                "prescribed_by": prescribed_by_id,
                "prescribed_by_name": prescribed_by_name,
                "origin_prescription_id": origin_prescription_id,
                "origin_caisse_item_id": item.get('origin_caisse_item_id'),
                "technician_id": current_user.user_id,
                "technician_name": current_user.full_name,
                "created_by": current_user.user_id,
                "created_by_name": current_user.full_name,
            }
            try:
                new_res = self.repo.create_lab_result(payload_item)
            except IntegrityError:
                # Examen supprime du catalogue (FK) ou reference invalide :
                # erreur definitive, jamais transitoire - un 422 (et non un
                # 500) pour que le connecteur PowerSync mette l'operation en
                # quarantaine au lieu de la rejouer indefiniment. Rollback
                # explicite : la session est inutilisable apres un INSERT
                # echoue.
                self.repo.session.rollback()
                raise HTTPException(
                    status_code=422,
                    detail=f"Examen ou reference invalide pour l'item {item.get('examen_id')}",
                )
            if not shared_code:
                shared_code = new_res.code_lab_patient
            success_count += 1

        return {"success": True, "count": success_count, "shared_code": shared_code, "batch_id": str(server_batch_id)}

    def _refuse_duplicate_lines(self, results_list: List[Dict[str, Any]],
                                origin_prescription_id: Optional[int]) -> None:
        """Une ligne d'ordonnance (ordonnance + examen) ou de facture ne se recoit qu'une fois.
        Verifie TOUT le lot avant de creer quoi que ce soit : un doublon refuse le lot entier (409).
        Un item deja cree sous le meme uuid (rejeu du connecteur) est ignore ici : idempotent."""
        seen_items, seen_exams = set(), set()
        for item in results_list:
            item_uuid = item.get('uuid')
            if item_uuid and self.repo.get_lab_result_by_uuid(item_uuid):
                continue
            item_id = item.get('origin_caisse_item_id')
            if item_id:
                caisse_item = self.repo.get_caisse_item(item_id)
                if not caisse_item or caisse_item.item_ref_id != item.get('examen_id'):
                    raise HTTPException(status_code=422, detail="Ligne de facture invalide pour cet examen.")
                if item_id in seen_items or self.repo.lab_result_exists_for_caisse_item(item_id):
                    raise HTTPException(status_code=409, detail="Cette ligne de facture a deja ete recue au laboratoire.")
                seen_items.add(item_id)
            if origin_prescription_id:
                key = (origin_prescription_id, item.get('examen_id'))
                if key in seen_exams or self.repo.lab_result_exists_for_prescription_exam(*key):
                    raise HTTPException(status_code=409, detail="Cet examen de l'ordonnance a deja ete recu au laboratoire.")
                seen_exams.add(key)

    def search_lab_files(self, query: str) -> List[Dict]:
        """Recherche globale avec regroupement intelligent par Batch ID."""
        if not query or len(query) < 2:
            return []
        
        # 1. Recherche standard (ce que tu faisais déjà)
        initial_results = self.repo.search_results_unified(query)
        
        # 2. L'EFFET AIMANT (Le chainon manquant)
        # On collecte les IDs de lots trouvés
        batch_ids_found = {r.batch_id for r in initial_results if r.batch_id is not None}
        
        final_list = initial_results
        
        # Si on a trouvé des éléments faisant partie de groupes
        if batch_ids_found:
            # On va chercher les "frères et sœurs" cachés
            siblings = self.repo.get_results_by_batch_ids(list(batch_ids_found))
            
            # 3. FUSION INTELLIGENTE (Dédoublonnage)
            # On utilise un dictionnaire {id: objet} pour écraser les doublons
            # (Car search_results_unified et get_results_by_batch_ids peuvent retourner le même objet)
            merged_results = {r.result_id: r for r in initial_results}
            for s in siblings:
                merged_results[s.result_id] = s
            
            # On remet sous forme de liste
            final_list = list(merged_results.values())

        # 4. FORMATAGE DE SORTIE (Ton code original adapté)
        # On trie pour que les batches restent groupés visuellement (par date ou ID)
        final_list.sort(key=lambda x: x.result_id, reverse=True)

        if self._est_medical_lecture_seule():
            final_list = [r for r in final_list if r.status == "completed"]

        return [{
            'result_id': r.result_id,
            'code': r.code_lab_patient,
            'batch_id': str(r.batch_id) if r.batch_id else None, # <-- Ajout utile pour le front
            'patient_name': self._format_patient_name(r),
            'test_date': r.test_date.strftime("%d/%m/%Y %H:%M") if r.test_date else "",
            'examen_nom': r.examen.nom if r.examen else 'Inconnu',
            'status': r.status
        } for r in final_list]
    
    def search_internal_with_prescriptions(self, query: str):
        # On ne traite pas si c'est vide
        if not query.strip():
            return []
        # Ordonnances (lignes restantes) + examens factures non recus - voir le repo.
        return self.repo.get_reception_candidates(query.strip())

    def get_results_by_batch_id(self, batch_id_str: str) -> List[Dict]:
        """Méthode appelée quand on clique sur un dossier groupé"""
        try:
            # Conversion string -> UUID
            b_uuid = uuid.UUID(batch_id_str)
            results = self.repo.get_results_by_batch_id(b_uuid)

            if self._est_medical_lecture_seule():
                results = [r for r in results if r.status == "completed"]

            # On retourne le format complet (LabResultOut)
            # Adapte 'to_dict()' selon comment tu formates tes objets habituellement
            # Ici je suppose que tes schémas Pydantic feront le travail de sérialisation
            return results 
        except ValueError:
            return []
    




    def get_patient_lab_history(self, patient_id: int) -> List[Dict]:
        """Historique par patient."""
        results = self.repo.list_results_for_patient(patient_id)
        if self._est_medical_lecture_seule():
            results = [r for r in results if r.status == "completed"]
        flagged_counts = self.repo.count_flagged_by_result([r.result_id for r in results])
        return [{
            'result_id': r.result_id,
            'code_lab': r.code_lab_patient,
            'test_date': r.test_date.strftime('%Y-%m-%d %H:%M') if r.test_date else '-',
            'examen_name': r.examen.nom if r.examen else 'Inconnu',
            'status': r.status,
            'prescribed_by': r.prescribed_by or "N/A",
            'nb_anormaux': flagged_counts.get(r.result_id, 0),
            'corrected': bool(r.corrected),
        } for r in results]

    def get_dashboard_stats(self, period: str = "month") -> Dict:
        """KPIs Dashboard."""
        try:
            # On utilise la NOUVELLE méthode du repo (get_advanced_stats)
            return self.repo.get_advanced_stats(filter_type=period)
        except Exception as e:
            print(f"Erreur Stats: {e}") # Utile pour le debug dans ton terminal
            # On retourne un dictionnaire vide mais formaté correctement en cas d'erreur
            return {
                "pending": 0, "completed_today": 0, "revenue_month": 0.0, "critical": 0,
                "total_month": 0, "top_exams": {}, "max_exam_count": 1, "recent_pending": [], "recent_passages": []
        }

            