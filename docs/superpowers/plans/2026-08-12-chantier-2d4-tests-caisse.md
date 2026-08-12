# Chantier 2d-4 — Tests d'intégration caisse et retrait — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Couvrir par des tests d'intégration réels les deux routeurs financiers `/caisse` (17 endpoints) et `/retrait` (6 endpoints), en s'appuyant sur l'infrastructure `db_session`/`api_client`/`create_test_user`/`create_test_patient`/`login` livrée par 2d-0 à 2d-3, et documenter (sans les corriger) les défauts réels découverts sur `HEAD` pendant le cadrage de ce plan — vérifiés par exécution réelle contre un worktree jetable basé sur `HEAD` (créé et supprimé pendant le cadrage, jamais contre le répertoire de travail principal, contaminé par le travail en cours sur `caisse_controller.py`/`caisse_repo.py`/`mapping.py`).

**Architecture:** Deux factories ajoutées à `tests/conftest.py` (`create_test_transaction`, `create_test_retrait`, appelant directement les repositories réels). Deux fichiers de tests séparés : `tests/test_caisse.py` (~30 tests) et `tests/test_retrait.py` (~11 tests) — deux routeurs, deux contrôleurs, deux repositories distincts, aucun code partagé entre eux hormis les factories communes.

**Tech Stack:** pytest, SQLAlchemy 2.0, FastAPI `TestClient`, PostgreSQL (base `AH2` locale réelle).

## Corrections et découvertes empiriques par rapport à la spec (`2026-08-12-chantier-2d4-tests-caisse-design.md`)

- **Bug 1 de la spec (notification Celery avec `tx.id` au lieu de `tx.transaction_id`) : ne se manifeste PAS sur `HEAD`.** `tasks/finance_tasks.py` n'existe que dans le travail en cours non commité de l'utilisateur — sur `HEAD`, `from tasks.finance_tasks import task_process_payment_notification` lève `ImportError`, capturé par `except ImportError: task_process_payment_notification = None`, et tout le bloc de notification est court-circuité (`if task_process_payment_notification:` est toujours faux). Confirmé par exécution réelle : une création de transaction prend 0,15s, pas de blocage. **Aucun test ne documente ce bug** — il ne redeviendra pertinent que si `tasks/finance_tasks.py` est un jour commité (item de registre pour cette éventualité, pas un test).
- **Bug 2 de la spec (suppression idempotente silencieuse) : confirmé tel quel.** `DELETE /caisse/999999999` → 204.
- **Découverte supplémentaire, hors spec initiale — `mapping.py::normalize_caisse_data` calcule `amount_due` et `amount_paid` de façon incorrecte.** `amount_due` est calculé comme `amount + advance_amount` (devrait être `amount - advance_amount`) et `amount_paid` comme `amount` seul (devrait être `advance_amount`). Confirmé par exécution réelle avec `amount=100, advance_amount=30` : `amount_due=130` (attendu 70), `amount_paid=100` (attendu 30). Bug présent dans du code déjà committé (`api_backend/backend_app/routes/caisse/mapping.py`), pas dans le travail en cours (dont le diff sur ce fichier ne fait qu'une ligne, sans rapport). Ce bug est indépendant des KPIs de tableau de bord (`get_caisse_kpis`), qui calculent correctement `remaining_due = total_factured - total_paid` — confirmé correct par exécution réelle (`total_paid=40.0, total_factured=100.0, remaining_due=60.0` pour une transaction `amount=100, advance_amount=40`).
- **Découverte supplémentaire — `POST /caisse/{id}/payment` renvoie un corps vide `{}`.** La route ne déclare pas de `response_model` et le contrôleur/repository renvoient un objet ORM `PaiementEchelonne` brut, que FastAPI ne sait pas sérialiser utilement sans schéma — confirmé par exécution réelle (`201` avec `{}`). Comportement documenté tel quel, pas corrigé.
- **Découverte supplémentaire — `total_remaining_due` filtre implicitement `status='active'` même sans paramètre `status`**, contrairement à `total`/`total_payments` qui ne filtrent par statut que si explicitement demandé (`repositories/caisse_repo.py::get_total_remaining_due` : `query.filter(Caisse.status == (status or 'active'))`). Incohérence documentée par un test, pas corrigée.
- **Découverte supplémentaire — annuler une transaction déjà annulée est idempotent silencieux (200), alors qu'annuler un retrait déjà annulé est refusé (400 "Ce retrait est déjà annulé.").** Incohérence de comportement entre les deux modules, documentée par un test sur chacun.
- **`total`/`total_payments`/`total_retraits` (sans filtre) reflètent de vraies données préexistantes dans la base partagée** (confirmé : `total=692100.0`, `total_payments=118540.0`, `total_retraits=59502.0` avant toute création de ce chantier). Les tests sur ces trois endpoints comparent une valeur avant/après une création, jamais une valeur absolue — même leçon que 2d-3.
- **Les KPIs de tableau de bord (`dashboard/caisse/kpis`, `dashboard/caisse/unpaid`, `dashboard/caisse/payment_distribution`) sont bornés par date et donnent des valeurs exactes fiables** quand `date_from=date_to=aujourd'hui` — confirmé par exécution réelle, pas de pollution par les données préexistantes en dehors de la plage.
- **Un `item_type` neutre (ex. `"Service"`), ne correspondant à aucun des mots-clés `médicament`/`medication`/`carnet`/`booklet`/`consultation`, évite toute dépendance à de vraies données `Pharmacy`/`ConsultationSpirituel`** — confirmé fonctionnel par exécution réelle. C'est le type utilisé par défaut dans la factory `create_test_transaction`.
- **`repositories/caisse_repo.py::create_transaction()` retourne directement l'objet `Caisse` complet** (contrairement à `PrescriptionRepository.create()` en 2d-3, qui ne retournait que `True`) — pas besoin de requête de relecture séparée pour obtenir l'id réel dans la factory ou les tests.

## Global Constraints

- RBAC identique sur les deux routeurs : `role_required("secretaire", "admin")`. 403 `"Accès refusé : rôle utilisateur insuffisant"` pour tout autre rôle (ex. `medecin`), 401 si non authentifié.
- Chaque test qui exerce `/caisse/*` surcharge **deux** `get_db()` via `api_client(auth_endpoints, caisse_endpoints)`. Chaque test qui exerce `/retrait/*` surcharge `api_client(auth_endpoints, retrait_endpoints)`.
- `create_transaction`/`update_transaction` prennent un `dict` brut (pas de schéma Pydantic) — la validation est manuelle côté contrôleur/repository, toutes les erreurs métier remontent en `ValueError` → 400.
- `create_retrait` utilise des paramètres `Body(...)` individuels validés par Pydantic (`amount: float = Body(..., gt=0)`) — un montant `<= 0` renvoie un 422 standard (pas de plantage, ce n'est pas un `model_validator` qui lève `ValueError`, donc le bug `E1` de prescriptions ne s'applique pas ici).
- Toute assertion sur `total`/`total_payments`/`total_remaining_due` (caisse) ou `total` (retrait) sans filtre de date doit comparer une valeur avant/après, jamais une valeur absolue — données réelles préexistantes dans la base partagée.
- Les KPIs de tableau de bord (`dashboard/caisse/*`) et les KPIs bornés par date peuvent être vérifiés en valeur exacte, à condition de borner strictement `date_from=date_to=aujourd'hui`.
- Toute ligne de transaction de test utilise `item_type="Service"` (ou toute valeur hors des mots-clés `médicament`/`medication`/`carnet`/`booklet`/`consultation`) pour éviter toute dépendance à de vraies données `Pharmacy`/`ConsultationSpirituel`.
- `create_transaction` exige ces clés dans le payload : `payment_method`, `transaction_type`, `amount`, `items`, `advance_amount`. Le montant total (`amount`) doit être égal à la somme des `line_total` des items.

---

## Task 1: Factories `create_test_transaction` et `create_test_retrait` (ajout à `tests/conftest.py`)

**Files:**
- Modify: `tests/conftest.py`

**Interfaces:**
- Consumes: `CaisseRepository` (`repositories/caisse_repo.py`, inchangé), `CaisseRetraitRepository` (`repositories/caisse_retrait_repo.py`, inchangé)
- Produces: `create_test_transaction(session, current_user, **overrides) -> Caisse`, `create_test_retrait(session, current_user, **overrides) -> CaisseRetrait`

- [ ] **Step 1: Ajouter les imports nécessaires en tête de `tests/conftest.py`**

```python
from repositories.caisse_repo import CaisseRepository
from repositories.caisse_retrait_repo import CaisseRetraitRepository
```

- [ ] **Step 2: Ajouter les deux factories à la fin de `tests/conftest.py`**

```python
def create_test_transaction(session, current_user, **overrides):
    """
    Cree une transaction caisse ephemere en appelant directement
    CaisseRepository.create_transaction() (ORM reel, pas de procedure
    stockee pour ce module). Contrairement a create_test_prescription,
    retourne directement l'objet Caisse complet (avec transaction_id
    reel) - le repository ne renvoie pas juste un booleen.

    item_type="Service" par defaut : ne correspond a aucun mot-cle
    special (medicament/carnet/consultation), evite toute dependance
    a de vraies donnees Pharmacy/ConsultationSpirituel.
    """
    data = {
        "amount": 100.0,
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {
                "item_type": "Service",
                "item_ref_id": 1,
                "unit_price": 100.0,
                "quantity": 1,
                "line_total": 100.0,
            }
        ],
        **overrides,
    }
    repo = CaisseRepository(session)
    return repo.create_transaction(data, current_user)


def create_test_retrait(session, current_user, **overrides):
    """
    Cree un retrait de caisse ephemere en appelant directement
    CaisseRetraitRepository.create().
    """
    data = {
        "amount": 50.0,
        "justification": "Retrait de test",
        "handled_by": current_user.user_id,
        "category": None,
        "payment_method": None,
        **overrides,
    }
    repo = CaisseRetraitRepository(session)
    return repo.create(**data)
```

- [ ] **Step 3: Vérifier que le fichier s'importe sans erreur**

```bash
python -c "from tests.conftest import create_test_transaction, create_test_retrait; print('ok')"
```

Attendu : `ok`, pas d'exception.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test: factories create_test_transaction et create_test_retrait (chantier 2d-4)

Appellent directement CaisseRepository.create_transaction() et
CaisseRetraitRepository.create() (ORM reel, pas de procedure stockee
pour ces deux modules). item_type=\"Service\" par defaut pour eviter
toute dependance a de vraies donnees Pharmacy/ConsultationSpirituel.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Tests de création caisse (`tests/test_caisse.py`, partie 1)

**Files:**
- Create: `tests/test_caisse.py`

**Interfaces:**
- Consumes: `db_session`, `api_client`, `create_test_user`, `create_test_patient`, `create_test_transaction`, `login`, `auth_headers` (tous déjà dans `tests/conftest.py`)
- Produces: rien — fichier de test, complété par les tâches suivantes

- [ ] **Step 1: Écrire les 7 tests de création**

```python
# tests/test_caisse.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from tests.conftest import create_test_user, create_test_patient, create_test_transaction, login, auth_headers

TEST_PASSWORD = "Correct123!"


def test_create_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_create", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_create", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "amount": 100.0,
        "advance_amount": 100.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
        ],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["amount"] == "100.00"
    assert body["advance_amount"] == "100.00"
    assert body["patient_id"] == patient_id
    assert body["transaction_id"]
    assert len(body["items"]) == 1


def test_create_transaction_partial_payment_amount_due_bug(db_session, api_client):
    """
    Documente un bug reel sur HEAD (SUIVI-AVANCEMENT.md registre a
    creer) : api_backend/backend_app/routes/caisse/mapping.py::
    normalize_caisse_data calcule amount_due = amount + advance_amount
    (au lieu de amount - advance_amount) et amount_paid = amount seul
    (au lieu de advance_amount). Constate par execution reelle : avec
    amount=100 et advance_amount=30, amount_due vaut 130 (attendu 70)
    et amount_paid vaut 100 (attendu 30). Ce bug est independant des
    KPIs de tableau de bord (get_caisse_kpis), qui calculent
    correctement remaining_due = total_factured - total_paid (voir
    test_dashboard_kpis_date_scoped_exact_values).
    """
    user = create_test_user(db_session, "test_caisse_secretaire_partial", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_partial", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "amount": 100.0,
        "advance_amount": 30.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
        ],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["amount"] == "100.00"
    assert body["advance_amount"] == "30.00"
    assert body["amount_due"] == "130.00"
    assert body["amount_paid"] == "100.00"


def test_create_transaction_missing_required_field_returns_400(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_missing", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_missing", TEST_PASSWORD)

    payload = {
        "amount": 100.0,
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "items": [],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 400
    assert "transaction_type" in resp.json()["detail"]


def test_create_transaction_amount_mismatch_returns_400(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_mismatch", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_mismatch", TEST_PASSWORD)

    payload = {
        "amount": 999.0,
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
        ],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 400
    assert "Incohérence" in resp.json()["detail"]


def test_create_transaction_invalid_consultation_reference_returns_400(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_badconsult", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_badconsult", TEST_PASSWORD)

    payload = {
        "amount": 100.0,
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {"item_type": "Consultation", "item_ref_id": 999999999, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
        ],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 400
    assert "Aucune consultation" in resp.json()["detail"]


def test_create_transaction_forbidden_for_medecin(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_medecin_create", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_medecin_create", TEST_PASSWORD)

    payload = {
        "amount": 100.0,
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
        ],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Accès refusé : rôle utilisateur insuffisant"


def test_create_transaction_unauthenticated_returns_401(db_session, api_client):
    client = api_client(auth_endpoints, caisse_endpoints)

    payload = {
        "amount": 100.0,
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [],
    }
    resp = client.post("/caisse/", json=payload)

    assert resp.status_code == 401
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_caisse.py -v
```

Attendu : 7 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_caisse.py
git commit -m "test: creation de transactions caisse (chantier 2d-4)

7 tests sur POST /caisse/ : succes, documentation du bug amount_due/
amount_paid dans mapping.py::normalize_caisse_data (registre a creer),
400 (champ requis manquant, incoherence montant/lignes, reference de
consultation invalide), 403 medecin, 401 non-authentifie.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Tests de lecture caisse (`tests/test_caisse.py`, partie 2)

**Files:**
- Modify: `tests/test_caisse.py`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichier de Task 2
- Produces: rien — complété par les tâches suivantes

- [ ] **Step 1: Ajouter les 6 tests de lecture à la fin de `tests/test_caisse.py`**

```python
def test_get_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_get", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=150.0, advance_amount=0.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 150.0, "quantity": 1, "line_total": 150.0}
    ])
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_get", TEST_PASSWORD)

    resp = client.get(f"/caisse/{tx.transaction_id}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["transaction_id"] == tx.transaction_id
    assert resp.json()["amount"] == "150.00"


def test_get_transaction_not_found(db_session, api_client):
    create_test_user(db_session, "test_caisse_secretaire_get404", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_get404", TEST_PASSWORD)

    resp = client.get("/caisse/999999999", headers=headers)

    assert resp.status_code == 404


def test_list_transactions_search_by_term(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_search", "secretaire", password=TEST_PASSWORD)
    create_test_transaction(db_session, user, transaction_type="Zzuniquetransactiontype2d4")
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_search", TEST_PASSWORD)

    resp = client.get("/caisse/?term=Zzuniquetransactiontype2d4", headers=headers)

    assert resp.status_code == 200
    types = [tx["transaction_type"] for tx in resp.json()["data"]]
    assert "Zzuniquetransactiontype2d4" in types


def test_list_transactions_filter_by_status(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_statusfilter", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, transaction_type="Zzstatusfilter2d4")
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_statusfilter", TEST_PASSWORD)

    resp_active = client.get("/caisse/?term=Zzstatusfilter2d4&status=active", headers=headers)
    assert resp_active.status_code == 200
    assert any(t["transaction_id"] == tx.transaction_id for t in resp_active.json()["data"])

    resp_cancelled = client.get("/caisse/?term=Zzstatusfilter2d4&status=cancelled", headers=headers)
    assert resp_cancelled.status_code == 200
    assert not any(t["transaction_id"] == tx.transaction_id for t in resp_cancelled.json()["data"])


def test_list_transactions_filter_by_date_range(db_session, api_client):
    from datetime import date as date_cls, timedelta

    user = create_test_user(db_session, "test_caisse_secretaire_daterange", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(
        db_session, user, transaction_type="Zzdaterange2d4",
        paid_at=date_cls(2030, 1, 15),
    )
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_daterange", TEST_PASSWORD)

    resp = client.get("/caisse/?date_from=2030-01-01&date_to=2030-01-31", headers=headers)
    assert resp.status_code == 200
    assert any(t["transaction_id"] == tx.transaction_id for t in resp.json()["data"])

    resp_excl = client.get("/caisse/?date_from=2030-02-01&date_to=2030-02-28", headers=headers)
    assert resp_excl.status_code == 200
    assert not any(t["transaction_id"] == tx.transaction_id for t in resp_excl.json()["data"])


def test_list_for_patient(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_forpatient", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, last_name="CaissePatient2d4")
    tx = create_test_transaction(db_session, user, patient_id=patient_id)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_forpatient", TEST_PASSWORD)

    resp = client.get(f"/caisse/patient/{patient_id}", headers=headers)

    assert resp.status_code == 200
    ids = [t["transaction_id"] for t in resp.json()]
    assert tx.transaction_id in ids
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_caisse.py -v
```

Attendu : 13 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_caisse.py
git commit -m "test: lecture et liste de transactions caisse (chantier 2d-4)

6 tests : GET par id (succes + 404), liste filtree par terme/statut/
plage de dates, liste par patient.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Tests de mise à jour caisse (`tests/test_caisse.py`, partie 3)

**Files:**
- Modify: `tests/test_caisse.py`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichier de Task 2-3
- Produces: rien — complété par les tâches suivantes

- [ ] **Step 1: Ajouter les 3 tests de mise à jour à la fin de `tests/test_caisse.py`**

```python
def test_update_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_update", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_update", TEST_PASSWORD)

    resp = client.put(f"/caisse/{tx.transaction_id}", json={"note": "Note mise a jour"}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["note"] == "Note mise a jour"


def test_update_transaction_refused_after_cancel(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_updatecancelled", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_updatecancelled", TEST_PASSWORD)

    cancel_resp = client.post(f"/caisse/{tx.transaction_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200

    resp = client.put(f"/caisse/{tx.transaction_id}", json={"note": "Ne devrait pas marcher"}, headers=headers)

    assert resp.status_code == 400
    assert "annulée" in resp.json()["detail"]


def test_update_transaction_not_found(db_session, api_client):
    create_test_user(db_session, "test_caisse_secretaire_update404", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_update404", TEST_PASSWORD)

    resp = client.put("/caisse/999999999", json={"note": "x"}, headers=headers)

    assert resp.status_code == 400
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_caisse.py -v
```

Attendu : 16 tests, tous PASS.

**Note sur `test_update_transaction_not_found`** : `update_transaction` (repository) lève `ValueError(f"Aucune transaction trouvée pour l'ID={transaction_id}")` sur un id inexistant, capturé par `except ValueError as ve: raise HTTPException(status_code=400, ...)` dans l'endpoint — **400, pas 404** (contrairement à `GET`/`DELETE` qui utilisent des chemins différents). Comportement réel, pas une erreur du plan.

- [ ] **Step 3: Commit**

```bash
git add tests/test_caisse.py
git commit -m "test: mise a jour de transactions caisse (chantier 2d-4)

3 tests sur PUT /caisse/{id} : succes, refus apres annulation, 400
(pas 404) sur id inexistant - update_transaction leve ValueError,
capture par le meme bloc except que les autres erreurs metier.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Tests de suppression caisse (`tests/test_caisse.py`, partie 4)

**Files:**
- Modify: `tests/test_caisse.py`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichier de Task 2-4
- Produces: rien — complété par les tâches suivantes

- [ ] **Step 1: Ajouter les 2 tests de suppression à la fin de `tests/test_caisse.py`**

```python
def test_delete_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_delete", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_delete", TEST_PASSWORD)

    delete_resp = client.delete(f"/caisse/{tx.transaction_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/caisse/{tx.transaction_id}", headers=headers)
    assert get_resp.status_code == 404


def test_delete_transaction_nonexistent_returns_204_not_404(db_session, api_client):
    """
    Documente un bug reel sur HEAD : api_backend/backend_app/routes/
    caisse/caisse_endpoints.py::delete_transaction ne verifie jamais
    la valeur de retour de caisse_ctrl.delete_transaction() -
    repositories/caisse_repo.py::delete_transaction() renvoie
    silencieusement None (pas d'exception) si l'id n'existe pas.
    Meme motif que le bug E2 de prescriptions (chantier 2d-3).
    """
    create_test_user(db_session, "test_caisse_secretaire_delete404", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_delete404", TEST_PASSWORD)

    resp = client.delete("/caisse/999999999", headers=headers)

    assert resp.status_code == 204
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_caisse.py -v
```

Attendu : 18 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_caisse.py
git commit -m "test: suppression de transactions caisse (chantier 2d-4)

2 tests sur DELETE /caisse/{id} : succes (confirme via GET 404 apres
coup) + documentation du bug de suppression idempotente silencieuse
(204 au lieu de 404 sur un id inexistant, meme motif que E2 sur
prescriptions).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: Tests paiement échelonné, solde, annulation (`tests/test_caisse.py`, partie 5)

**Files:**
- Modify: `tests/test_caisse.py`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichier de Task 2-5
- Produces: rien — complété par les tâches suivantes

- [ ] **Step 1: Ajouter les 5 tests à la fin de `tests/test_caisse.py`**

```python
def test_add_installment_payment_success(db_session, api_client):
    """
    POST /caisse/{id}/payment ne declare pas de response_model - le
    controller/repository renvoient un objet ORM PaiementEchelonne brut
    que FastAPI ne sait pas serialiser utilement sans schema. Constate
    par execution reelle : 201 avec un corps vide {}. Documente tel
    quel, pas corrige.
    """
    user = create_test_user(db_session, "test_caisse_secretaire_payment", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=30.0)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_payment", TEST_PASSWORD)

    resp = client.post(
        f"/caisse/{tx.transaction_id}/payment",
        json={"paid_amount": 20.0, "payment_method": "Especes"},
        headers=headers,
    )

    assert resp.status_code == 201
    assert resp.json() == {}

    get_resp = client.get(f"/caisse/{tx.transaction_id}", headers=headers)
    assert get_resp.json()["advance_amount"] == "50.00"


def test_add_installment_payment_exceeds_remaining_returns_400(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_paymentexceed", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=30.0)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_paymentexceed", TEST_PASSWORD)

    resp = client.post(
        f"/caisse/{tx.transaction_id}/payment",
        json={"paid_amount": 100.0, "payment_method": "Especes"},
        headers=headers,
    )

    assert resp.status_code == 400
    assert "Montant trop élevé" in resp.json()["detail"]


def test_settle_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_settle", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=30.0)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_settle", TEST_PASSWORD)

    resp = client.post(f"/caisse/{tx.transaction_id}/settle", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["advance_amount"] == "100.00"


def test_cancel_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_cancel", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_cancel", TEST_PASSWORD)

    resp = client.post(f"/caisse/{tx.transaction_id}/cancel", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["detail"] == "Annulé"

    get_resp = client.get(f"/caisse/{tx.transaction_id}", headers=headers)
    assert get_resp.json()["status"] == "cancelled"


def test_cancel_transaction_already_cancelled_is_idempotent(db_session, api_client):
    """
    Documente une incoherence entre caisse et retrait : annuler une
    transaction caisse deja annulee reussit silencieusement (200,
    repositories/caisse_repo.py::cancel_transaction fait
    "if tx.status == 'cancelled': return tx" sans lever d'exception),
    alors qu'annuler un retrait deja annule est refuse explicitement
    (400, voir test_cancel_retrait_already_cancelled_returns_400 dans
    tests/test_retrait.py).
    """
    user = create_test_user(db_session, "test_caisse_secretaire_doublecancel", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_doublecancel", TEST_PASSWORD)

    first = client.post(f"/caisse/{tx.transaction_id}/cancel", headers=headers)
    assert first.status_code == 200

    second = client.post(f"/caisse/{tx.transaction_id}/cancel", headers=headers)
    assert second.status_code == 200
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_caisse.py -v
```

Attendu : 23 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_caisse.py
git commit -m "test: paiement echelonne, solde et annulation caisse (chantier 2d-4)

5 tests : paiement echelonne (succes + documentation du corps de
reponse vide + refus si montant > reste du), solde, annulation
(succes + documentation de l'idempotence silencieuse sur double
annulation, incoherence avec le comportement de /retrait).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 7: Tests KPI caisse (`tests/test_caisse.py`, partie 6)

**Files:**
- Modify: `tests/test_caisse.py`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichier de Task 2-6
- Produces: rien — complété par les tâches suivantes

- [ ] **Step 1: Ajouter les 7 tests à la fin de `tests/test_caisse.py`**

```python
def test_daily_total_reflects_created_transaction(db_session, api_client):
    from datetime import date as date_cls

    user = create_test_user(db_session, "test_caisse_secretaire_dailytotal", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_dailytotal", TEST_PASSWORD)
    today = date_cls.today().isoformat()

    before = client.get(f"/caisse/daily_total?for_date={today}", headers=headers).json()
    create_test_transaction(db_session, user, amount=77.0, advance_amount=0.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 77.0, "quantity": 1, "line_total": 77.0}
    ])
    after = client.get(f"/caisse/daily_total?for_date={today}", headers=headers).json()

    assert after == before + 77.0


def test_total_transactions_reflects_created_transaction(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_total", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_total", TEST_PASSWORD)

    before = client.get("/caisse/total", headers=headers).json()
    create_test_transaction(db_session, user, amount=88.0, advance_amount=0.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 88.0, "quantity": 1, "line_total": 88.0}
    ])
    after = client.get("/caisse/total", headers=headers).json()

    assert after == before + 88.0


def test_total_payments_reflects_advance_amount(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_totalpay", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_totalpay", TEST_PASSWORD)

    before = client.get("/caisse/total_payments", headers=headers).json()
    create_test_transaction(db_session, user, amount=100.0, advance_amount=25.0)
    after = client.get("/caisse/total_payments", headers=headers).json()

    assert after == before + 25.0


def test_total_remaining_due_default_filters_active_status(db_session, api_client):
    """
    Documente une incoherence sur HEAD : total_remaining_due filtre
    implicitement status='active' meme sans parametre status
    (repositories/caisse_repo.py::get_total_remaining_due fait
    "query.filter(Caisse.status == (status or 'active'))"), alors que
    total/total_payments ne filtrent par statut que si explicitement
    demande. Une transaction annulee avec un solde restant du n'est
    donc jamais comptee ici, sans que l'appelant sans filtre explicite
    ne s'y attende forcement.
    """
    user = create_test_user(db_session, "test_caisse_secretaire_remaining", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_remaining", TEST_PASSWORD)

    before = client.get("/caisse/total_remaining_due", headers=headers).json()
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=40.0)
    after_active = client.get("/caisse/total_remaining_due", headers=headers).json()
    assert after_active == before + 60.0

    cancel_resp = client.post(f"/caisse/{tx.transaction_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    after_cancel = client.get("/caisse/total_remaining_due", headers=headers).json()
    assert after_cancel == before


def test_dashboard_kpis_date_scoped_exact_values(db_session, api_client):
    from datetime import date as date_cls

    user = create_test_user(db_session, "test_caisse_secretaire_dashkpis", "secretaire", password=TEST_PASSWORD)
    create_test_transaction(db_session, user, amount=100.0, advance_amount=40.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
    ])
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_dashkpis", TEST_PASSWORD)
    today = date_cls.today().isoformat()

    resp = client.get(f"/caisse/dashboard/caisse/kpis?date_from={today}&date_to={today}", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_paid"] == 40.0
    assert body["total_factured"] == 100.0
    assert body["remaining_due"] == 60.0
    assert body["total_transactions"] == 1


def test_dashboard_unpaid_list(db_session, api_client):
    from datetime import date as date_cls

    user = create_test_user(db_session, "test_caisse_secretaire_dashunpaid", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=40.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
    ])
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_dashunpaid", TEST_PASSWORD)
    today = date_cls.today().isoformat()

    resp = client.get(f"/caisse/dashboard/caisse/unpaid?date_from={today}&date_to={today}", headers=headers)

    assert resp.status_code == 200
    ids = [t["transaction_id"] for t in resp.json()]
    assert tx.transaction_id in ids


def test_dashboard_payment_distribution(db_session, api_client):
    from datetime import date as date_cls

    user = create_test_user(db_session, "test_caisse_secretaire_dashdistrib", "secretaire", password=TEST_PASSWORD)
    create_test_transaction(
        db_session, user, amount=100.0, advance_amount=40.0, payment_method="Zzuniquepaymentmethod2d4",
        items=[{"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}],
    )
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_dashdistrib", TEST_PASSWORD)
    today = date_cls.today().isoformat()

    resp = client.get(f"/caisse/dashboard/caisse/payment_distribution?date_from={today}&date_to={today}", headers=headers)

    assert resp.status_code == 200
    distribution = {item["method"]: item["total"] for item in resp.json()["distribution"]}
    assert distribution.get("Zzuniquepaymentmethod2d4") == 40.0
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_caisse.py -v
```

Attendu : 30 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_caisse.py
git commit -m "test: KPIs de caisse (chantier 2d-4)

7 tests : daily_total/total/total_payments (comparaison avant/apres,
donnees reelles preexistantes dans la base partagee), documentation
de l'incoherence de filtre implicite status='active' sur
total_remaining_due, KPIs de tableau de bord bornes par date
(valeurs exactes fiables : kpis, unpaid, payment_distribution).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 8: Tests facture PDF (`tests/test_caisse.py`, partie 7)

**Files:**
- Modify: `tests/test_caisse.py`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichier de Task 2-7
- Produces: rien — complété par la tâche suivante

- [ ] **Step 1: Ajouter les 2 tests à la fin de `tests/test_caisse.py`**

```python
def test_download_invoice_pdf_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_pdf", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_pdf", TEST_PASSWORD)

    resp = client.get(f"/caisse/{tx.transaction_id}/invoice/download", headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 1000


def test_download_invoice_pdf_not_found(db_session, api_client):
    create_test_user(db_session, "test_caisse_secretaire_pdf404", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_pdf404", TEST_PASSWORD)

    resp = client.get("/caisse/999999999/invoice/download", headers=headers)

    assert resp.status_code == 404
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_caisse.py -v
```

Attendu : 32 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_caisse.py
git commit -m "test: telechargement de facture PDF caisse (chantier 2d-4)

2 tests sur GET /caisse/{id}/invoice/download : succes (Content-Type
application/pdf, corps substantiel) + 404 sur id inexistant. Le
contenu textuel de la facture n'est pas verifie (hors perimetre du
plan), seule la presence d'octets PDF valides l'est.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 9: Tests retrait (`tests/test_retrait.py`)

**Files:**
- Create: `tests/test_retrait.py`

**Interfaces:**
- Consumes: `db_session`, `api_client`, `create_test_user`, `create_test_retrait`, `login`, `auth_headers` (tous déjà dans `tests/conftest.py`)
- Produces: rien — dernier fichier de test du chantier

- [ ] **Step 1: Écrire les 11 tests**

```python
# tests/test_retrait.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.retrait import retrait_endpoints
from tests.conftest import create_test_user, create_test_retrait, login, auth_headers

TEST_PASSWORD = "Correct123!"


def test_create_retrait_success(db_session, api_client):
    user = create_test_user(db_session, "test_retrait_secretaire_create", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_create", TEST_PASSWORD)

    resp = client.post(
        "/retrait/",
        json={"amount": 60.0, "justification": "Achat fournitures bureau", "category": "Fournitures", "payment_method": "Especes"},
        headers=headers,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["amount"] == 60.0
    assert body["justification"] == "Achat fournitures bureau"
    assert body["status"] == "active"
    assert body["retrait_id"]


def test_create_retrait_negative_amount_returns_422(db_session, api_client):
    create_test_user(db_session, "test_retrait_secretaire_negative", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_negative", TEST_PASSWORD)

    resp = client.post("/retrait/", json={"amount": -5.0, "justification": "x"}, headers=headers)

    assert resp.status_code == 422


def test_get_retrait_success(db_session, api_client):
    user = create_test_user(db_session, "test_retrait_secretaire_get", "secretaire", password=TEST_PASSWORD)
    retrait = create_test_retrait(db_session, user, amount=42.0, justification="Retrait specifique")
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_get", TEST_PASSWORD)

    resp = client.get(f"/retrait/{retrait.retrait_id}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["retrait_id"] == retrait.retrait_id
    assert resp.json()["amount"] == 42.0


def test_get_retrait_not_found(db_session, api_client):
    create_test_user(db_session, "test_retrait_secretaire_get404", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_get404", TEST_PASSWORD)

    resp = client.get("/retrait/999999999", headers=headers)

    assert resp.status_code == 404


def test_list_retraits(db_session, api_client):
    user = create_test_user(db_session, "test_retrait_secretaire_list", "secretaire", password=TEST_PASSWORD)
    retrait = create_test_retrait(db_session, user, justification="Zzuniquelistjustif2d4")
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_list", TEST_PASSWORD)

    resp = client.get("/retrait/?per_page=200", headers=headers)

    assert resp.status_code == 200
    ids = [r["retrait_id"] for r in resp.json()["data"]]
    assert retrait.retrait_id in ids


def test_search_retraits_by_term(db_session, api_client):
    user = create_test_user(db_session, "test_retrait_secretaire_search", "secretaire", password=TEST_PASSWORD)
    create_test_retrait(db_session, user, justification="Zzuniquesearchjustif2d4")
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_search", TEST_PASSWORD)

    resp = client.get("/retrait/search?term=Zzuniquesearchjustif2d4", headers=headers)

    assert resp.status_code == 200
    justifications = [r["justification"] for r in resp.json()["data"]]
    assert "Zzuniquesearchjustif2d4" in justifications


def test_total_retraits(db_session, api_client):
    user = create_test_user(db_session, "test_retrait_secretaire_total", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_total", TEST_PASSWORD)

    before = client.get("/retrait/total", headers=headers).json()
    create_test_retrait(db_session, user, amount=33.0)
    after = client.get("/retrait/total", headers=headers).json()

    assert after == before + 33.0


def test_cancel_retrait_success(db_session, api_client):
    user = create_test_user(db_session, "test_retrait_secretaire_cancel", "secretaire", password=TEST_PASSWORD)
    retrait = create_test_retrait(db_session, user)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_cancel", TEST_PASSWORD)

    resp = client.post(
        f"/retrait/{retrait.retrait_id}/cancel",
        json={"cancel_justification": "Erreur de saisie"},
        headers=headers,
    )

    assert resp.status_code == 200
    assert resp.json()["detail"] == "Retrait annulé avec succès"

    get_resp = client.get(f"/retrait/{retrait.retrait_id}", headers=headers)
    assert get_resp.json()["status"] == "cancelled"


def test_cancel_retrait_already_cancelled_returns_400(db_session, api_client):
    """
    Contraste avec test_cancel_transaction_already_cancelled_is_idempotent
    (tests/test_caisse.py) : ici, annuler un retrait deja annule est
    explicitement refuse (400), alors qu'annuler une transaction caisse
    deja annulee reussit silencieusement (200) - incoherence de
    comportement entre les deux modules.
    """
    user = create_test_user(db_session, "test_retrait_secretaire_doublecancel", "secretaire", password=TEST_PASSWORD)
    retrait = create_test_retrait(db_session, user)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_doublecancel", TEST_PASSWORD)

    first = client.post(f"/retrait/{retrait.retrait_id}/cancel", json={"cancel_justification": "Premiere annulation"}, headers=headers)
    assert first.status_code == 200

    second = client.post(f"/retrait/{retrait.retrait_id}/cancel", json={"cancel_justification": "Deuxieme annulation"}, headers=headers)
    assert second.status_code == 400
    assert "déjà annulé" in second.json()["detail"]


def test_retrait_forbidden_for_medecin(db_session, api_client):
    create_test_user(db_session, "test_retrait_medecin", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_medecin", TEST_PASSWORD)

    resp = client.get("/retrait/", headers=headers)

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Accès refusé : rôle utilisateur insuffisant"


def test_retrait_unauthenticated_returns_401(db_session, api_client):
    client = api_client(auth_endpoints, retrait_endpoints)

    resp = client.get("/retrait/")

    assert resp.status_code == 401
```

- [ ] **Step 2: Lancer les tests**

```bash
pytest tests/test_retrait.py -v
```

Attendu : 11 tests, tous PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_retrait.py
git commit -m "test: module retrait de caisse (chantier 2d-4)

11 tests sur tout le routeur /retrait : creation (succes + 422 montant
negatif), lecture (succes + 404), liste, recherche, total (comparaison
avant/apres), annulation (succes + refus explicite sur double
annulation, contraste documente avec l'idempotence silencieuse de
/caisse/{id}/cancel), RBAC (403 medecin, 401 non-authentifie).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 10: Vérification finale, registre

**Files:**
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md`

**Interfaces:**
- Consumes: infrastructure de Task 1, fichiers de Task 2-9
- Produces: rien — dernière tâche du chantier

- [ ] **Step 1: Suite de tests complète**

```bash
pytest tests/test_caisse.py tests/test_retrait.py -v
```

Attendu : 43 tests, tous PASS (32 dans `test_caisse.py`, 11 dans `test_retrait.py`).

```bash
pytest tests/ -v
```

Attendu : aucune régression sur les tests déjà verts avant ce chantier. Les échecs déjà connus et attribués au travail en cours de l'utilisateur restent inchangés (`test_patient_repo.py`, `test_prescription_repo.py`, éventuellement `test_patients.py::test_update_patient_flag_protection_prevents_any_change` et des tests de `test_prescriptions.py` documentant `E1`/`E5`/`E6` selon l'état du travail en cours au moment de l'exécution — voir `SUIVI-AVANCEMENT.md` pour le détail à jour). **Ce chantier n'ajoute que `tests/test_caisse.py` et `tests/test_retrait.py`, il ne modifie ni `controller/caisse_controller.py`, ni `repositories/caisse_repo.py`, ni `api_backend/backend_app/routes/caisse/mapping.py`** (les trois fichiers en travail non commité) : aucune nouvelle régression n'est attendue de ce chantier lui-même.

- [ ] **Step 2: Confirmer l'absence de donnée résiduelle**

```bash
psql -U postgres -h localhost -d AH2 -c "SELECT COUNT(*) FROM caisse WHERE transaction_type LIKE '%2d4%' OR payment_method LIKE '%2d4%'; SELECT COUNT(*) FROM caisse_retrait WHERE justification LIKE '%2d4%';"
```

Attendu : `0` sur les deux requêtes — tous les tests s'exécutent dans la transaction annulée de `db_session`.

- [ ] **Step 3: Mettre à jour `docs/superpowers/SUIVI-AVANCEMENT.md`**

Ajouter la section de détail suivante dans "Détail des chantiers terminés", juste après la section "### Chantier 2d-3 — Tests d'intégration prescriptions" existante :

```markdown
### Chantier 2d-4 — Tests d'intégration caisse et retrait
Spec : `2026-08-12-chantier-2d4-tests-caisse-design.md` · Plan : `2026-08-12-chantier-2d4-tests-caisse.md`
Quatrième sous-chantier métier, construit sur 2d-0/2d-1/2d-2/2d-3. Exécuté via subagent-driven-development, worktree isolé (`.claude/worktrees/chantier-2d4-tests-caisse`). 43 tests neufs : 32 dans `tests/test_caisse.py` (routeur `/caisse`, 17 endpoints), 11 dans `tests/test_retrait.py` (routeur `/retrait`, 6 endpoints). RBAC identique sur les deux routeurs (`secretaire`/`admin`, différent de prescriptions) :
- Caisse — création : succès + documentation du bug `F1` (calcul erroné de `amount_due`/`amount_paid` dans `mapping.py`) + validations métier (champ requis, incohérence montant/lignes, référence de consultation invalide) + RBAC.
- Caisse — lecture : succès + 404, liste/recherche filtrée (terme, statut, plage de dates), liste par patient.
- Caisse — mise à jour : succès, refus après annulation, 400 (pas 404) sur id inexistant.
- Caisse — suppression : succès + documentation du bug `F2` (204 au lieu de 404 sur un id inexistant, même motif que `E2` sur prescriptions).
- Caisse — paiement/solde/annulation : succès + documentation du corps de réponse vide sur le paiement échelonné + documentation de l'idempotence silencieuse sur double annulation.
- Caisse — KPIs : `daily_total`/`total`/`total_payments` (comparaison avant/après, données réelles préexistantes) + documentation de l'incohérence de filtre implicite sur `total_remaining_due` + KPIs de tableau de bord bornés par date (valeurs exactes fiables, calcul correct — contrairement au bug `F1`).
- Caisse — facture PDF : téléchargement réel (10+ Ko constatés), Content-Type correct, 404 sur id inexistant.
- Retrait — couverture complète : création (succès + 422 montant négatif), lecture, liste, recherche, total, annulation (refus explicite sur double annulation — contraste documenté avec l'idempotence de `/caisse/{id}/cancel`), RBAC.

**Correction empirique par rapport à la spec** : le "Bug 1" anticipé (notification Celery avec `tx.id` au lieu de `tx.transaction_id`) ne se manifeste pas sur `HEAD` — `tasks/finance_tasks.py` n'existe que dans le travail en cours non commité de l'utilisateur, l'import échoue silencieusement sur `HEAD` et tout le bloc de notification est court-circuité. Aucun test ne le documente ; il redeviendra pertinent si ce fichier est un jour commité.

**Fichiers en travail non commité** (jamais touchés par ce chantier) : `api_backend/backend_app/routes/caisse/mapping.py`, `controller/caisse_controller.py`, `repositories/caisse_repo.py`. Le module `retrait` n'est pas touché par le travail en cours.
```

Puis, une nouvelle catégorie de registre **F** après la catégorie E existante (dans "Registre des découvertes non traitées") :

```markdown
### F — Découvertes du chantier 2d-4 (caisse, retrait), non bloquées par le travail en cours

Comme la catégorie E, ces défauts sont dans du code déjà committé et ne
dépendent d'aucun fichier en travail en cours côté utilisateur —
corrigeables dès qu'un chantier dédié leur est consacré.

| # | Découverte | Fichier | Gravité |
|---|---|---|---|
| F1 | `normalize_caisse_data()` calcule `amount_due = amount + advance_amount` (devrait être `amount - advance_amount`) et `amount_paid = amount` (devrait être `advance_amount`). Confirmé avec `amount=100, advance_amount=30` : `amount_due=130` (attendu 70), `amount_paid=100` (attendu 30). Indépendant des KPIs de tableau de bord (`get_caisse_kpis`), qui calculent correctement. Tout client (frontend) affichant ces deux champs par transaction affiche des montants faux. | `api_backend/backend_app/routes/caisse/mapping.py` | Élevée — chiffres financiers visibles par transaction, faux dans les deux sens |
| F2 | `DELETE /caisse/{id}` sur un id inexistant renvoie 204 au lieu de 404 — l'endpoint ne vérifie jamais la valeur de retour de `delete_transaction()`, qui échoue silencieusement (`None`, pas d'exception) sur un id absent. Même motif que `E2` sur prescriptions. | `api_backend/backend_app/routes/caisse/caisse_endpoints.py` | Faible — comportement silencieux, pas de perte de données |
| F3 | `POST /caisse/{id}/payment` ne déclare pas de `response_model` — renvoie 201 avec un corps vide `{}` (l'objet ORM `PaiementEchelonne` retourné n'est pas sérialisable sans schéma). Le client doit refaire un `GET` pour voir l'état à jour. | `api_backend/backend_app/routes/caisse/caisse_endpoints.py` | Faible — pas de perte de données, juste un round-trip supplémentaire nécessaire côté client |
| F4 | `get_total_remaining_due()` filtre implicitement `status='active'` même sans paramètre `status` explicite, contrairement à `get_total_transactions()`/`get_total_payments()` qui ne filtrent par statut que si demandé. Incohérence d'API entre trois endpoints de la même famille (`/caisse/total`, `/caisse/total_payments`, `/caisse/total_remaining_due`). | `repositories/caisse_repo.py` | Moyenne — surprend un appelant qui s'attend à un comportement uniforme entre les trois endpoints |
| F5 | Annuler une transaction caisse déjà annulée réussit silencieusement (200, `cancel_transaction()` fait `if tx.status == 'cancelled': return tx` sans erreur), alors qu'annuler un retrait déjà annulé est explicitement refusé (400 `"Ce retrait est déjà annulé."`). Incohérence de comportement entre deux modules très proches du même domaine (caisse). | `repositories/caisse_repo.py` vs `repositories/caisse_retrait_repo.py` | Faible — incohérence de contrat API, pas de perte de données |

**Note (pas un bug)** : `tasks/finance_tasks.py` — référencé par `controller/caisse_controller.py` mais absent de `HEAD` (uniquement dans le travail en cours de l'utilisateur) — n'a jamais été exercé par ce chantier. Si ce fichier est un jour commité, revérifier `create_transaction` : l'appel `task_process_payment_notification.delay(transaction_id=tx.id, ...)` utilise `tx.id`, qui n'existe pas sur le modèle `Caisse` (seul `transaction_id` existe) — probable `AttributeError` avalée silencieusement, à re-tester à ce moment-là.
```

- [ ] **Step 4: Commit de la mise à jour du suivi**

```bash
git add docs/superpowers/SUIVI-AVANCEMENT.md
git commit -m "docs: cloture du chantier 2d-4 dans le suivi d'avancement

43 tests sur les routeurs /caisse (32, 17 endpoints) et /retrait (11,
6 endpoints). Nouvelle categorie de registre F (5 items) - comme E,
ces defauts sont dans du code deja committe, pas bloques par le
travail en cours : F1 (calcul errone de amount_due/amount_paid dans
mapping.py, la plus grave - chiffres financiers faux par transaction),
F2 (suppression idempotente silencieuse, meme motif que E2), F3
(corps de reponse vide sur le paiement echelonne), F4 (filtre de
statut implicite incoherent entre trois endpoints de total), F5
(annulation idempotente sur caisse vs refusee sur retrait).

Correction empirique par rapport a la spec : le bug Celery
initialement anticipe (tx.id) ne se manifeste pas sur HEAD, le fichier
tasks/finance_tasks.py n'existe que dans le travail en cours - note
pour re-verification future plutot qu'un test.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Récapitulatif**

Chantier 2d-4 terminé : 43 tests neufs (`tests/test_caisse.py`, `tests/test_retrait.py`), aucune régression, 5 nouveaux items de registre (F1-F5) dont un (F1) touchant des chiffres financiers visibles par l'utilisateur final. Prêt pour `superpowers:finishing-a-development-branch`.
