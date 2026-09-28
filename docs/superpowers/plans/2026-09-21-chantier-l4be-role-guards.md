# Chantier L4b-e Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close registre `L4a`-`L4e` (role-guard mismatches between UI and server) plus the role-guard-themed technical debt parked by chantiers 6, 7a and 7c.

**Architecture:** Backend-first (three routers gain a missing role, one router gains a narrower per-route guard, one dead stored-procedure overload is dropped, one dead code block is removed), then frontend (a single case-insensitive role-comparison helper replaces 7 duplicated ad-hoc checks, then small router/menu adjustments).

**Tech Stack:** FastAPI + SQLAlchemy + PostgreSQL (Alembic migrations), Vue 3 (`<script setup>` and Options-API Pinia stores), vue-router, vue-i18n.

**Spec:** `docs/superpowers/specs/2026-09-21-chantier-l4be-role-guards-design.md`

## Global Constraints

- No account is created for `ToxicoManager` in this plan — the role becomes reachable end-to-end (it already is, via `UserModal.vue`); the user creates the real account themselves after delivery.
- The secretariat-side half of `L4d` (appointments access) is explicitly OUT OF SCOPE — user decision 2026-09-21: appointments are medical-patient-scoped, the absence of a secretariat menu entry is correct behavior, not a bug.
- The migration in Task 3 touches the real local AH2 database — apply it only after the user explicitly confirms at execution time (same rule as every prior chantier's migrations).
- No frontend test framework exists in this repo — frontend verification is `npm run build` plus a manual QA checklist at the end of the plan.
- `role_required(...)` already normalizes case via `normalize_role_name()` (`api_backend/backend_app/security/role_map.py`) — do not add any new case-handling logic to it, just pass role names as arguments like every other call site in this codebase already does.

---

## Task 1: Backend — L4a, ToxicoManager recognized by the 3 routers that exclude it

**Files:**
- Modify: `api_backend/backend_app/routes/admin/users_endpoint.py:71`
- Modify: `api_backend/backend_app/routes/audit/audit_endpoint.py:20`
- Modify: `api_backend/backend_app/routes/patients/patients_endpoints.py:24`
- Test: `tests/test_users_pagination.py`
- Test: `tests/test_audit_endpoint.py` (new)
- Test: `tests/test_patients.py`

**Interfaces:**
- Consumes: `role_required(*allowed_roles)` (`api_backend/backend_app/routes/auth/auth_endpoints.py:194`) — unchanged signature, just called with one more argument at 3 call sites.
- Produces: none consumed by later tasks in this plan (independent fix).

- [ ] **Step 1: Write a failing test for `/users/` recognizing ToxicoManager**

Add to `tests/test_users_pagination.py`:

```python
def test_toxicomanager_can_list_users(db_session, api_client):
    """Registre L4a : ToxicoManager est deja normalise par role_required()
    (voir api_backend/backend_app/security/role_map.py) mais le routeur
    /users ne le listait pas encore parmi les roles autorises."""
    create_test_user(db_session, "l4a_toxicomanager_users", "ToxicoManager")
    db_session.flush()

    client = api_client(users_endpoint, auth_endpoints)
    headers = auth_headers(client, "l4a_toxicomanager_users", "TestPass123!")

    reponse = client.get("/users/?page=1&per_page=1", headers=headers)

    assert reponse.status_code == 200
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_users_pagination.py::test_toxicomanager_can_list_users -v`
Expected: FAIL with 403 (`"Accès refusé : rôle utilisateur insuffisant"`).

- [ ] **Step 3: Fix `users_endpoint.py`**

In `api_backend/backend_app/routes/admin/users_endpoint.py`, change the `list_users` decorator from:

```python
@router.get("/", response_model=UserListResponse, dependencies=[Depends(role_required("admin", "manager"))])
```

to:

```python
@router.get("/", response_model=UserListResponse, dependencies=[Depends(role_required("admin", "manager", "ToxicoManager"))])
```

- [ ] **Step 4: Run the test again to verify it passes**

Run: `python -m pytest tests/test_users_pagination.py::test_toxicomanager_can_list_users -v`
Expected: PASS

- [ ] **Step 5: Write a failing test for `/audit/access` recognizing ToxicoManager**

Create `tests/test_audit_endpoint.py`:

```python
# tests/test_audit_endpoint.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.audit import audit_endpoint
from tests.conftest import create_test_user, login, auth_headers

TEST_PASSWORD = "Correct123!"


def test_toxicomanager_can_list_audit_access(db_session, api_client):
    """Registre L4a : /audit n'autorisait que admin/manager, alors que
    ToxicoManager a deja une entree de menu vers les logs (MainLayout.vue)
    et que role_required() reconnait deja ce role ailleurs (labo, toxico)."""
    create_test_user(db_session, "l4a_toxicomanager_audit", "ToxicoManager", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, audit_endpoint)
    headers = auth_headers(client, "l4a_toxicomanager_audit", TEST_PASSWORD)

    resp = client.get("/audit/access?page=1&per_page=1", headers=headers)

    assert resp.status_code == 200


def test_medecin_still_forbidden_from_audit(db_session, api_client):
    """Garde-fou : l'elargissement a ToxicoManager ne doit pas elargir
    /audit a d'autres roles non prevus."""
    create_test_user(db_session, "l4a_medecin_audit", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, audit_endpoint)
    headers = auth_headers(client, "l4a_medecin_audit", TEST_PASSWORD)

    resp = client.get("/audit/access?page=1&per_page=1", headers=headers)

    assert resp.status_code == 403
```

- [ ] **Step 6: Run both to verify the first fails and the second already passes**

Run: `python -m pytest tests/test_audit_endpoint.py -v`
Expected: `test_toxicomanager_can_list_audit_access` FAILS (403), `test_medecin_still_forbidden_from_audit` PASSES (already 403 today).

- [ ] **Step 7: Fix `audit_endpoint.py`**

In `api_backend/backend_app/routes/audit/audit_endpoint.py`, change the router declaration from:

```python
router = APIRouter(
    prefix="/audit",
    tags=["Audit"],
    dependencies=[Depends(role_required("admin", "manager"))]
)
```

to:

```python
router = APIRouter(
    prefix="/audit",
    tags=["Audit"],
    dependencies=[Depends(role_required("admin", "manager", "ToxicoManager"))]
)
```

- [ ] **Step 8: Run both tests again to verify they pass**

Run: `python -m pytest tests/test_audit_endpoint.py -v`
Expected: both PASS

- [ ] **Step 9: Write a failing test for `/patients/` recognizing ToxicoManager**

Add to `tests/test_patients.py`:

```python
def test_toxicomanager_can_search_patients(db_session, api_client):
    """Registre L4a : /patients autorisait deja assistant/secretaire/medecin/
    nurse/admin/manager mais pas ToxicoManager, alors que MainLayout.vue lui
    donne deja une entree de menu vers /dashboard/patients."""
    create_test_user(db_session, "l4a_toxicomanager_patients", "ToxicoManager", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "l4a_toxicomanager_patients", TEST_PASSWORD)

    resp = client.get("/patients/", headers=headers)

    assert resp.status_code == 200
```

- [ ] **Step 10: Run it to verify it fails**

Run: `python -m pytest tests/test_patients.py::test_toxicomanager_can_search_patients -v`
Expected: FAIL with 403.

- [ ] **Step 11: Fix `patients_endpoints.py`**

In `api_backend/backend_app/routes/patients/patients_endpoints.py`, change the router declaration from:

```python
router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
    # 🟢 "assistant" ajoute (chantier 6, tache 3) : l'assistant qui admet un
    # patient en toxico doit pouvoir verifier/rechercher un patient existant
    # via /patients (necessaire aussi a la recherche frontend de la tache 4).
    dependencies=[Depends(role_required("medecin", "nurse","secretaire","admin","manager","assistant"))]
)
```

to:

```python
router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
    # 🟢 "assistant" ajoute (chantier 6, tache 3) : l'assistant qui admet un
    # patient en toxico doit pouvoir verifier/rechercher un patient existant
    # via /patients (necessaire aussi a la recherche frontend de la tache 4).
    # "ToxicoManager" ajoute (chantier L4b-e, registre L4a) : MainLayout.vue
    # lui donne deja une entree de menu vers /dashboard/patients.
    dependencies=[Depends(role_required("medecin", "nurse","secretaire","admin","manager","assistant","ToxicoManager"))]
)
```

- [ ] **Step 12: Run the test again, then the whole patients test file, to verify no regression**

Run: `python -m pytest tests/test_patients.py -v`
Expected: all PASS

- [ ] **Step 13: Commit**

This project never commits without the user's fresh explicit approval — do not run `git add`/`git commit`. Leave the changes on disk.

---

## Task 2: Backend — restrict `assistant` to read/search on `/patients` (parked debt, chantier 6)

**Files:**
- Modify: `api_backend/backend_app/routes/patients/patients_endpoints.py:149,184`
- Test: `tests/test_patients.py`

**Interfaces:**
- Consumes: none (independent of Task 1 — different lines of the same file, no overlap: Task 1 touches the router-level `dependencies=[...]` on line 24, this task adds route-level `dependencies=[...]` on the `PUT`/`DELETE` decorators at lines 149/184).
- Produces: none consumed by later tasks.

- [ ] **Step 1: Write a failing test — assistant must be refused on PUT**

Add to `tests/test_patients.py`:

```python
def test_assistant_forbidden_from_update_patient(db_session, api_client):
    """Dette parquee au chantier 6 : le role 'assistant', elargi sur le
    routeur /patients entier pour permettre la recherche (necessaire a
    l'admission toxico), avait de facto acces a PUT/DELETE sur n'importe
    quel patient. La composition des dependances FastAPI est un ET logique :
    une dependance de route plus stricte, ajoutee en plus de la dependance
    de routeur, retire assistant de l'ecriture sans toucher a son acces en
    lecture (GET), toujours necessaire au flux d'admission toxico."""
    admin = create_test_user(db_session, "l4_assistant_denied_update_admin", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="Avant")
    create_test_user(db_session, "l4_assistant_denied_update", "Assistant", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "l4_assistant_denied_update", TEST_PASSWORD)

    resp = client.put(f"/patients/{patient_id}", json={"first_name": "Apres"}, headers=headers)

    assert resp.status_code == 403


def test_assistant_forbidden_from_delete_patient(db_session, api_client):
    admin = create_test_user(db_session, "l4_assistant_denied_delete_admin", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin)
    create_test_user(db_session, "l4_assistant_denied_delete", "Assistant", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "l4_assistant_denied_delete", TEST_PASSWORD)

    resp = client.delete(f"/patients/{patient_id}", headers=headers)

    assert resp.status_code == 403


def test_assistant_still_allowed_to_search_patients(db_session, api_client):
    """Garde-fou : la restriction PUT/DELETE ne doit pas toucher a GET,
    necessaire au flux d'admission toxico de l'assistant."""
    create_test_user(db_session, "l4_assistant_still_search", "Assistant", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "l4_assistant_still_search", TEST_PASSWORD)

    resp = client.get("/patients/", headers=headers)

    assert resp.status_code == 200
```

- [ ] **Step 2: Run all three to verify the first two fail and the third already passes**

Run: `python -m pytest tests/test_patients.py::test_assistant_forbidden_from_update_patient tests/test_patients.py::test_assistant_forbidden_from_delete_patient tests/test_patients.py::test_assistant_still_allowed_to_search_patients -v`
Expected: first two FAIL (200/204 instead of 403), third PASSES already.

- [ ] **Step 3: Add the stricter route-level dependency on PUT and DELETE**

In `api_backend/backend_app/routes/patients/patients_endpoints.py`, change:

```python
@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    data: PatientUpdate,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
```

to:

```python
@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    # Restreint l'ecriture par rapport a la dependance de routeur (plus
    # large, qui inclut "assistant" pour la recherche) : composition ET des
    # dependances FastAPI, l'intersection exclut "assistant" ici sans
    # toucher a son acces en lecture (registre L4, dette parquee chantier 6).
    dependencies=[Depends(role_required("medecin", "nurse", "secretaire", "admin", "manager"))],
)
def update_patient(
    patient_id: int,
    data: PatientUpdate,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
```

and change:

```python
@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: int,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
```

to:

```python
@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(role_required("medecin", "nurse", "secretaire", "admin", "manager"))],
)
def delete_patient(
    patient_id: int,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
```

- [ ] **Step 4: Run the three tests again, then the whole patients test file, to verify no regression**

Run: `python -m pytest tests/test_patients.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

No commit — see Task 1 Step 13.

---

## Task 3: Backend — drop the dead 19-param `create_medical_record` overload

**Files:**
- Create: `alembic/versions/007_drop_medrec_19param_overload.py`
- Modify: `ci/schema_only.sql` (regenerated, not hand-edited)

**Interfaces:**
- Consumes: none.
- Produces: none consumed by later tasks (independent cleanup).

- [ ] **Step 1: Write the migration**

Create `alembic/versions/007_drop_medrec_19param_overload.py`:

```python
"""drop dead 19-param create_medical_record overload (chantier L4b-e)

Revision ID: 007_drop_medrec_19param
Revises: 006_caisse_cancel_justification
Create Date: 2026-09-21 00:00:00.000000

Chantier 7c (migration 005) a etendu create_medical_record de 19 a 20
parametres (ajout de p_appointment_id) via CREATE OR REPLACE PROCEDURE.
PostgreSQL ne remplace une procedure que si l'arite est identique - un
changement d'arite cree une NOUVELLE surcharge au lieu de remplacer
l'ancienne. Les deux ont coexiste depuis (verifie par grep exhaustif :
seul repositories/medical_repo.py::create appelle cette procedure,
toujours avec 20 arguments - l'ancienne surcharge a 19 est inatteignable
mais physiquement presente en base). Parquee au chantier 7c pour
nettoyage au chantier L4b-e (registre "gardes de role" - dette technique
liee aux procedures stockees, traitee dans le meme chantier que le reste
du nettoyage de dette parquee).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_drop_medrec_19param'
down_revision: Union[str, Sequence[str], None] = '006_caisse_cancel_justification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        DROP PROCEDURE IF EXISTS public.create_medical_record(
            integer, timestamp without time zone, character varying,
            character varying, numeric, numeric, numeric, text, text, text,
            text, text, character varying, text, character varying,
            integer, character varying, integer, character varying
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        CREATE OR REPLACE PROCEDURE public.create_medical_record(
            IN p_patient_id integer,
            IN p_consultation_date timestamp without time zone,
            IN p_marital_status character varying,
            IN p_bp character varying,
            IN p_temperature numeric,
            IN p_weight numeric,
            IN p_height numeric,
            IN p_medical_history text,
            IN p_allergies text,
            IN p_symptoms text,
            IN p_diagnosis text,
            IN p_treatment text,
            IN p_severity character varying,
            IN p_notes text,
            IN p_motif_code character varying,
            IN p_created_by integer DEFAULT NULL::integer,
            IN p_created_by_name character varying DEFAULT NULL::character varying,
            IN p_last_updated_by integer DEFAULT NULL::integer,
            IN p_last_updated_by_name character varying DEFAULT NULL::character varying
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO public.medical_records (
                patient_id, consultation_date, marital_status, bp, temperature,
                weight, height, medical_history, allergies, symptoms, diagnosis,
                treatment, severity, notes, motif_code, created_by, created_by_name,
                last_updated_by, last_updated_by_name
            ) VALUES (
                p_patient_id, p_consultation_date, p_marital_status, p_bp, p_temperature,
                p_weight, p_height, p_medical_history, p_allergies, p_symptoms, p_diagnosis,
                p_treatment, p_severity, p_notes, p_motif_code, p_created_by, p_created_by_name,
                p_last_updated_by, p_last_updated_by_name
            );
        END;
        $$;
    """)
```

(`revision` string is 24 characters — well under the 32-char `alembic_version.version_num` limit discovered in chantier 7c; `down_revision` matches chantier 7b's migration 006 exactly — verify this against the real `revision =` line in `alembic/versions/006_caisse_cancel_justification.py` before writing the file, don't trust this plan's memory of it.)

- [ ] **Step 2: Ask the user for explicit confirmation before applying the migration to the real local AH2 database**

This drops a stored procedure in a production-shaped local database — do not run `alembic upgrade head` without the user's explicit go-ahead at this point in execution.

- [ ] **Step 3: Apply the migration (only after confirmation)**

Run: `alembic upgrade head`
Expected: migration `007_drop_medrec_19param` applied, no errors.

- [ ] **Step 4: Verify the 19-param overload is gone and the 20-param one still exists**

Run a quick `psql` check that `pg_get_function_arguments` for `create_medical_record` now returns exactly one row (20 params, including `p_appointment_id`), not two.

- [ ] **Step 5: Regenerate `ci/schema_only.sql`**

Run: `pg_dump --schema-only --no-owner --no-privileges -h localhost -p 5432 -U postgres -d AH2 > ci/schema_only.sql`

Diff the result to confirm the only functional change is the removal of the 19-param `create_medical_record` overload (the 20-param one stays; other unrelated diff lines from other uncommitted chantiers' work are expected and not a concern — this project never commits, so `ci/schema_only.sql` reflects live DB state across every chantier run so far, not just this one).

- [ ] **Step 6: Run the existing medical-records test suite to confirm no regression**

Run: `python -m pytest tests/test_medical_records_appointment_link.py -v`
Expected: all PASS (this suite exercises the 20-param overload exclusively — confirms it's untouched).

- [ ] **Step 7: Commit**

No commit — see Task 1 Step 13.

---

## Task 4: Backend — remove the twin dead-code block in `create_patient`

**Files:**
- Modify: `controller/patient_controller.py:78-104`
- Test: `tests/test_patients.py`

**Interfaces:**
- Consumes: none.
- Produces: none consumed by later tasks.

- [ ] **Step 1: Write a test proving the dead branches never fire (documents the fix, not a regression test for removed behavior)**

Add to `tests/test_patients.py`:

```python
def test_create_patient_by_secretaire_does_not_force_is_spiritual(db_session, api_client):
    """Chantier L4b-e : le bloc mort dans PatientController.create_patient
    forcait is_spiritual=True pour un createur 'app_secretaire'/'secretaire'
    quand le champ n'etait pas fourni. PatientCreate.is_spiritual defaut a
    False (jamais None, voir patients_schemas.py) : la condition
    'data.get('is_spiritual') is None' n'a jamais ete vraie, ce bloc etait
    deja inerte avant sa suppression. Ce test prouve juste qu'une secretaire
    peut creer un patient et que is_spiritual reste False par defaut,
    inchange par sa suppression."""
    create_test_user(db_session, "l4_secretaire_create_patient", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "l4_secretaire_create_patient", TEST_PASSWORD)

    payload = {"first_name": "Test", "last_name": "Inerte", "birth_date": "1990-01-01"}
    resp = client.post("/patients/", json=payload, headers=headers)

    assert resp.status_code == 201
    assert resp.json()["is_spiritual"] is False
```

- [ ] **Step 2: Run it to verify it already passes (confirms the branch is dead before touching it)**

Run: `python -m pytest tests/test_patients.py::test_create_patient_by_secretaire_does_not_force_is_spiritual -v`
Expected: PASS (proves the block is inert on `HEAD`, before removal — this is the evidence that Step 3 is safe).

- [ ] **Step 3: Remove the dead block**

In `controller/patient_controller.py`, change:

```python
    def create_patient(self, data: dict) -> tuple[int, str]:
        required = ['first_name', 'last_name', 'birth_date']
        if any(not data.get(f) for f in required):
            raise ValueError("Champs obligatoires manquants")
        
        user_roles = self._get_user_roles_set()

        if 'app_secretaire' in user_roles or 'secretaire' in user_roles:
            if data.get('is_spiritual') is None: data['is_spiritual'] = True

        if 'app_medical' in user_roles or 'medecin' in user_roles or 'nurse' in user_roles:
            if data.get('is_clinical') is None: data['is_clinical'] = True

        result = self.repo.create_patient(data, self.user)
```

to:

```python
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
```

- [ ] **Step 4: Run the test again plus the whole patients test file to verify no regression**

Run: `python -m pytest tests/test_patients.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

No commit — see Task 1 Step 13.

---

## Task 5: Frontend — `authStore.hasRole()` and its 6 call sites (L4e)

**Files:**
- Modify: `ah2-admin-web/src/stores/auth.js`
- Modify: `ah2-admin-web/src/components/layout/MainLayout.vue:221`
- Modify: `ah2-admin-web/src/views/modules/toxico/ToxicoList.vue:318,323`
- Modify: `ah2-admin-web/src/views/modules/patients/PatientList.vue:190`
- Modify: `ah2-admin-web/src/views/modules/patients/PatientDetailView.vue:184`
- Modify: `ah2-admin-web/src/views/modules/labo/LabConfig.vue:63`
- Modify: `ah2-admin-web/src/views/modules/labo/LabLayout.vue:66`

**Interfaces:**
- Consumes: none.
- Produces: `authStore.hasRole(allowedRoles: string[]): boolean` — a case-insensitive membership check, same semantics as `[...].includes(authStore.userRole)` today, just robust to a casing mismatch between the array literal and the real DB `role_name`. Not consumed by any later task in this plan (Task 6 does not need it), but establishes the pattern any future role-gated UI code should follow.

- [ ] **Step 1: Add the `hasRole` getter**

In `ah2-admin-web/src/stores/auth.js`, this store uses the Options API (`state`/`getters`/`actions`), not `<script setup>` — add a new getter inside the existing `getters: { ... }` block, right after `isToxicoTeam`:

```javascript
    isToxicoTeam: (state) => {
        const role = state.user?.application_role?.role_name || 'Guest';
        return ['admin', 'ToxicoManager', 'Psychologist', 'Assistant'].includes(role);
    },

    // Comparaison de role insensible a la casse (registre L4e) - meme
    // logique que router/index.js:386-389, qui normalise deja userRole et
    // la liste autorisee avant de comparer. Les 7 endroits qui comparaient
    // authStore.userRole directement (sans normalisation) sont fragiles au
    // moindre ecart de casse en base ; ce getter est le point de verite
    // unique a utiliser desormais pour toute nouvelle garde de role.
    hasRole(state) {
        return (allowedRoles) => {
            const role = (this.userRole || '').toLowerCase();
            return (allowedRoles || []).some((r) => (r || '').toLowerCase() === role);
        };
    }
```

- [ ] **Step 2: Replace `MainLayout.vue:221`**

Change:

```javascript
        return item.roles.includes(userRole);
```

to:

```javascript
        return authStore.hasRole(item.roles);
```

(the `filteredMenu` computed already destructures `const userRole = authStore.userRole;` at its top — that local variable becomes unused by this change; remove that line too, since the surrounding `if (authStore.isAdmin || userRole === ROLES.ADMIN)` check right above still needs a role comparison — replace it with `authStore.hasRole([ROLES.ADMIN])` instead of removing it, so the whole computed reads:)

```javascript
const filteredMenu = computed(() => {
    // Si ADMIN, on retourne tout (Super User)
    if (authStore.isAdmin || authStore.hasRole([ROLES.ADMIN])) {
        return menuItems;
    }

    // Sinon, on filtre selon le tableau 'roles' de chaque item
    return menuItems.filter(item => {
        if (!item.roles) return false;
        // La condition magique : est-ce que mon rôle est dans la liste autorisée ?
        return authStore.hasRole(item.roles);
    });
});
```

- [ ] **Step 3: Replace `ToxicoList.vue:318,323`**

Change:

```javascript
const canAdmitPatient = computed(() => {
    // Admin, Manager et Assistant peuvent créer une admission
    return ['admin', 'ToxicoManager', 'Assistant'].includes(authStore.userRole);
});

const canDischargePatient = computed(() => {
    // Admin et Manager peuvent faire une sortie
    return ['admin', 'ToxicoManager'].includes(authStore.userRole);
});
```

to:

```javascript
const canAdmitPatient = computed(() => {
    // Admin, Manager et Assistant peuvent créer une admission
    return authStore.hasRole(['admin', 'ToxicoManager', 'Assistant']);
});

const canDischargePatient = computed(() => {
    // Admin et Manager peuvent faire une sortie
    return authStore.hasRole(['admin', 'ToxicoManager']);
});
```

- [ ] **Step 4: Replace `PatientList.vue:190`**

Change:

```javascript
const canManagePatients = computed(() =>
    ['medecin', 'nurse', 'secretaire', 'admin', 'manager', 'Assistant'].includes(authStore.userRole)
);
```

to:

```javascript
const canManagePatients = computed(() =>
    authStore.hasRole(['medecin', 'nurse', 'secretaire', 'admin', 'manager', 'Assistant'])
);
```

- [ ] **Step 5: Replace `PatientDetailView.vue:184`**

Change:

```javascript
const canCreateConsultation = computed(() => ['medecin', 'nurse'].includes(authStore.userRole));
```

to:

```javascript
const canCreateConsultation = computed(() => authStore.hasRole(['medecin', 'nurse']));
```

- [ ] **Step 6: Replace `LabConfig.vue:63`**

Change:

```javascript
const isAdmin = computed(() => {
    return ['admin', 'manager'].includes(authStore.userRole);
});
```

to:

```javascript
const isAdmin = computed(() => {
    return authStore.hasRole(['admin', 'manager']);
});
```

- [ ] **Step 7: Replace `LabLayout.vue:66`**

Change:

```javascript
const canConfigure = computed(() => ['admin', 'manager', 'biologiste'].includes(authStore.userRole));
```

to:

```javascript
const canConfigure = computed(() => authStore.hasRole(['admin', 'manager', 'biologiste']));
```

- [ ] **Step 8: Verify the build succeeds**

Run: `cd ah2-admin-web && npm run build`
Expected: build succeeds, no unused-variable errors (confirm the `userRole` local variable removed from `MainLayout.vue`'s `filteredMenu` in Step 2 isn't referenced anywhere else in that computed).

- [ ] **Step 9: Commit**

No commit — see Task 1 Step 13.

---

## Task 6: Frontend — router and menu adjustments (L4b, L4c, L4d)

**Files:**
- Modify: `ah2-admin-web/src/router/index.js`
- Modify: `ah2-admin-web/src/components/layout/MainLayout.vue`
- Modify: `ah2-admin-web/src/components/layout/MedicalLayout.vue`

**Interfaces:**
- Consumes: none (independent of Task 5 — different lines/concerns in the shared files: Task 5 touched `filteredMenu`'s comparison logic in `MainLayout.vue`, this task touches `menuItems`' role-list content and a separate route's `meta.roles`).
- Produces: none consumed by later tasks — last task of this plan.

- [ ] **Step 1: L4b — add `nurse` to `lab-history`**

In `ah2-admin-web/src/router/index.js`, change:

```javascript
            {
                path: 'history',
                name: 'lab-history',
                component: () => import('@/views/modules/labo/LabHistory.vue'),
                meta: { requiresAuth: true, roles: ['admin', 'laborantin', 'ToxicoManager', 'medecin'] }
            },
```

to:

```javascript
            {
                path: 'history',
                name: 'lab-history',
                component: () => import('@/views/modules/labo/LabHistory.vue'),
                meta: { requiresAuth: true, roles: ['admin', 'laborantin', 'ToxicoManager', 'medecin', 'nurse'] }
            },
```

- [ ] **Step 2: L4c — remove `Assistant` from `SystemConfig`, in both the menu and the route guard**

In `ah2-admin-web/src/components/layout/MainLayout.vue`, change:

```javascript
  {
    path: '/dashboard/configuration',
    labelKey: 'config.title',
    icon: CogIcon,
    separator: true,
    roles: [ROLES.TOXICO_MANAGER, ROLES.ASSISTANT]
  }
```

to:

```javascript
  {
    path: '/dashboard/configuration',
    labelKey: 'config.title',
    icon: CogIcon,
    separator: true,
    roles: [ROLES.TOXICO_MANAGER]
  }
```

In `ah2-admin-web/src/router/index.js`, find the `configuration` child route (inside the `/dashboard` block):

```javascript
      {
        path: 'configuration',
        name: 'system-config',
        component: () => import('@/views/SystemConfig.vue'),
        meta: { 
            requiresAuth: true, 
            roles: [ROLES.ADMIN, ROLES.TOXICO_MANAGER, ROLES.ASSISTANT] 
        }
      },
```

change it to:

```javascript
      {
        path: 'configuration',
        name: 'system-config',
        component: () => import('@/views/SystemConfig.vue'),
        meta: { 
            requiresAuth: true, 
            roles: [ROLES.ADMIN, ROLES.TOXICO_MANAGER] 
        }
      },
```

- [ ] **Step 3: L4d (reduced) — new `/medical/consultations` route for medecin and nurse**

In `ah2-admin-web/src/router/index.js`, inside the `/medical` block's `children` array, add a new entry right after the existing `doctors` entry:

```javascript
      {
        path: 'doctors',
        name: 'medical-doctors',
        component: () => import('@/views/modules/doctors/DoctorKpiView.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
      {
        path: 'consultations',
        name: 'medical-consultations',
        component: () => import('@/views/modules/consultations/ConsultationsList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      }
```

(this only adds the new `consultations` object as a sibling after `doctors` — the `doctors` block itself is unchanged, shown here only to anchor the insertion point exactly.)

- [ ] **Step 4: Add the menu entry in `MedicalLayout.vue`**

Add `SparklesIcon` to the Heroicons import block (matches the icon already used for the same screen in `SecretaireLayout.vue`):

```javascript
import {
  CalendarIcon,
  TagIcon,
  HeartIcon,
  UserGroupIcon,
  ChartBarIcon,
  SparklesIcon,
  Bars3Icon,
  Bars3CenterLeftIcon
} from '@heroicons/vue/24/outline';
```

Add a new menu item after `doctors` in `menuItems`:

```javascript
  {
    path: '/medical/doctors',
    labelKey: 'doctorKpi.title',
    icon: ChartBarIcon,
  },
  {
    path: '/medical/consultations',
    labelKey: 'consultations.title',
    icon: SparklesIcon,
  },
];
```

(`consultations.title` already exists in both `fr` and `en` locale blocks of `ah2-admin-web/src/i18n.js` — no new i18n key needed, verify it resolves to "Consultations" in both before moving on.)

- [ ] **Step 5: Verify the build succeeds**

Run: `cd ah2-admin-web && npm run build`
Expected: build succeeds, a dedicated lazy chunk is emitted for the reused `ConsultationsList.vue` component (or it's bundled with its existing `secretariat-consultations` chunk — either is fine, this route reuses the same component file, not a new one).

- [ ] **Step 6: Commit**

No commit — see Task 1 Step 13.

---

## Manual QA checklist (not executable in this environment — no browser tool)

Record in the ledger as unexecuted, same as every prior chantier:

1. A real `admin` account still sees every menu entry unchanged (super-user bypass in `MainLayout.vue`'s `filteredMenu` still works after the `hasRole` refactor).
2. An `Assistant` account no longer sees "Configuration" in the sidebar, and navigating directly to `/dashboard/configuration` by URL redirects away (403/forbidden), not just hides the menu link.
3. A `nurse` account now sees "Historique" under Laboratoire and can open it without a 403.
4. A `medecin` (and separately a `nurse`) account now sees "Consultations" in `/medical`'s sidebar, opens `ConsultationsList.vue` without a 403, and the list loads real spiritual-consultation data.
5. A freshly created `ToxicoManager` account (created by the user after this chantier lands) can open Users, Logs (audit), and Patients without any 403 — the 3 previously-broken menu entries.
6. An `Assistant` account can still search/list patients (`GET /patients/`) but a `PUT`/`DELETE` attempt on a patient (e.g. via direct API call, since the UI never exposed this to Assistant anyway) is refused with 403.
7. Spot-check that role-gated buttons still show/hide correctly for at least one role per touched file (secretaire on `PatientList.vue`'s manage buttons, medecin on `PatientDetailView.vue`'s consultation button, admin on `LabConfig.vue`'s admin-only controls) — the `hasRole` refactor should be behaviorally invisible to every role that isn't ToxicoManager/Assistant/nurse.

## Self-review

- **Spec coverage:** §3 (L4a) → Task 1. §6 (L4d reduced) → Task 6 Steps 3-4. §5 (L4c) → Task 6 Step 2. §4 (L4b) → Task 6 Step 1. §7 (L4e) → Task 5. §8 (dette : assistant/patients → Task 2; procédure morte → Task 3; code mort create_patient → Task 4).
- **Placeholder scan:** no TBD/TODO; every step has complete, real code, verified against the actual current file contents before this plan was written (not assumed).
- **Type consistency:** `authStore.hasRole(allowedRoles: string[]): boolean` (Task 5, defined once) is called identically at all 6 replaced sites and nowhere redefined with a different name or signature.
