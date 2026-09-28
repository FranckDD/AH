# controllers/patient_controller.py

import logging
import os
import json
import redis
from dotenv import load_dotenv
from celery import Task
from typing import Optional, Dict, Any, List
from datetime import date, timedelta, datetime, time
from sqlalchemy.exc import SQLAlchemyError

# --- Modèles & Repos ---
from models.application_role import ApplicationRole
from models.user import User
from repositories.audit_repo import AuditRepository

# --- Optimisation ---
# Import de la tâche (Fallback si fichier non créé)
try:
    from tasks.patient_tasks import task_notify_new_patient # type: ignore
    task_notify_new_patient: Task = task_notify_new_patient # type: ignore
except ImportError:
    task_notify_new_patient = None # type: ignore

# Config Redis
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class PatientController:
    def __init__(self, repo, current_user, audit_repo: Optional[AuditRepository] = None):
        self.repo = repo
        self.user = current_user
        self.audit_repo = audit_repo
        self.session = repo.session
        self.logger = logging.getLogger(__name__)

    def _get_user_roles_set(self):
        """Helper privé pour récupérer les rôles."""
        roles_set = set()
        if hasattr(self.user, 'postgres_role') and self.user.postgres_role:
            roles_set.add(self.user.postgres_role.lower())
        if hasattr(self.user, 'roles'):
            for r in self.user.roles:
                roles_set.add(r.lower())
        role_name = getattr(self.user, 'role_name', None)
        if role_name:
            roles_set.add(role_name.lower())
        return roles_set

    # 🟢 Helper d'invalidation du cache
    def _invalidate_patient_stats(self):
        """Supprime les clés de cache liées aux statistiques patients."""
        try:
            # On supprime les compteurs globaux et les KPIs spirituels
            keys = [
                "patient:stats:global",
                "patient:stats:spiritual:status",
                "patient:stats:spiritual:assurance"
            ]
            # Pour les clés dynamiques (dates), on utilise pattern matching si nécessaire
            # ou on laisse le TTL expirer (ici on supprime les gros agrégats)
            redis_client.delete(*keys)
            
            # Optionnel : Invalider aussi les recherches par jour si critique
            # keys_registered = redis_client.keys("patient:stats:registered:*")
            # if keys_registered: redis_client.delete(*keys_registered)
            
        except Exception as e:
            self.logger.warning(f"⚠️ [REDIS] Erreur invalidation: {e}")

    # =========================================================================
    # PARTIE 1 : LOGIQUE MÉTIER PURE (PRÉPARATION) - Inchangée
    # =========================================================================

    def create_patient(self, data: dict) -> tuple[int, str]:
        required = ['first_name', 'last_name', 'birth_date']
        if any(not data.get(f) for f in required):
            raise ValueError("Champs obligatoires manquants")

        # Chantier L4b-e : bloc jumeau de celui retire de update_patient au
        # chantier 7a (roles 'app_secretaire'/'app_medical' qui ne
        # correspondent a aucun role reel du systeme depuis le chantier 6),
        # deja inerte de toute facon : PatientCreate.is_spiritual/is_clinical
        # defautent a False, jamais None (patients_schemas.py) - la
        # condition 'is None' n'etait donc jamais vraie.

        result = self.repo.create_patient(data, self.user)
        patient_id, patient_code = result
        
        if self.audit_repo and self.user:
            self.audit_repo.log_user_action(
                current_user=self.user,
                resource_type="Patient",
                action_performed="CREATE",
                resource_id=patient_id,
                details=f"Nom: {data.get('last_name')} {data.get('first_name')}",
                new_values=data 
            )
        
        return patient_id, patient_code

    def update_patient(self, patient_id: int, data: dict) -> tuple[int, str]:
        existing_patient = self.repo.get_by_id(patient_id)
        if not existing_patient:
            raise ValueError("Patient introuvable")

        # Chantier 7a : l'ancien bloc de "protection" des drapeaux
        # is_clinical/is_toxicology/is_spiritual (roles 'app_admin',
        # 'app_secretaire', 'app_toxico_web'... qui ne correspondent a
        # aucun role reel du systeme) est retire - il dupliquait de facon
        # confuse une protection deja assuree par la procedure stockee
        # public.update_patient (ci/schema_only.sql : COALESCE(p_is_X, is_X)
        # preserve la valeur existante si le champ n'est pas envoye). Ces
        # 3 colonnes ne sont de toute facon plus une source de verite
        # depuis le chantier 6 (compute_domain_flags, calcul a la lecture).

        old_values = {k: existing_patient.get(k) for k in data.keys() if k in existing_patient}

        self.repo.update_patient(patient_id, data, self.user)
        
        if self.audit_repo and self.user:
            self.audit_repo.log_user_action(
                current_user=self.user,
                resource_type="Patient",
                action_performed="UPDATE",
                resource_id=patient_id,
                old_values=old_values, 
                new_values=data
            )
            
        return patient_id, existing_patient['code_patient']

    # =========================================================================
    # PARTIE 2 : MÉTHODES TRANSACTIONNELLES (Avec Optimisation)
    # =========================================================================

    def sync_simple_patient_creation(self, data: dict) -> tuple[int, str]:
        """Wrapper transactionnel : Prépare + Valide + Async Tasks."""
        try:
            # 1. Logique métier
            pid, code = self.create_patient(data)
            
            # 2. Validation DB
            self.session.commit()

            # 3. 🟢 Invalidation Cache Stats
            self._invalidate_patient_stats()

            # 4. 🟢 Tâche Celery (Notification)
            if task_notify_new_patient:
                try:
                    task_notify_new_patient.delay(
                        patient_id=pid,
                        code=code,
                        first_name=data.get('first_name', ''),
                        phone=data.get('contact_phone')
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ [CELERY] Erreur tâche notification: {e}")

            return pid, code

        except SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"Erreur SQL Transaction Simple Create : {e}")
            raise
        except Exception:
            self.session.rollback()
            raise

    def sync_simple_patient_update(self, patient_id: int, data: dict) -> tuple[int, str]:
        try:
            pid, code = self.update_patient(patient_id, data)
            self.session.commit()
            
            # 🟢 Invalidation Cache (Les stats peuvent changer si on modifie le type de patient)
            self._invalidate_patient_stats()
            
            return pid, code
        except SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"Erreur SQL Transaction Simple Update : {e}")
            raise
        except Exception:
            self.session.rollback()
            raise

    # =========================================================================
    # PARTIE 3 : MÉTHODES DE LECTURE (Avec Cache)
    # =========================================================================

    def get_global_counts(self):
        """Récupère les compteurs globaux (cache 10 min)."""
        CACHE_KEY = "patient:stats:global"
        counts = None

        try:
            cached = redis_client.get(CACHE_KEY)
            if cached:
                counts = json.loads(cached)
        except Exception: pass

        if counts is None:
            # Calcul DB
            counts = self.repo.get_global_patient_counts()

            try:
                redis_client.setex(CACHE_KEY, 600, json.dumps(counts))
            except Exception: pass

        # medecin/nurse ne doivent connaitre ni le volume toxico ni le
        # volume spirituel (chantier perimetre medical, 2026-09-22) - le
        # cache reste partage entre tous les roles avec les vraies valeurs,
        # le filtre s'applique seulement sur la copie renvoyee a ce role,
        # jamais sur la valeur mise en cache elle-meme (sinon un admin
        # recevrait ensuite des zeros restes en cache).
        if self._get_user_roles_set() & {"medecin", "nurse"}:
            counts = {**counts, "total_toxicology": 0, "total_spiritual": 0}

        return counts

    def count_registered(self, period: str = "day") -> int:
        """Compte les inscrits (Cache 5 min)."""
        today = date.today()
        # Clé unique par jour et période
        CACHE_KEY = f"patient:stats:registered:{period}:{today}"
        
        try:
            cached = redis_client.get(CACHE_KEY)
            if cached: return int(cached) # type: ignore
        except Exception: pass

        if period == "day":
            res = self.repo.count_by_creation_date(today)
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            res = self.repo.count_by_creation_date_range(start_week, end_week)
        else:
            raise ValueError("Période non valide")
            
        try:
            redis_client.setex(CACHE_KEY, 300, res)
        except Exception: pass
        
        return res

    def get_spiritual_new_patients_count_kpi(self, period: str = "week") -> int:
        # Pas de cache ici pour simplifier (ou ajouter si très lent)
        today = date.today()
        if period == "day":
            start_date = datetime.combine(today, time.min)
            end_date = start_date + timedelta(days=1)
        elif period == "week":
            start_date = datetime.combine(today - timedelta(days=today.weekday()), time.min)
            end_date = start_date + timedelta(days=7)
        else:
            raise ValueError("Période non valide")
        return self.repo.count_new_spiritual_patients_by_range(start_date=start_date, end_date=end_date)

    def get_spiritual_patient_status_kpi(self) -> Dict[str, int]:
        CACHE_KEY = "patient:stats:spiritual:status"
        try:
            cached = redis_client.get(CACHE_KEY)
            if cached: return json.loads(cached) # type: ignore
        except Exception: pass

        data = self.repo.get_spiritual_patient_status_distribution()
        
        try:
            redis_client.setex(CACHE_KEY, 600, json.dumps(data))
        except Exception: pass
        return data

    def get_spiritual_assurance_distribution_kpi(self) -> Dict[str, int]:
        CACHE_KEY = "patient:stats:spiritual:assurance"
        try:
            cached = redis_client.get(CACHE_KEY)
            if cached: return json.loads(cached) # type: ignore
        except Exception: pass

        data = self.repo.get_spiritual_assurance_distribution_kpi()
        
        try:
            redis_client.setex(CACHE_KEY, 600, json.dumps(data))
        except Exception: pass
        return data

    # --- MÉTHODES STANDARD (Sans Cache) ---
    
    def delete_patient(self, patient_id: int) -> bool:
        user_id = getattr(self.user, 'user_id', None)
        success = self.repo.delete_patient(patient_id, user_id)
        if success:
            if self.audit_repo and self.user:
                try:
                    self.audit_repo.log_user_action(
                        current_user=self.user,
                        resource_type="Patient",
                        action_performed="SOFT_DELETE",
                        resource_id=patient_id
                    )
                except Exception:
                    self.logger.exception("Échec de l'écriture d'audit")
            # Invalidation
            self._invalidate_patient_stats()
        return success

    def get_patient(self, patient_id: int) -> dict:
        return self.repo.get_by_id(patient_id)

    def list_patients(self, page=1, per_page=10, search=None):
        roles = self._get_user_roles_set()
        filters = {}
        if not search:
            # Le filtre par domaine (B6) ne restreint que la navigation par
            # defaut - une recherche explicite doit pouvoir trouver n'importe
            # quel patient existant, y compris hors du domaine du role, sinon
            # le rattachement inter-domaines (chantier 6) devient impossible :
            # un role ne peut alors trouver que des patients qui ONT DEJA un
            # dossier dans son propre domaine, jamais ceux qui en ont besoin.
            if 'secretaire' in roles:
                filters['is_spiritual'] = True
            elif 'assistant' in roles:
                # 🟢 chantier 6, tache 3 : "assistant" est le role d'admission
                # toxico (voir toxico_endpoint.py) - il doit retrouver les
                # patients deja connus du volet toxicologie, pas du clinique.
                filters['is_toxicology'] = True
            elif roles & {'medecin', 'nurse'}:
                filters['is_clinical'] = True
        return self.repo.list_patients(page=page, per_page=per_page, search=search, filters=filters)
    
    def list_patients_for_export(self, tab_type: str = "ALL", search: Optional[str] = None,
                                   date_from=None, date_to=None) -> List:
        """
        Meme mapping onglet -> filtre que les endpoints /clinical,
        /toxicology, /spiritual/list existants - l'export respecte
        l'onglet actif a l'ecran (decision utilisateur, chantier exports).
        """
        if tab_type in ("TOXICO", "SPIRITUEL") and self._get_user_roles_set() & {"medecin", "nurse"}:
            # Coherence avec /patients/toxicology et /patients/spiritual/list
            # (chantier perimetre medical, 2026-09-22), qui excluent deja
            # medecin/nurse via une garde de route dediee - cet export ne
            # doit pas devenir un contournement de cette regle.
            raise PermissionError("Export reserve, hors perimetre clinique de ce role.")
        filters = None
        if tab_type == "CLINIQUE":
            filters = {"is_clinical": True}
        elif tab_type == "TOXICO":
            filters = {"is_toxicology": True}
        elif tab_type == "SPIRITUEL":
            filters = {"is_spiritual": True}
        return self.repo.list_patients_for_export(search=search, filters=filters, date_from=date_from, date_to=date_to)

    def list_spiritual_patients(self):
        return self.repo.find_by_creator_role('secretaire')

    def list_clinical_patients(self, page=1, per_page=10, search=None):
        return self.repo.list_clinical_patients(page, per_page, search)

    def list_toxicology_patients(self, page=1, per_page=10, search=None):
        return self.repo.list_toxicology_patients(page, per_page, search)

    def list_spiritual_patients_list(self, page=1, per_page=10, search=None):
        return self.repo.list_spiritual_patients_paginated(page, per_page, search)
    
    def find_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        p = self.repo.find_by_code(code)
        if not p: return None
        return {
            'patient_id':    p.patient_id,
            'code_patient':  p.code_patient,
            'first_name':    p.first_name,
            'last_name':     p.last_name,
            'birth_date':    p.birth_date,
            'gender':        p.gender,
            'national_id':   p.national_id,
            'contact_phone': p.contact_phone,
            'assurance':     p.assurance,
            'residence':     p.residence,
            'father_name':   p.father_name,
            'mother_name':   p.mother_name,
        }

    def find_patient(self, query: str):
        if not query: return None
        q = query.strip()
        if q.isdigit():
            pid = int(q)
            return self.repo.find_by_id(pid)
        else:
            return self.repo.find_by_code(q)

    def patients_followed_by_doctor(self, doctor_id: Optional[int] = None, page=1, per_page=50):
        d = doctor_id or getattr(self.user, 'user_id', None)
        if d is None: raise RuntimeError("Doctor id non disponible")
        return self.repo.patients_followed_by_doctor(d, page=page, per_page=per_page)
    
    def patients_by_consultation_type(self, doctor_id: Optional[int] = None, start: Optional[date]=None, end: Optional[date]=None):
        d = doctor_id or getattr(self.user, 'user_id', None)
        if d is None: raise RuntimeError("Doctor id non disponible")
        return self.repo.patients_by_consultation_type_for_doctor(d, start=start, end=end)
    
    def patients_for_day(self, target_date: date, doctor_id: Optional[int] = None):
        d = doctor_id or getattr(self.user, 'user_id', None)
        if d is None: raise RuntimeError("doctor_id non disponible")
        return self.repo.patients_for_day(d, target_date)

    def find_by_patient_presc(self, query: str):
        if not query: return None
        q = query.strip()
        try:
            p = self.repo.find_for_prescription(q)
            if not p: return None
            # Si p est un objet SQLAlchemy, on le transforme (simplification)
            if hasattr(p, "__dict__") and not isinstance(p, dict):
                return {
                    'patient_id':    getattr(p, 'patient_id', None),
                    'code_patient':  getattr(p, 'code_patient', None),
                    'first_name':    getattr(p, 'first_name', None),
                    'last_name':     getattr(p, 'last_name', None),
                    'birth_date':    getattr(p, 'birth_date', None),
                    'gender':        getattr(p, 'gender', None),
                    'national_id':   getattr(p, 'national_id', None),
                    'contact_phone': getattr(p, 'contact_phone', None),
                    'assurance':     getattr(p, 'assurance', None),
                    'residence':     getattr(p, 'residence', None),
                    'father_name':   getattr(p, 'father_name', None),
                    'mother_name':   getattr(p, 'mother_name', None),
                }
            return p
        except Exception as e:
            self.logger.exception("Erreur find_by_patient_presc: %s", e)
            return None
        
    def new_patients_for_day(self, target_date: date, doctor_id: Optional[int] = None,
                             page: int = 1, per_page: int = 200) -> List[Dict[str, Any]]:
        pats = self.repo.get_new_patients_for_day(target_date, doctor_id=doctor_id, page=page, per_page=per_page)

        def serialize(p):
            pid = getattr(p, "patient_id", None) or getattr(p, "id", None)
            code = getattr(p, "code_patient", None)
            fname = getattr(p, "first_name", None)
            lname = getattr(p, "last_name", None)
            birth = getattr(p, "birth_date", None)
            age = None
            try:
                if birth:
                    today = date.today()
                    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            except Exception:
                age = None
            return {
                "patient_id": pid,
                "code_patient": code,
                "first_name": fname,
                "last_name": lname,
                "birth_date": birth,
                "age": age,
            }
        return [serialize(p) for p in pats]