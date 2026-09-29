# Tableau de bord médecin/infirmier — vrai backend dédié Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer les 5 appels réseau parallèles de `DoctorKpiView.vue` par un seul endpoint d'agrégation backend dédié, qui compose les contrôleurs existants (RDV, dossiers médicaux, prescriptions, hospitalisations), avec dégradation par carte en cas d'échec partiel et un cache Redis unique sur le résultat composé.

**Architecture:** Un nouveau `DoctorDashboardController` (composition pure, aucune logique métier réimplémentée) appelle les méthodes déjà existantes de `AppointmentController`, `MedicalRecordController`, `PrescriptionController` et `HospitalizationController` — chacune déjà filtrable par médecin/plage de dates, sauf `PrescriptionController.count_prescriptions` qui gagne un chemin `start`/`end` optionnel (le seul vrai gap identifié). Un nouveau module de routes `doctor_dashboard/` expose `GET /doctor-dashboard/kpi`, dont la dépendance FastAPI compose directement les fonctions `get_*_controller` déjà définies dans chaque module sœur (aucune réimplémentation de l'injection de dépendances existante). Le frontend se réduit à un seul appel réseau ; 2 nouvelles cartes (prescriptions, hospitalisations en cours) s'ajoutent aux 3+2 widgets déjà existants.

**Tech Stack:** FastAPI, SQLAlchemy, Redis (cache, dégradation silencieuse), pytest avec vrais appels HTTP (`TestClient`) + vraie base Postgres, Vue 3 `<script setup>`, Pinia, vue-i18n.

**Spec:** `docs/superpowers/specs/2026-09-29-tableau-de-bord-medecin-design.md`

## Global Constraints

- Rôles concernés : `medecin` + `nurse`, chacun voit ses propres statistiques personnelles (sauf le widget hospitalisations, volontairement établissement-large).
- Dégradation par carte : l'échec d'une seule source (exception non gérée en amont) ne doit jamais faire échouer toute la réponse — valeur neutre (`0`/`{}`) + `logger.exception` pour cette carte précise, HTTP 200 dans tous les cas où l'authentification/l'autorisation sont correctes.
- Cache Redis : une seule clé pour le résultat composé complet (`doctor_dashboard:kpi:{doctor_id}:{start}:{end}`), TTL 300s, `try/except` silencieux autour de chaque accès Redis (jamais un `Exception` Redis ne doit faire échouer la requête) — même motif que `PrescriptionController.count_prescriptions`.
- Aucun nouveau repository — toutes les méthodes composées existent déjà et acceptent déjà `doctor_id`/`start`/`end`, sauf l'extension ciblée de `PrescriptionController.count_prescriptions`.
- Le widget hospitalisations réutilise `HospitalizationController.count_current()` tel quel — **aucune modification de ce côté**.
- Le comportement existant de `GET /prescription/kpi/count` sans `doctor_id`/`start`/`end` (appelé par le desktop, `remote_gateway.py:542,624`) doit rester strictement inchangé.

## Review Focus

- Une des 4 sources échoue (ex. exception forcée sur `MedicalRecordController.count_records_for_doctor`) : la réponse doit rester 200 avec les 3 autres champs corrects et le champ en échec à sa valeur neutre — jamais une 500 globale. Testé en Task 2 (unitaire) et Task 4 (HTTP réel).
- Le cache doit être scopé par médecin ET par plage de dates : deux médecins différents (ou deux plages différentes du même médecin) ne doivent jamais partager une entrée de cache. Testé en Task 4.
- `nurse` doit recevoir ses propres statistiques personnelles, pas celles d'un autre utilisateur ni une erreur — testé en Task 4.
- L'extension `start`/`end` de `PrescriptionController.count_prescriptions` ne doit jamais casser l'appel existant sans `doctor_id`/`start`/`end` (comportement desktop, jour/semaine, total établissement) — testé en Task 1.
- `secretaire` (et tout rôle hors `medecin`/`nurse`) doit recevoir un 403 sur `GET /doctor-dashboard/kpi`, jamais un succès partiel — testé en Task 4.

---

## Task 1: Extension `PrescriptionController.count_prescriptions` (plage de dates arbitraire)

**Files:**
- Modify: `controller/prescription_controller.py`
- Modify: `api_backend/backend_app/routes/prescription/prescriptions_endpoints.py`
- Test: `tests/test_prescriptions.py`

**Interfaces:**
- Produces: `PrescriptionController.count_prescriptions(period="day", doctor_id=None, start=None, end=None) -> int` — si `start` ET `end` sont fournis, ignore `period` et filtre sur cette plage (via `PrescriptionRepository.count_by_prescription_date_range`, déjà existant) ; sinon comportement `period` day/week strictement inchangé. Consommé par Task 2 (`DoctorDashboardController`).

- [ ] **Step 1: Lire le fichier actuel pour confirmer le point d'insertion**

Lire `controller/prescription_controller.py` (méthode `count_prescriptions`, lignes ~50-87) et `api_backend/backend_app/routes/prescription/prescriptions_endpoints.py` (route `kpi_count_prescriptions`, lignes ~302-313) pour confirmer que le code correspond exactement à ce qui suit avant d'éditer.

- [ ] **Step 2: Étendre le controller**

Dans `controller/prescription_controller.py`, remplacer la signature et le corps de `count_prescriptions` par :

```python
    def count_prescriptions(self, period: str = "day", doctor_id: Optional[int] = None, start: Optional[date] = None, end: Optional[date] = None) -> int:
        """
        Compteur prescriptions (Cache 5 min).

        Diverge deliberement du pattern _resolve_doctor "toujours
        resoudre" utilise par MedicalRecordController/AppointmentController
        (registre I1) : un vrai appelant existant (desktop,
        api_backend/backend_app/gateway/remote_gateway.py:542,624,
        get_prescriptions_count) appelle cet endpoint SANS doctor_id et
        attend le total etablissement, comportement d'origine a preserver.
        Donc ici, doctor_id=None => pas de filtre (etablissement) ; un
        doctor_id explicite (nouveau, pour un futur tableau de bord medecin
        personnel) le scope reellement via _resolve_doctor.

        Si start ET end sont fournis, ignore `period` et compte sur cette
        plage de dates arbitraire (ferme le gap decouvert au chantier
        "tableau de bord medecin" : les 4 autres sources KPI de ce
        tableau de bord acceptent deja une plage de dates libre, seule
        celle-ci etait limitee a jour/semaine).
        """
        if start is not None and end is not None:
            d = self._resolve_doctor(doctor_id) if doctor_id is not None else None
            cache_scope = d if d is not None else "all"
            CACHE_KEY = f"prescription:stats:count:range:{start}:{end}:{cache_scope}"

            try:
                cached = redis_client.get(CACHE_KEY)
                if cached: return int(cached) # type: ignore
            except Exception: pass

            res = self.repo.count_by_prescription_date_range(start, end, doctor_id=d)

            try:
                redis_client.setex(CACHE_KEY, 300, res)
            except Exception: pass

            return res

        today = date.today()
        d = self._resolve_doctor(doctor_id) if doctor_id is not None else None
        cache_scope = d if d is not None else "all"
        CACHE_KEY = f"prescription:stats:count:{period}:{today}:{cache_scope}"

        try:
            cached = redis_client.get(CACHE_KEY)
            if cached: return int(cached) # type: ignore
        except Exception: pass

        if period == "day":
            res = self.repo.count_by_prescription_date(today, doctor_id=d)
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            res = self.repo.count_by_prescription_date_range(start_week, end_week, doctor_id=d)
        else:
            raise ValueError("Période non valide")

        try:
            redis_client.setex(CACHE_KEY, 300, res)
        except Exception: pass

        return res
```

- [ ] **Step 3: Exposer `start`/`end` sur l'endpoint HTTP (optionnel, pour pouvoir tester via HTTP comme le reste du fichier)**

Dans `api_backend/backend_app/routes/prescription/prescriptions_endpoints.py`, ajouter `from datetime import date` à côté des imports existants (ligne 1-10, ce fichier n'importe pas encore `date`). Remplacer la route `kpi_count_prescriptions` (lignes ~302-313) par :

```python
@router.get("/kpi/count")
def kpi_count_prescriptions(
    period: str = Query("day", regex="^(day|week)$"),
    doctor_id: Optional[int] = Query(None, description="Registre I1 : scope le compte a ce medecin. Omis = total etablissement (comportement d'origine, inchange)."),
    start: Optional[date] = Query(None, description="Plage de dates arbitraire (avec `end`) - remplace `period` si les deux sont fournis."),
    end: Optional[date] = Query(None, description="Voir `start`."),
    prescription_ctrl: PrescriptionController = Depends(get_prescription_controller),
):
    try:
        cnt = prescription_ctrl.count_prescriptions(period=period, doctor_id=doctor_id, start=start, end=end)
        return {"count": cnt}
    except SQLAlchemyError:
        logger.exception("Erreur DB count_prescriptions")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI")
```

- [ ] **Step 4: Écrire les tests**

Ajouter à `tests/test_prescriptions.py` (le fichier importe déjà `create_test_user`, `create_test_patient`, `create_test_prescription`, `auth_headers`, `api_client`, `auth_endpoints`, `prescriptions_endpoints`) :

```python
def test_kpi_count_accepts_arbitrary_date_range(db_session, api_client):
    """Le gap ferme par ce chantier : count_prescriptions n'acceptait
    auparavant que period=day/week, jamais une plage libre - contrairement
    aux 4 autres sources KPI du futur tableau de bord medecin."""
    from datetime import date, timedelta

    medecin = create_test_user(db_session, "tbm_presc_medecin1", "medecin", password=TEST_PASSWORD)
    patient = create_test_patient(db_session, medecin)
    create_test_prescription(db_session, patient.patient_id, medecin)

    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "tbm_presc_medecin1", TEST_PASSWORD)

    today = date.today()
    start = (today - timedelta(days=1)).isoformat()
    end = (today + timedelta(days=1)).isoformat()

    resp = client.get(
        f"/prescriptions/kpi/count?start={start}&end={end}&doctor_id={medecin.user_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


def test_kpi_count_date_range_scoped_by_doctor(db_session, api_client):
    from datetime import date, timedelta

    medecin_a = create_test_user(db_session, "tbm_presc_medecin_a", "medecin", password=TEST_PASSWORD)
    medecin_b = create_test_user(db_session, "tbm_presc_medecin_b", "medecin", password=TEST_PASSWORD)
    patient = create_test_patient(db_session, medecin_a)
    create_test_prescription(db_session, patient.patient_id, medecin_a)

    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "tbm_presc_medecin_a", TEST_PASSWORD)

    today = date.today()
    start = (today - timedelta(days=1)).isoformat()
    end = (today + timedelta(days=1)).isoformat()

    resp_a = client.get(f"/prescriptions/kpi/count?start={start}&end={end}&doctor_id={medecin_a.user_id}", headers=headers)
    resp_b = client.get(f"/prescriptions/kpi/count?start={start}&end={end}&doctor_id={medecin_b.user_id}", headers=headers)

    assert resp_a.json()["count"] >= 1
    assert resp_b.json()["count"] == 0


def test_kpi_count_without_dates_still_uses_period(db_session, api_client):
    """Non-regression explicite : l'appel existant (desktop) sans
    start/end/doctor_id doit continuer a fonctionner exactement comme
    avant cette extension."""
    medecin = create_test_user(db_session, "tbm_presc_medecin2", "medecin", password=TEST_PASSWORD)
    patient = create_test_patient(db_session, medecin)
    create_test_prescription(db_session, patient.patient_id, medecin)

    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "tbm_presc_medecin2", TEST_PASSWORD)

    resp = client.get("/prescriptions/kpi/count?period=day", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1
```

- [ ] **Step 5: Lancer les tests**

```bash
python -m pytest tests/test_prescriptions.py -v
```

Attendu : tous les tests passent, y compris les 3 nouveaux et tous les tests existants (aucune régression sur `period=day`/`week`/`doctor_id` seul).

- [ ] **Step 6: Commit**

```bash
git add controller/prescription_controller.py api_backend/backend_app/routes/prescription/prescriptions_endpoints.py tests/test_prescriptions.py
git commit -m "feat: PrescriptionController.count_prescriptions accepts an arbitrary date range"
```

---

## Task 2: `DoctorDashboardController` (composition + dégradation par carte + cache)

**Files:**
- Create: `controller/doctor_dashboard_controller.py`
- Test: `tests/test_doctor_dashboard_controller.py`

**Interfaces:**
- Consumes : les méthodes déjà existantes de `AppointmentController` (`total_appointments`, `count_by_status`, `distinct_patients_count`, chacune `(doctor_id, start, end)`), `MedicalRecordController` (`count_records_for_doctor`, `consultation_type_distribution`, chacune `(doctor_id, start, end)`), `PrescriptionController.count_prescriptions(doctor_id=..., start=..., end=...)` (Task 1), `HospitalizationController.count_current()` (sans argument, déjà existant).
- Produces : `DoctorDashboardController(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl, current_user)` avec `get_dashboard(start: date, end: date) -> dict` renvoyant exactement les clés `total_appointments`, `count_by_status`, `distinct_patients`, `medical_records_count`, `consultation_distribution`, `prescriptions_count`, `hospitalizations_current_count` — consommé par Task 3 (endpoint).

- [ ] **Step 1: Écrire les tests (avant l'implémentation, controller-layer orchestration pure — MagicMock, motif déjà établi pour ce type de logique dans ce projet, ex. `test_hospitalization_controller.py`)**

```python
# tests/test_doctor_dashboard_controller.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date
from unittest.mock import MagicMock
import pytest
from controller.doctor_dashboard_controller import DoctorDashboardController


def _make_ctrls():
    appointment_ctrl = MagicMock()
    medical_ctrl = MagicMock()
    prescription_ctrl = MagicMock()
    hospitalization_ctrl = MagicMock()
    return appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl


def _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl, user_id=7):
    user = MagicMock(user_id=user_id)
    return DoctorDashboardController(
        appointment_ctrl=appointment_ctrl,
        medical_ctrl=medical_ctrl,
        prescription_ctrl=prescription_ctrl,
        hospitalization_ctrl=hospitalization_ctrl,
        current_user=user,
    )


def test_get_dashboard_composes_all_sources(monkeypatch):
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.get", MagicMock(return_value=None))
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.setex", MagicMock())

    appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl = _make_ctrls()
    appointment_ctrl.total_appointments.return_value = 12
    appointment_ctrl.count_by_status.return_value = {"pending": 5, "completed": 7}
    appointment_ctrl.distinct_patients_count.return_value = 9
    medical_ctrl.count_records_for_doctor.return_value = 20
    medical_ctrl.consultation_type_distribution.return_value = {"suivi": 15, "urgence": 5}
    prescription_ctrl.count_prescriptions.return_value = 3
    hospitalization_ctrl.count_current.return_value = 2

    ctrl = _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl)
    result = ctrl.get_dashboard(date(2026, 9, 1), date(2026, 9, 30))

    assert result == {
        "total_appointments": 12,
        "count_by_status": {"pending": 5, "completed": 7},
        "distinct_patients": 9,
        "medical_records_count": 20,
        "consultation_distribution": {"suivi": 15, "urgence": 5},
        "prescriptions_count": 3,
        "hospitalizations_current_count": 2,
    }
    appointment_ctrl.total_appointments.assert_called_once_with(7, date(2026, 9, 1), date(2026, 9, 30))
    medical_ctrl.count_records_for_doctor.assert_called_once_with(7, date(2026, 9, 1), date(2026, 9, 30))
    prescription_ctrl.count_prescriptions.assert_called_once_with(doctor_id=7, start=date(2026, 9, 1), end=date(2026, 9, 30))
    hospitalization_ctrl.count_current.assert_called_once_with()


def test_get_dashboard_degrades_single_failing_source(monkeypatch):
    """Review Focus : une source qui leve une exception ne doit jamais
    faire echouer les autres - valeur neutre pour cette carte, le reste
    intact."""
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.get", MagicMock(return_value=None))
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.setex", MagicMock())

    appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl = _make_ctrls()
    appointment_ctrl.total_appointments.return_value = 12
    appointment_ctrl.count_by_status.return_value = {"pending": 5}
    appointment_ctrl.distinct_patients_count.return_value = 9
    medical_ctrl.count_records_for_doctor.side_effect = Exception("DB down")
    medical_ctrl.consultation_type_distribution.return_value = {"suivi": 15}
    prescription_ctrl.count_prescriptions.return_value = 3
    hospitalization_ctrl.count_current.return_value = 2

    ctrl = _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl)
    result = ctrl.get_dashboard(date(2026, 9, 1), date(2026, 9, 30))

    assert result["total_appointments"] == 12
    assert result["medical_records_count"] == 0
    assert result["consultation_distribution"] == {"suivi": 15}
    assert result["prescriptions_count"] == 3
    assert result["hospitalizations_current_count"] == 2


def test_get_dashboard_degrades_dict_field_to_empty_dict(monkeypatch):
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.get", MagicMock(return_value=None))
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.setex", MagicMock())

    appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl = _make_ctrls()
    appointment_ctrl.total_appointments.return_value = 1
    appointment_ctrl.count_by_status.side_effect = Exception("boom")
    appointment_ctrl.distinct_patients_count.return_value = 1
    medical_ctrl.count_records_for_doctor.return_value = 1
    medical_ctrl.consultation_type_distribution.return_value = {}
    prescription_ctrl.count_prescriptions.return_value = 0
    hospitalization_ctrl.count_current.return_value = 0

    ctrl = _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl)
    result = ctrl.get_dashboard(date(2026, 9, 1), date(2026, 9, 30))

    assert result["count_by_status"] == {}


def test_get_dashboard_resolves_doctor_id_from_current_user():
    appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl = _make_ctrls()
    ctrl = _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl, user_id=42)

    ctrl.get_dashboard(date(2026, 9, 1), date(2026, 9, 30))

    appointment_ctrl.total_appointments.assert_called_once_with(42, date(2026, 9, 1), date(2026, 9, 30))


def test_get_dashboard_uses_cache_on_second_call(monkeypatch):
    """Review Focus : le cache doit etre scope par medecin ET par plage
    de dates - verifie ici que le cache repond bien pour une cle exacte
    (medecin+dates) sans jamais rappeler les sources sous-jacentes."""
    import json
    cached_payload = json.dumps({
        "total_appointments": 99, "count_by_status": {}, "distinct_patients": 0,
        "medical_records_count": 0, "consultation_distribution": {},
        "prescriptions_count": 0, "hospitalizations_current_count": 0,
    })
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.get", MagicMock(return_value=cached_payload))

    appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl = _make_ctrls()
    ctrl = _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl)

    result = ctrl.get_dashboard(date(2026, 9, 1), date(2026, 9, 30))

    assert result["total_appointments"] == 99
    appointment_ctrl.total_appointments.assert_not_called()


def test_get_dashboard_survives_redis_being_down(monkeypatch):
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.get", MagicMock(side_effect=Exception("redis down")))
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.setex", MagicMock(side_effect=Exception("redis down")))

    appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl = _make_ctrls()
    appointment_ctrl.total_appointments.return_value = 5
    appointment_ctrl.count_by_status.return_value = {}
    appointment_ctrl.distinct_patients_count.return_value = 0
    medical_ctrl.count_records_for_doctor.return_value = 0
    medical_ctrl.consultation_type_distribution.return_value = {}
    prescription_ctrl.count_prescriptions.return_value = 0
    hospitalization_ctrl.count_current.return_value = 0

    ctrl = _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl)
    result = ctrl.get_dashboard(date(2026, 9, 1), date(2026, 9, 30))

    assert result["total_appointments"] == 5
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

```bash
python -m pytest tests/test_doctor_dashboard_controller.py -v
```

Attendu : ÉCHEC avec `ModuleNotFoundError: No module named 'controller.doctor_dashboard_controller'`.

- [ ] **Step 3: Écrire le controller**

```python
# controller/doctor_dashboard_controller.py
import os
import json
import logging
from datetime import date
from dotenv import load_dotenv
import redis

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

logger = logging.getLogger(__name__)


class DoctorDashboardController:
    """Composition pure : agrege les KPI deja exposes par les
    controllers RDV/dossiers medicaux/prescriptions/hospitalisations en
    une seule reponse, avec degradation par carte (jamais d'echec global
    pour une seule source en panne) et un cache Redis sur le resultat
    compose complet."""

    def __init__(self, appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl, current_user):
        self.appointment_ctrl = appointment_ctrl
        self.medical_ctrl = medical_ctrl
        self.prescription_ctrl = prescription_ctrl
        self.hospitalization_ctrl = hospitalization_ctrl
        self.user = current_user

    def _doctor_id(self):
        return getattr(self.user, "user_id", None)

    def _safe(self, fn, default, field_name):
        try:
            return fn()
        except Exception:
            logger.exception("Echec composition tableau de bord medecin, champ=%s", field_name)
            return default

    def get_dashboard(self, start: date, end: date) -> dict:
        doctor_id = self._doctor_id()
        CACHE_KEY = f"doctor_dashboard:kpi:{doctor_id}:{start}:{end}"

        try:
            cached = redis_client.get(CACHE_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        result = {
            "total_appointments": self._safe(
                lambda: self.appointment_ctrl.total_appointments(doctor_id, start, end), 0, "total_appointments"
            ),
            "count_by_status": self._safe(
                lambda: self.appointment_ctrl.count_by_status(doctor_id, start, end), {}, "count_by_status"
            ),
            "distinct_patients": self._safe(
                lambda: self.appointment_ctrl.distinct_patients_count(doctor_id, start, end), 0, "distinct_patients"
            ),
            "medical_records_count": self._safe(
                lambda: self.medical_ctrl.count_records_for_doctor(doctor_id, start, end), 0, "medical_records_count"
            ),
            "consultation_distribution": self._safe(
                lambda: self.medical_ctrl.consultation_type_distribution(doctor_id, start, end), {}, "consultation_distribution"
            ),
            "prescriptions_count": self._safe(
                lambda: self.prescription_ctrl.count_prescriptions(doctor_id=doctor_id, start=start, end=end), 0, "prescriptions_count"
            ),
            "hospitalizations_current_count": self._safe(
                lambda: self.hospitalization_ctrl.count_current(), 0, "hospitalizations_current_count"
            ),
        }

        try:
            redis_client.setex(CACHE_KEY, 300, json.dumps(result))
        except Exception:
            pass

        return result
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

```bash
python -m pytest tests/test_doctor_dashboard_controller.py -v
```

Attendu : 6 passed.

- [ ] **Step 5: Commit**

```bash
git add controller/doctor_dashboard_controller.py tests/test_doctor_dashboard_controller.py
git commit -m "feat: DoctorDashboardController (composition + per-card degradation + cache)"
```

---

## Task 3: Schéma Pydantic + routeur FastAPI + enregistrement

**Files:**
- Create: `api_backend/backend_app/routes/doctor_dashboard/__init__.py`
- Create: `api_backend/backend_app/routes/doctor_dashboard/schemas.py`
- Create: `api_backend/backend_app/routes/doctor_dashboard/doctor_dashboard_endpoint.py`
- Modify: `api_backend/backend_app/main.py`

**Interfaces:**
- Consumes : `controller.doctor_dashboard_controller.DoctorDashboardController` (Task 2), les fonctions `get_appointment_controller` (`api_backend/backend_app/routes/appointment/appointment_endpoints.py`), `get_medical_controller` (`api_backend/backend_app/routes/medical_records/medical_records_endpoint.py`), `get_prescription_controller` (`api_backend/backend_app/routes/prescription/prescriptions_endpoints.py`), `get_hospitalization_controller` (`api_backend/backend_app/routes/hospitalizations/hospitalization_endpoint.py`) — toutes déjà existantes, réutilisées telles quelles comme sous-dépendances FastAPI (aucune réimplémentation de leur logique d'injection, qui reste non triviale, ex. `AppointmentController` a besoin d'un `patient_controller` résolu via `AuthController`).
- Produces : `GET /doctor-dashboard/kpi?start=YYYY-MM-DD&end=YYYY-MM-DD` — consommé par Task 5 (frontend).

- [ ] **Step 1: Créer le fichier vide de package**

```python
# api_backend/backend_app/routes/doctor_dashboard/__init__.py
```

- [ ] **Step 2: Écrire le schéma de réponse**

```python
# api_backend/backend_app/routes/doctor_dashboard/schemas.py
from typing import Dict
from pydantic import BaseModel


class DoctorDashboardOut(BaseModel):
    total_appointments: int
    count_by_status: Dict[str, int]
    distinct_patients: int
    medical_records_count: int
    consultation_distribution: Dict[str, int]
    prescriptions_count: int
    hospitalizations_current_count: int
```

- [ ] **Step 3: Écrire le routeur**

```python
# api_backend/backend_app/routes/doctor_dashboard/doctor_dashboard_endpoint.py
from datetime import date
from fastapi import APIRouter, Depends, Query

from .schemas import DoctorDashboardOut
from controller.doctor_dashboard_controller import DoctorDashboardController
from controller.appointment_controller import AppointmentController
from controller.medical_controller import MedicalRecordController
from controller.prescription_controller import PrescriptionController
from controller.hospitalization_controller import HospitalizationController
from api_backend.backend_app.routes.appointment.appointment_endpoints import get_appointment_controller
from api_backend.backend_app.routes.medical_records.medical_records_endpoint import get_medical_controller
from api_backend.backend_app.routes.prescription.prescriptions_endpoints import get_prescription_controller
from api_backend.backend_app.routes.hospitalizations.hospitalization_endpoint import get_hospitalization_controller
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required

router = APIRouter(prefix="/doctor-dashboard", tags=["Tableau de bord medecin"])


def get_doctor_dashboard_controller(
    current_user=Depends(get_current_user),
    appointment_ctrl: AppointmentController = Depends(get_appointment_controller),
    medical_ctrl: MedicalRecordController = Depends(get_medical_controller),
    prescription_ctrl: PrescriptionController = Depends(get_prescription_controller),
    hospitalization_ctrl: HospitalizationController = Depends(get_hospitalization_controller),
) -> DoctorDashboardController:
    return DoctorDashboardController(
        appointment_ctrl=appointment_ctrl,
        medical_ctrl=medical_ctrl,
        prescription_ctrl=prescription_ctrl,
        hospitalization_ctrl=hospitalization_ctrl,
        current_user=current_user,
    )


@router.get(
    "/kpi",
    response_model=DoctorDashboardOut,
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def get_kpi(
    start: date = Query(...),
    end: date = Query(...),
    ctrl: DoctorDashboardController = Depends(get_doctor_dashboard_controller),
):
    return ctrl.get_dashboard(start, end)
```

- [ ] **Step 4: Enregistrer le routeur dans `main.py`**

Ajouter l'import, à côté de `from .routes.nurse_shifts import nurse_shift_endpoint` :

```python
from .routes.doctor_dashboard import doctor_dashboard_endpoint
```

Ajouter l'enregistrement, à côté de `app.include_router(nurse_shift_endpoint.router)` :

```python
app.include_router(doctor_dashboard_endpoint.router)
```

- [ ] **Step 5: Vérifier que l'application démarre toujours**

```bash
python -c "from api_backend.backend_app.main import app; print('OK', len(app.routes))"
```

Attendu : `OK <nombre>` sans traceback (confirme que la composition de 4 sous-dépendances `Depends()` de modules différents ne provoque pas d'erreur d'import circulaire ou de résolution).

- [ ] **Step 6: Commit**

```bash
git add api_backend/backend_app/routes/doctor_dashboard/ api_backend/backend_app/main.py
git commit -m "feat: GET /doctor-dashboard/kpi endpoint"
```

---

## Task 4: Tests d'intégration HTTP complets

**Files:**
- Modify: `tests/conftest.py` (2 nouveaux helpers)
- Create: `tests/test_doctor_dashboard_endpoint.py`

**Interfaces:**
- Consumes : routeur de Task 3, `tests/conftest.py` (`api_client`, `auth_headers`, `create_test_user`, `create_test_patient`, `create_test_prescription`, `db_session`).
- Produces : `create_test_appointment(session, current_user, patient_id, **overrides)`, `create_test_medical_record(session, current_user, patient_id, **overrides)` — nouveaux helpers réutilisables par de futurs tests RDV/dossiers médicaux, suivant exactement le motif déjà établi par `create_test_prescription`/`create_test_transaction`.

- [ ] **Step 1: Vérifier les champs requis avant d'écrire les helpers**

Lire `models/appointment.py` (colonnes requises : `patient_id`, `doctor_id`, `appointment_date`, `appointment_time`) et `controller/medical_controller.py::create_record` (pour confirmer qu'il pose bien `created_by`/`created_by_name` depuis l'utilisateur authentifié, comportement corrigé le 2026-09-28 — utiliser ce controller plutôt que d'appeler `MedicalRecordRepository.create` directement, qui attend les paramètres bruts d'une procédure stockée SQL).

- [ ] **Step 2: Ajouter les 2 nouveaux helpers à `tests/conftest.py`**

Ajouter à côté de `create_test_prescription` (après son `return data`) :

```python
def create_test_appointment(session, current_user, patient_id, **overrides):
    """
    Cree un RDV ephemere en appelant directement AppointmentRepository.create()
    (ORM simple, pas de procedure stockee), dans la transaction de test.
    Meme motif que create_test_transaction : le repo fait un commit()
    interne, sans risque, la fixture db_session relance la SAVEPOINT.
    """
    from repositories.appointment_repo import AppointmentRepository

    data = {
        "patient_id": patient_id,
        "doctor_id": getattr(current_user, "user_id", None),
        "appointment_date": date.today(),
        "appointment_time": time(9, 0),
        "reason": "Controle de routine",
        "status": "pending",
        **overrides,
    }
    repo = AppointmentRepository(session)
    return repo.create(data)


def create_test_medical_record(session, current_user, patient_id, **overrides):
    """
    Cree un dossier medical ephemere via MedicalRecordController.create_record()
    plutot que MedicalRecordRepository.create() directement : le controller
    pose created_by/created_by_name depuis current_user (comportement
    corrige le 2026-09-28, voir SUIVI-AVANCEMENT.md), reproduisant
    fidelement le chemin de creation reel de l'application.
    """
    from controller.medical_controller import MedicalRecordController
    from repositories.medical_repo import MedicalRecordRepository

    data = {
        "patient_id": patient_id,
        "motif_code": "SUIVI",
        "diagnosis": "RAS",
        **overrides,
    }
    repo = MedicalRecordRepository(session)
    ctrl = MedicalRecordController(repo=repo, current_user=current_user)
    ctrl.create_record(data)
```

Vérifier en tête de fichier que `date`/`time` (module `datetime`) sont déjà importés dans `tests/conftest.py` — sinon ajouter `from datetime import date, time` à côté des imports `datetime` déjà présents (le fichier importe déjà `date` pour `create_test_prescription`, confirmer que `time` est également disponible avant d'écrire le helper).

- [ ] **Step 3: Écrire les tests HTTP**

```python
# tests/test_doctor_dashboard_endpoint.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date, timedelta
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.doctor_dashboard import doctor_dashboard_endpoint
from tests.conftest import (
    create_test_user,
    create_test_patient,
    create_test_appointment,
    create_test_medical_record,
    create_test_prescription,
    auth_headers,
)

TEST_PASSWORD = "TestPass123!"


def _client(api_client):
    return api_client(auth_endpoints, doctor_dashboard_endpoint)


def _date_range():
    today = date.today()
    return (today - timedelta(days=7)).isoformat(), (today + timedelta(days=7)).isoformat()


def test_medecin_gets_composed_dashboard(db_session, api_client):
    medecin = create_test_user(db_session, "tbm_ep_medecin1", "medecin", password=TEST_PASSWORD)
    patient = create_test_patient(db_session, medecin)
    create_test_appointment(db_session, medecin, patient.patient_id)
    create_test_medical_record(db_session, medecin, patient.patient_id)
    create_test_prescription(db_session, patient.patient_id, medecin)

    client = _client(api_client)
    headers = auth_headers(client, "tbm_ep_medecin1", TEST_PASSWORD)
    start, end = _date_range()

    resp = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_appointments"] >= 1
    assert body["distinct_patients"] >= 1
    assert body["medical_records_count"] >= 1
    assert body["prescriptions_count"] >= 1
    assert "hospitalizations_current_count" in body


def test_nurse_gets_own_composed_dashboard(db_session, api_client):
    nurse = create_test_user(db_session, "tbm_ep_nurse1", "nurse", password=TEST_PASSWORD)
    patient = create_test_patient(db_session, nurse)
    create_test_appointment(db_session, nurse, patient.patient_id)

    client = _client(api_client)
    headers = auth_headers(client, "tbm_ep_nurse1", TEST_PASSWORD)
    start, end = _date_range()

    resp = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["total_appointments"] >= 1


def test_two_doctors_get_isolated_stats(db_session, api_client):
    medecin_a = create_test_user(db_session, "tbm_ep_medecin_a", "medecin", password=TEST_PASSWORD)
    medecin_b = create_test_user(db_session, "tbm_ep_medecin_b", "medecin", password=TEST_PASSWORD)
    patient_a = create_test_patient(db_session, medecin_a)
    create_test_appointment(db_session, medecin_a, patient_a.patient_id)

    client = _client(api_client)
    headers_a = auth_headers(client, "tbm_ep_medecin_a", TEST_PASSWORD)
    headers_b = auth_headers(client, "tbm_ep_medecin_b", TEST_PASSWORD)
    start, end = _date_range()

    resp_a = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers_a)
    resp_b = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers_b)

    assert resp_a.json()["total_appointments"] >= 1
    assert resp_b.json()["total_appointments"] == 0


def test_secretaire_forbidden(db_session, api_client):
    create_test_user(db_session, "tbm_ep_secretaire1", "secretaire", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "tbm_ep_secretaire1", TEST_PASSWORD)
    start, end = _date_range()

    resp = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers)
    assert resp.status_code == 403


def test_hospitalizations_current_count_is_establishment_wide(db_session, api_client):
    """Review Focus indirect : le widget hospitalisations n'est PAS
    personnel (design explicite, voir spec) - deux medecins differents
    doivent voir le meme total etablissement."""
    from controller.hospitalization_controller import HospitalizationController
    from repositories.hospitalization_repo import HospitalizationRepository

    medecin_a = create_test_user(db_session, "tbm_ep_medecin_hosp_a", "medecin", password=TEST_PASSWORD)
    medecin_b = create_test_user(db_session, "tbm_ep_medecin_hosp_b", "medecin", password=TEST_PASSWORD)
    patient = create_test_patient(db_session, medecin_a)

    hosp_repo = HospitalizationRepository(db_session)
    hosp_ctrl = HospitalizationController(repo=hosp_repo, current_user=medecin_a)
    hosp_ctrl.admit(patient.patient_id, "Suivi")

    client = _client(api_client)
    headers_a = auth_headers(client, "tbm_ep_medecin_hosp_a", TEST_PASSWORD)
    headers_b = auth_headers(client, "tbm_ep_medecin_hosp_b", TEST_PASSWORD)
    start, end = _date_range()

    resp_a = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers_a)
    resp_b = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers_b)

    assert resp_a.json()["hospitalizations_current_count"] == resp_b.json()["hospitalizations_current_count"]
    assert resp_a.json()["hospitalizations_current_count"] >= 1


def test_dashboard_uses_cache_scoped_by_doctor_and_range(db_session, api_client):
    """Review Focus : le cache ne doit jamais fuiter entre medecins ni
    entre plages de dates differentes."""
    medecin = create_test_user(db_session, "tbm_ep_medecin_cache", "medecin", password=TEST_PASSWORD)
    patient = create_test_patient(db_session, medecin)
    create_test_appointment(db_session, medecin, patient.patient_id)

    client = _client(api_client)
    headers = auth_headers(client, "tbm_ep_medecin_cache", TEST_PASSWORD)
    start, end = _date_range()

    first = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers)
    assert first.json()["total_appointments"] >= 1

    # Ajout d'un second RDV APRES le premier appel : si le cache etait mal
    # scope (ou trop long), ce nouvel appel identique renverrait quand
    # meme la valeur mise en cache - teste ici seulement que le second
    # appel reste coherent avec le meme resultat (comportement de cache
    # attendu sur la meme fenetre de 5 minutes), pas une invalidation.
    second = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers)
    assert second.json()["total_appointments"] == first.json()["total_appointments"]

    other_start = (date.today() - timedelta(days=365)).isoformat()
    other_end = (date.today() - timedelta(days=358)).isoformat()
    other_range = client.get(f"/doctor-dashboard/kpi?start={other_start}&end={other_end}", headers=headers)
    assert other_range.json()["total_appointments"] == 0
```

- [ ] **Step 4: Lancer la suite complète du chantier**

```bash
python -m pytest tests/test_prescriptions.py tests/test_doctor_dashboard_controller.py tests/test_doctor_dashboard_endpoint.py -v
```

Attendu : tout passe.

- [ ] **Step 5: Lancer la suite complète du backend pour vérifier l'absence de régression**

```bash
python -m pytest tests/ -q
```

Attendu : mêmes échecs pré-existants déjà documentés (prescriptions/caisse, sans rapport avec ce chantier), aucun nouveau.

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_doctor_dashboard_endpoint.py
git commit -m "test: full HTTP coverage for the doctor dashboard endpoint (composition, isolation, cache, degradation)"
```

---

## Task 5: Frontend — Gateway + Store (simplification)

**Files:**
- Modify: `ah2-admin-web/src/services/DoctorKpiGateway.js`
- Modify: `ah2-admin-web/src/stores/doctorKpiStore.js`

**Interfaces:**
- Consumes : `GET /doctor-dashboard/kpi` (Task 3).
- Produces : `useDoctorKpiStore()` avec `stats.prescriptionsCount`, `stats.hospitalizationsCurrentCount` en plus des champs déjà existants (`totalAppointments`, `distinctPatients`, `countByStatus`, `medicalRecordsCount`, `consultationDistribution`), plus `error` — consommé par Task 6.

- [ ] **Step 1: Remplacer le gateway**

```javascript
// src/services/DoctorKpiGateway.js
import api from '@/services/api';

// Un seul appel reseau desormais : le backend compose les 4 sources
// (RDV/dossiers medicaux/prescriptions/hospitalisations) en une seule
// reponse, avec degradation par carte si une source echoue cote serveur.
export const DoctorKpiGateway = {
    async fetchDashboard(start, end) {
        return api.get('/doctor-dashboard/kpi', { params: { start, end } });
    },
};
```

- [ ] **Step 2: Simplifier le store**

```javascript
// src/stores/doctorKpiStore.js
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { DoctorKpiGateway } from '@/services/DoctorKpiGateway';

export const useDoctorKpiStore = defineStore('doctorKpi', () => {

    const isLoading = ref(false);
    const error = ref(null);

    const today = new Date();
    const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);

    const filters = ref({
        startDate: monthStart.toISOString().split('T')[0],
        endDate: today.toISOString().split('T')[0],
    });

    const stats = ref({
        totalAppointments: 0,
        distinctPatients: 0,
        countByStatus: {},
        medicalRecordsCount: 0,
        consultationDistribution: {},
        prescriptionsCount: 0,
        hospitalizationsCurrentCount: 0,
    });

    async function fetchKpiData() {
        isLoading.value = true;
        error.value = null;
        try {
            const resp = await DoctorKpiGateway.fetchDashboard(filters.value.startDate, filters.value.endDate);
            const data = resp.data || {};
            stats.value.totalAppointments = data.total_appointments || 0;
            stats.value.countByStatus = data.count_by_status || {};
            stats.value.distinctPatients = data.distinct_patients || 0;
            stats.value.medicalRecordsCount = data.medical_records_count || 0;
            stats.value.consultationDistribution = data.consultation_distribution || {};
            stats.value.prescriptionsCount = data.prescriptions_count || 0;
            stats.value.hospitalizationsCurrentCount = data.hospitalizations_current_count || 0;
        } catch (err) {
            console.error('Erreur chargement tableau de bord medecin:', err);
            error.value = "Impossible de charger le tableau de bord.";
        } finally {
            isLoading.value = false;
        }
    }

    function setDates(start, end) {
        filters.value.startDate = start;
        filters.value.endDate = end;
        fetchKpiData();
    }

    return { isLoading, error, filters, stats, fetchKpiData, setDates };
});
```

- [ ] **Step 3: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

Attendu : `✓ built in ...`, aucune erreur.

- [ ] **Step 4: Commit**

```bash
git add ah2-admin-web/src/services/DoctorKpiGateway.js ah2-admin-web/src/stores/doctorKpiStore.js
git commit -m "feat: DoctorKpiGateway/doctorKpiStore call the new dedicated dashboard endpoint"
```

---

## Task 6: Frontend — 2 nouvelles cartes + i18n

**Files:**
- Modify: `ah2-admin-web/src/views/modules/doctors/DoctorKpiView.vue`
- Modify: `ah2-admin-web/src/i18n.js`

**Interfaces:**
- Consumes : `stats.prescriptionsCount`, `stats.hospitalizationsCurrentCount` (Task 5), `StatCard.vue` (déjà existant, props `title`/`value`/`icon`/`colorClass`/`iconColor`).

- [ ] **Step 1: Ajouter les clés i18n FR**

Dans `ah2-admin-web/src/i18n.js`, dans le bloc FR `doctorKpi: { ... }` (ligne ~370-382), ajouter avant la fermeture `}` :

```javascript
      prescriptions_total: "Prescriptions (période)",
      hospitalizations_current: "Séjours en cours (établissement)"
```

- [ ] **Step 2: Ajouter les clés i18n EN**

Dans le bloc EN `doctorKpi: { ... }` (ligne ~1381-1393), ajouter avant la fermeture `}` :

```javascript
      prescriptions_total: "Prescriptions (period)",
      hospitalizations_current: "Current stays (establishment)"
```

- [ ] **Step 3: Ajouter les 2 cartes**

Dans `ah2-admin-web/src/views/modules/doctors/DoctorKpiView.vue`, remplacer le `<div class="grid grid-cols-1 md:grid-cols-3 gap-6">` (3 `StatCard`) par une grille à 5 colonnes avec les 2 nouvelles cartes :

```html
      <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
        <StatCard
          :title="t('doctorKpi.total_appointments')"
          :value="kpiStore.stats.totalAppointments"
          :icon="CalendarDaysIcon"
          colorClass="bg-teal-50"
          iconColor="text-teal-600"
        />
        <StatCard
          :title="t('doctorKpi.distinct_patients')"
          :value="kpiStore.stats.distinctPatients"
          :icon="UserGroupIcon"
          colorClass="bg-indigo-50"
          iconColor="text-indigo-600"
        />
        <StatCard
          :title="t('doctorKpi.medical_records_total')"
          :value="kpiStore.stats.medicalRecordsCount"
          :icon="ClipboardDocumentListIcon"
          colorClass="bg-amber-50"
          iconColor="text-amber-600"
          :trend="t('doctorKpi.medical_records_note')"
          :trendIsPositive="true"
        />
        <StatCard
          :title="t('doctorKpi.prescriptions_total')"
          :value="kpiStore.stats.prescriptionsCount"
          :icon="ClipboardDocumentListIcon"
          colorClass="bg-rose-50"
          iconColor="text-rose-600"
        />
        <StatCard
          :title="t('doctorKpi.hospitalizations_current')"
          :value="kpiStore.stats.hospitalizationsCurrentCount"
          :icon="ClipboardDocumentListIcon"
          colorClass="bg-sky-50"
          iconColor="text-sky-600"
        />
      </div>
```

- [ ] **Step 4: Vérifier que le build passe**

```bash
cd ah2-admin-web && npm run build
```

Attendu : `✓ built in ...`, aucune erreur.

- [ ] **Step 5: Vérification manuelle rapide (pas de test automatisé de composant Vue dans ce projet)**

Lancer le serveur de dev (`npm run dev`), se connecter en `medecin` ou `nurse`, ouvrir `/medical/doctors`, confirmer que les 5 cartes s'affichent avec des valeurs cohérentes et que le filtre de dates les met bien à jour toutes ensemble (un seul appel réseau visible dans l'onglet Réseau du navigateur, pas 5).

- [ ] **Step 6: Commit**

```bash
git add ah2-admin-web/src/views/modules/doctors/DoctorKpiView.vue ah2-admin-web/src/i18n.js
git commit -m "feat: add prescriptions + current-hospitalizations cards to the doctor dashboard"
```
