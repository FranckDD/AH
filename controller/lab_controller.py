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
from repositories.lab_repo import LabRepository
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
from api_backend.backend_app.utils.patient_resolution import resolve_patient_id

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

    def create_examen(self, data: Dict[str, Any]) -> Dict:
        """Crée un nouvel examen."""
        ex = self.repo.create_examen(data)
        return self._serialize_examen(ex)

    def update_examen(self, examen_id: int, data: Dict[str, Any]) -> Optional[Dict]:
        """Met à jour un examen."""
        clean_data = {k: v for k, v in data.items() if v is not None}
        ex = self.repo.update_examen(examen_id, clean_data)
        return self._serialize_examen(ex) if ex else None

    def delete_examen(self, examen_id: int) -> bool:
        """Supprime un examen."""
        return self.repo.delete_examen(examen_id)

    # --- Gestion des Paramètres (Leucocytes, Hématies...) ---

    def add_parametre(self, examen_id: int, data: Dict[str, Any]) -> Dict:
        """Ajoute un paramètre à un examen existant."""
        data['examen_id'] = examen_id
        p = self.repo.create_parametre(data)
        return {"id": p.id, "nom": p.nom_parametre, "unite": p.unite}

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
                        "min": float(r.valeur_min) if r.valeur_min else None, 
                        "max": float(r.valeur_max) if r.valeur_max else None
                    } for r in p.reference_ranges
                ]
            })
        return result

    def delete_parametre(self, param_id: int) -> bool:
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

    def get_paginated_results(self, page: int = 1, limit: int = 20, search: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
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
            status=status
        )
        
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
                'test_date': r.test_date.strftime("%d/%m/%Y %H:%M") if r.test_date else "",
                'status': r.status,
                'batch_id': str(r.batch_id) if r.batch_id else None
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

        # 2. Calcul Âge et Sexe
        age_patient, sexe_patient = self.repo._get_patient_bio_info(r)
        
        if r.patient:
            patient_name = f"{r.patient.last_name} {r.patient.first_name}"
        else:
            patient_name = r.external_patient_info.get('nom', 'Inconnu') if r.external_patient_info else 'Inconnu'

        patient_info = {
            "nom": patient_name,
            "age": age_patient,
            "sexe": sexe_patient
        }
        
        # 3. Traitement des résultats et des normes
        details_format_list = []
        
        for d in r.details:
            if not d.parametre: 
                continue
                
            p = d.parametre
            norme_trouvee = None
            
            # On ne cherche la norme que si c'est un paramètre numérique
            if p.input_type == 'numeric':
                for rr in p.reference_ranges:
                    if rr.sexe in ['X', sexe_patient] and (rr.age_min <= age_patient <= rr.age_max):
                        norme_trouvee = rr
                        break

            # Formatage de l'affichage de la Norme
            norme_affichage = "-"
            if p.input_type == 'numeric' and norme_trouvee:
                if norme_trouvee.valeur_min is not None and norme_trouvee.valeur_max is not None:
                    # Formatage propre pour enlever les zéros inutiles si besoin, ex: 4.50 -> 4.5
                    min_val = round(norme_trouvee.valeur_min, 2)
                    max_val = round(norme_trouvee.valeur_max, 2)
                    norme_affichage = f"[{min_val} - {max_val}]"

            # Extraction de la valeur du résultat saisie
            if p.input_type == 'numeric' and d.valeur_num is not None:
                valeur_resultat = str(round(d.valeur_num, 2))
            else:
                valeur_resultat = d.valeur_text or ""

            details_format_list.append({
                "parametre_nom": p.nom_parametre,  # Changé de 'parametre' à 'parametre_nom'
                "valeur": valeur_resultat,
                "unite": p.unite or "",
                "reference_str": norme_affichage, # Changé de 'norme_affichage' à 'reference_str'
                "is_abnormal": d.flagged,         # Ajouté pour la couleur rouge (flag-H)
                "interpretation": d.interpretation or ""
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
                "note": r.note # Utilisé pour la conclusion en bas
            },
            "details": details_format_list,
            "date_impression": datetime.now().strftime("%d/%m/%Y à %H:%M")
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
        for d in r.details:
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
            "patient_info": self._format_patient_info(r),
            "examen_nom": r.examen.nom if r.examen else "Inconnu",
            "details": details_out
        }
    
    # ====================================================================
    # 🧪 PAILLASSE (LISTE TECHNIQUE)
    # ====================================================================
    def get_paillasse_list(self) -> List[Dict]:
        """Récupère les dossiers en attente avec toutes les infos formatées."""
        
        # Récupère les résultats depuis le Repo (avec joinedload !)
        results = self.repo.get_active_worklist() 
        
        output = []
        for r in results:
            # On utilise le helper pour extraire proprement les infos patient
            p_infos = self._format_patient_info(r)
            
            output.append({
                'result_id': r.result_id,  # L'ID technique du dossier
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
        except Exception as e:
            self.logger.error(f"Erreur submit values {result_id}: {e}")
            raise e

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

        # Appel au repo (Jointure SQL)
        results = self.repo.get_internal_with_active_prescription(query.strip())

        # Formatage pour le frontend (le Store Pinia)
        return [
            {
                "id": p.patient_id,
                "nom": p.last_name,
                "patient_code": p.code_patient ,
                "prescription_id": pr.prescription_id,
                "exams_prescribed": pr.lab_exams_list,
                "has_active_prescription": True
            } for p, pr in results
        ]
    

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
        return [{
            'result_id': r.result_id,
            'code_lab': r.code_lab_patient,
            'test_date': r.test_date.strftime('%Y-%m-%d %H:%M') if r.test_date else '-',
            'examen_name': r.examen.nom if r.examen else 'Inconnu',
            'status': r.status,
            'prescribed_by': r.prescribed_by or "N/A"
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
                "total_month": 0, "top_exams": {}, "max_exam_count": 1, "recent_pending": []
        }

            