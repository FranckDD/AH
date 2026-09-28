# Chantier 7d Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every role a self-service way to change their password and edit their own profile (`full_name`, `email`, `contact`) — closing registre `L3f`, the last item of chantier 7.

**Architecture:** Backend-first: fix a pre-existing bug in `UserController.update_user` that swallows uniqueness conflicts into a generic 500, extend `GET /auth/me`, add a new restricted self-service `PUT /auth/profile` endpoint. Then frontend: two new `authStore` actions wrapping the already-working `PUT /auth/password` and the new `PUT /auth/profile`, one shared `AccountModal.vue` (profile tab + password tab), wired into the 3 independent layout headers (`MainLayout.vue`, `SecretaireLayout.vue`, `MedicalLayout.vue` — `LabLayout.vue` is nested inside `MainLayout.vue`, not a 4th window, so it's already covered).

**Tech Stack:** FastAPI + SQLAlchemy + PostgreSQL (Pydantic schemas), Vue 3 (`<script setup>`, Options-API Pinia store), vue-i18n, Tailwind, Heroicons.

**Spec:** `docs/superpowers/specs/2026-09-22-chantier-7d-profil-mot-de-passe-design.md`

## Global Constraints

- `PUT /auth/profile` accepts ONLY `full_name`, `email`, `contact` — never `username`, `password`, `role_id`, `is_active`, `specialty_id`. `user_id` comes exclusively from the JWT (`current_user`), never from the request body or a URL parameter.
- No new role guard: `PUT /auth/profile` and `PUT /auth/password` are reachable by any authenticated user (`Depends(get_current_user)`), matching `GET /auth/me` today.
- Avoid the circular import between `auth_endpoints.py` and `users_endpoint.py` — `auth_endpoints.py` must build its own `UserController` inline (via `UserRepository`/`RoleRepository`, both leaf modules), never import `users_endpoint.py::get_user_controller`.
- No frontend test framework exists in this repo — frontend verification is `npm run build` plus a manual QA checklist at the end of the plan.

---

## Task 1: Backend — fix `UserController.update_user`'s swallowed `IntegrityError`

**Files:**
- Modify: `controller/user_controller.py:6,39-53`
- Test: `tests/test_users_pagination.py` (or create `tests/test_users_update.py` if that file doesn't already cover this — see Step 1)

**Interfaces:**
- Consumes: none.
- Produces: `UserController.update_user(user_id, data)` now re-raises `IntegrityError` distinctly instead of converting it to `RuntimeError` — Task 2 depends on this to return a clean 409 from the new self-service endpoint (reusing this exact method).

- [ ] **Step 1: Write a failing test proving the existing admin endpoint returns 500 instead of 409 on a duplicate email**

Check first whether `tests/test_users_pagination.py` or another existing test file already imports `users_endpoint` and `create_test_user` in a way you can extend — if so add the test there; otherwise create a new file `tests/test_users_update.py`:

```python
# tests/test_users_update.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.admin import users_endpoint
from tests.conftest import create_test_user, auth_headers

TEST_PASSWORD = "Correct123!"


def test_update_user_duplicate_email_returns_409_not_500(db_session, api_client):
    """Registre L3f (chantier 7d) : UserController.update_user attrapait
    IntegrityError dans son 'except SQLAlchemyError' generique (IntegrityError
    est une sous-classe de SQLAlchemyError), le convertissant en RuntimeError
    avant meme de sortir du controller - le bloc 'except IntegrityError' de
    cet endpoint n'a donc jamais pu s'executer. Un email deja pris par un
    autre compte renvoyait un 500 generique au lieu d'un 409 propre."""
    admin = create_test_user(db_session, "l7d_admin_dupemail", "admin", password=TEST_PASSWORD)
    admin.email = "deja.pris@example.com"
    db_session.flush()
    target = create_test_user(db_session, "l7d_target_dupemail", "secretaire", password=TEST_PASSWORD)
    db_session.flush()

    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "l7d_admin_dupemail", TEST_PASSWORD)

    resp = client.put(f"/users/{target.user_id}", json={"email": "deja.pris@example.com"}, headers=headers)

    assert resp.status_code == 409
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_users_update.py::test_update_user_duplicate_email_returns_409_not_500 -v`
Expected: FAIL — the response is 500 ("Erreur serveur maj"), not 409.

- [ ] **Step 3: Fix `controller/user_controller.py`**

Change the import at the top of the file from:

```python
from sqlalchemy.exc import SQLAlchemyError
```

to:

```python
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
```

Then change `update_user`'s commit block from:

```python
        try:
            self.user_repo.session.commit()
            return user
        except SQLAlchemyError as e:
            self.user_repo.session.rollback()
            raise RuntimeError(f"Erreur mise à jour utilisateur : {e}")
```

to:

```python
        try:
            self.user_repo.session.commit()
            return user
        except IntegrityError:
            self.user_repo.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.user_repo.session.rollback()
            raise RuntimeError(f"Erreur mise à jour utilisateur : {e}")
```

- [ ] **Step 4: Run the test again to verify it passes**

Run: `python -m pytest tests/test_users_update.py::test_update_user_duplicate_email_returns_409_not_500 -v`
Expected: PASS

- [ ] **Step 5: Run the whole users test suite to confirm no regression**

Run: `python -m pytest tests/test_users_pagination.py tests/test_users_update.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

This project never commits without the user's fresh explicit approval — do not run `git add`/`git commit`. Leave the changes on disk.

---

## Task 2: Backend — extend `GET /auth/me`, add `PUT /auth/profile`

**Files:**
- Modify: `api_backend/backend_app/routes/auth/auth_endpoints.py:1-14` (imports), `:178-190` (`get_me`), after `:243` (new endpoint)
- Modify: `api_backend/backend_app/routes/auth/schemas.py:1` (imports), end of file (new schema)
- Test: `tests/test_auth_profile.py` (new)

**Interfaces:**
- Consumes: `UserController.update_user(user_id, data)` from Task 1 (must re-raise `IntegrityError` distinctly for this task's 409 to work).
- Produces: `GET /auth/me` response now includes `full_name`, `email`, `contact`. `PUT /auth/profile` accepts `{full_name?, email?, contact?}`, returns `{id, username, full_name, email, contact}` — Task 4 (frontend `authStore.updateProfile`) consumes this exact response shape to merge into `authStore.user`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_auth_profile.py`:

```python
# tests/test_auth_profile.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from tests.conftest import create_test_user, login, auth_headers

TEST_PASSWORD = "Correct123!"


def test_get_me_includes_profile_fields(db_session, api_client):
    user = create_test_user(db_session, "l7d_getme_profile", "medecin", password=TEST_PASSWORD)
    user.email = "medecin.test@example.com"
    user.contact = "0102030405"
    db_session.flush()

    client = api_client(auth_endpoints)
    headers = auth_headers(client, "l7d_getme_profile", TEST_PASSWORD)

    resp = client.get("/auth/me", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Test l7d_getme_profile"
    assert body["email"] == "medecin.test@example.com"
    assert body["contact"] == "0102030405"


def test_update_my_profile_success(db_session, api_client):
    create_test_user(db_session, "l7d_update_profile", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints)
    headers = auth_headers(client, "l7d_update_profile", TEST_PASSWORD)

    resp = client.put(
        "/auth/profile",
        json={"full_name": "Nouveau Nom", "email": "nouveau@example.com", "contact": "0611223344"},
        headers=headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Nouveau Nom"
    assert body["email"] == "nouveau@example.com"
    assert body["contact"] == "0611223344"

    get_resp = client.get("/auth/me", headers=headers)
    assert get_resp.json()["full_name"] == "Nouveau Nom"


def test_update_my_profile_partial_leaves_other_fields_unchanged(db_session, api_client):
    user = create_test_user(db_session, "l7d_partial_profile", "secretaire", password=TEST_PASSWORD)
    user.contact = "0600000000"
    db_session.flush()

    client = api_client(auth_endpoints)
    headers = auth_headers(client, "l7d_partial_profile", TEST_PASSWORD)

    resp = client.put("/auth/profile", json={"full_name": "Juste Le Nom"}, headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Juste Le Nom"
    assert body["contact"] == "0600000000"


def test_update_my_profile_duplicate_email_returns_409(db_session, api_client):
    other = create_test_user(db_session, "l7d_other_dupemail", "medecin", password=TEST_PASSWORD)
    other.email = "occupe@example.com"
    db_session.flush()
    create_test_user(db_session, "l7d_self_dupemail", "secretaire", password=TEST_PASSWORD)

    client = api_client(auth_endpoints)
    headers = auth_headers(client, "l7d_self_dupemail", TEST_PASSWORD)

    resp = client.put("/auth/profile", json={"email": "occupe@example.com"}, headers=headers)

    assert resp.status_code == 409


def test_update_my_profile_cannot_change_role_or_username(db_session, api_client):
    """SelfProfileUpdate n'a aucun champ role_id/username/is_active/password -
    meme envoyes, ils sont silencieusement ignores par Pydantic (champs
    inconnus rejetes par defaut... verifie qu'ils n'ont AUCUN effet, pas que
    la requete echoue)."""
    user = create_test_user(db_session, "l7d_no_privesc", "secretaire", password=TEST_PASSWORD)
    original_role_id = user.role_id
    db_session.flush()

    client = api_client(auth_endpoints)
    headers = auth_headers(client, "l7d_no_privesc", TEST_PASSWORD)

    resp = client.put(
        "/auth/profile",
        json={"full_name": "Toujours Secretaire", "role_id": 999999, "username": "pirate", "is_active": False},
        headers=headers,
    )

    assert resp.status_code == 200
    get_resp = client.get("/auth/me", headers=headers)
    assert get_resp.json()["username"] == "l7d_no_privesc"
    assert get_resp.json()["application_role"]["role_name"] == "secretaire"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_auth_profile.py -v`
Expected: FAIL — `full_name`/`email`/`contact` missing from `/auth/me`, `PUT /auth/profile` returns 404 (route doesn't exist yet).

- [ ] **Step 3: Add `SelfProfileUpdate` to `api_backend/backend_app/routes/auth/schemas.py`**

Change the import line from:

```python
from pydantic import BaseModel, Field, validator
```

to:

```python
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
```

Add at the end of the file:

```python
class SelfProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    contact: Optional[str] = None
```

- [ ] **Step 4: Extend `GET /auth/me` in `auth_endpoints.py`**

Change:

```python
@router.get("/auth/me", tags=["Authentication"])
def get_me(current_user=Depends(get_current_user)):
    """
    Retourne les infos du user courant basé sur le JWT.
    """
    return {
        "id": current_user.user_id,
        "username": getattr(current_user, "username", None),
        "application_role": {
            "id": getattr(current_user.application_role, "id", None),
            "role_name": getattr(current_user.application_role, "role_name", None),
        }
    }
```

to:

```python
@router.get("/auth/me", tags=["Authentication"])
def get_me(current_user=Depends(get_current_user)):
    """
    Retourne les infos du user courant basé sur le JWT.
    """
    return {
        "id": current_user.user_id,
        "username": getattr(current_user, "username", None),
        "full_name": getattr(current_user, "full_name", None),
        "email": getattr(current_user, "email", None),
        "contact": getattr(current_user, "contact", None),
        "application_role": {
            "id": getattr(current_user.application_role, "id", None),
            "role_name": getattr(current_user.application_role, "role_name", None),
        }
    }
```

- [ ] **Step 5: Add the new imports to `auth_endpoints.py`**

Change:

```python
import datetime
from ...security.role_map import normalize_role_name, normalize_roles_list
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import ExpiredSignatureError, jwt as jose_jwt ,JWTError
from ...database import SessionLocal
from ...config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from ...rate_limit import limiter
from controller.auth_controller import AuthController
from .schemas import Token
from .schemas import UserPasswordUpdate
from typing import Any
import uuid
```

to:

```python
import datetime
from ...security.role_map import normalize_role_name, normalize_roles_list
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from jose import ExpiredSignatureError, jwt as jose_jwt ,JWTError
from ...database import SessionLocal
from ...config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from ...rate_limit import limiter
from ...exceptions import translate_integrity_error
from controller.auth_controller import AuthController
from controller.user_controller import UserController
from repositories.user_repo import UserRepository
from repositories.role_repo import RoleRepository
from .schemas import Token
from .schemas import UserPasswordUpdate
from .schemas import SelfProfileUpdate
from typing import Any
import uuid
```

- [ ] **Step 6: Add the new endpoint, right after `update_password`**

Add at the end of the file (after the existing `update_password` function, which ends around line 243):

```python
def get_self_user_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserController:
    # Factory locale : ne PAS importer users_endpoint.py::get_user_controller
    # ici, ce module y est deja importe (get_current_user/role_required) -
    # un import dans l'autre sens creerait un cycle.
    user_repo = UserRepository(session=db)
    role_repo = RoleRepository(session=db)
    return UserController(user_repo=user_repo, role_repo=role_repo)


@router.put("/auth/profile", tags=["Authentication"])
def update_my_profile(
    data: SelfProfileUpdate,
    user_ctrl: UserController = Depends(get_self_user_controller),
    current_user = Depends(get_current_user),
):
    """
    Permet à l'utilisateur connecté de modifier son propre profil
    (full_name/email/contact uniquement - jamais username/password/role_id/
    is_active/specialty_id, absents de SelfProfileUpdate). user_id vient
    exclusivement du JWT décodé (current_user), jamais du corps de la
    requête.
    """
    try:
        payload = data.model_dump(exclude_unset=True)
        updated = user_ctrl.update_user(current_user.user_id, payload)
        return {
            "id": updated.user_id,
            "username": updated.username,
            "full_name": updated.full_name,
            "email": updated.email,
            "contact": updated.contact,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except IntegrityError as ie:
        try:
            user_ctrl.user_repo.session.rollback()
        except Exception:
            pass
        raise translate_integrity_error(ie)
```

- [ ] **Step 7: Run the tests again, then the whole auth test suite, to verify no regression**

Run: `python -m pytest tests/test_auth_profile.py tests/test_auth_login.py tests/test_auth_token_lifecycle.py tests/test_auth_manager.py -v`
Expected: all PASS

- [ ] **Step 8: Commit**

No commit — see Task 1 Step 6.

---

## Task 3: Frontend — `authStore` actions (`updateProfile`, `changePassword`)

**Files:**
- Modify: `ah2-admin-web/src/stores/auth.js`

**Interfaces:**
- Consumes: `PUT /auth/profile` (Task 2) and the pre-existing `PUT /auth/password`.
- Produces: `authStore.updateProfile(payload: {full_name?, email?, contact?}): Promise<{id, username, full_name, email, contact}>` (merges the response into `this.user` and `localStorage`), `authStore.changePassword(payload: {old_password, new_password, confirm_password}): Promise<AxiosResponse>` — consumed by Task 5 (`AccountModal.vue`).

- [ ] **Step 1: Add the two actions**

In `ah2-admin-web/src/stores/auth.js`, this store is written as an Options API object (`state`/`getters`/`actions`). Add the two new actions inside the existing `actions: { ... }` block, right after `login` and before `logout` (or anywhere inside `actions`, order doesn't matter functionally — placing them together after `login` keeps related auth-adjacent calls grouped):

```javascript
    async updateProfile(payload) {
      const response = await api.put('/auth/profile', payload);
      this.user = { ...this.user, ...response.data };
      localStorage.setItem('user', JSON.stringify(this.user));
      return response.data;
    },

    async changePassword(payload) {
      return api.put('/auth/password', payload);
    },
```

- [ ] **Step 2: Verify the build succeeds**

Run: `cd ah2-admin-web && npm run build`
Expected: build succeeds (these actions aren't called from anywhere yet, so this only catches syntax errors — full wiring verified in Task 5/6).

- [ ] **Step 3: Commit**

No commit — see Task 1 Step 6.

---

## Task 4: Frontend — `AccountModal.vue` (new, self-contained: profile tab + password tab)

**Files:**
- Create: `ah2-admin-web/src/components/account/AccountModal.vue`
- Modify: `ah2-admin-web/src/i18n.js`

**Interfaces:**
- Consumes: `authStore.user` (for pre-filling the profile tab — already carries `full_name`/`email`/`contact` after Task 2's `/auth/me` extension, since login already calls `/auth/me`), `authStore.updateProfile(payload)`, `authStore.changePassword(payload)` (Task 3).
- Produces: emits only `close` — this modal is fully self-contained (no list to refresh afterward, unlike other modals in this codebase that emit `save` to a parent orchestrator).

- [ ] **Step 1: Create `AccountModal.vue`**

```vue
<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-sm">
    <div class="relative mx-auto w-full max-w-md bg-white shadow-xl rounded-2xl border border-gray-200 flex flex-col max-h-[90vh]">
      <div class="px-6 py-4 border-b border-gray-100 bg-gray-700 rounded-t-2xl flex justify-between items-center flex-shrink-0">
        <h3 class="text-lg font-bold text-white flex items-center">
          <UserCircleIcon class="h-6 w-6 mr-2" />
          {{ t('account.title') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-200 hover:text-white transition">
          <span class="text-2xl font-bold">&times;</span>
        </button>
      </div>

      <div class="border-b border-gray-100 flex flex-shrink-0">
        <button
          @click="activeTab = 'profile'"
          class="flex-1 py-3 text-sm font-semibold transition"
          :class="activeTab === 'profile' ? 'text-gray-800 border-b-2 border-gray-700' : 'text-gray-400 hover:text-gray-600'"
        >
          {{ t('account.tab_profile') }}
        </button>
        <button
          @click="activeTab = 'password'"
          class="flex-1 py-3 text-sm font-semibold transition"
          :class="activeTab === 'password' ? 'text-gray-800 border-b-2 border-gray-700' : 'text-gray-400 hover:text-gray-600'"
        >
          {{ t('account.tab_password') }}
        </button>
      </div>

      <div class="p-6 overflow-y-auto">
        <form v-if="activeTab === 'profile'" @submit.prevent="handleProfileSubmit" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('account.full_name') }}</label>
            <input v-model="profileForm.fullName" type="text" required
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-gray-500 focus:border-gray-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('account.email') }}</label>
            <input v-model="profileForm.email" type="email"
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-gray-500 focus:border-gray-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('account.contact') }}</label>
            <input v-model="profileForm.contact" type="tel"
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-gray-500 focus:border-gray-500" />
          </div>

          <div v-if="profileError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded text-sm text-red-700">
            {{ profileError }}
          </div>
          <div v-if="profileSuccess" class="bg-green-50 border-l-4 border-green-500 p-3 rounded text-sm text-green-700">
            {{ t('account.profile_saved') }}
          </div>

          <div class="flex justify-end pt-2">
            <button type="submit" :disabled="isSavingProfile"
                    class="px-6 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 font-medium shadow-sm transition disabled:opacity-50">
              {{ isSavingProfile ? t('account.saving') : t('account.save') }}
            </button>
          </div>
        </form>

        <form v-else @submit.prevent="handlePasswordSubmit" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('account.old_password') }}</label>
            <input v-model="passwordForm.oldPassword" type="password" required
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-gray-500 focus:border-gray-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('account.new_password') }}</label>
            <input v-model="passwordForm.newPassword" type="password" required minlength="8"
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-gray-500 focus:border-gray-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('account.confirm_password') }}</label>
            <input v-model="passwordForm.confirmPassword" type="password" required minlength="8"
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-gray-500 focus:border-gray-500" />
          </div>

          <div v-if="passwordMismatch" class="bg-red-50 border-l-4 border-red-500 p-3 rounded text-sm text-red-700">
            {{ t('account.password_mismatch') }}
          </div>
          <div v-if="passwordError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded text-sm text-red-700">
            {{ passwordError }}
          </div>
          <div v-if="passwordSuccess" class="bg-green-50 border-l-4 border-green-500 p-3 rounded text-sm text-green-700">
            {{ t('account.password_saved') }}
          </div>

          <div class="flex justify-end pt-2">
            <button type="submit" :disabled="isSavingPassword"
                    class="px-6 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 font-medium shadow-sm transition disabled:opacity-50">
              {{ isSavingPassword ? t('account.saving') : t('account.save') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { UserCircleIcon } from '@heroicons/vue/24/outline';

defineEmits(['close']);
const { t } = useI18n();
const authStore = useAuthStore();

const activeTab = ref('profile');

// --- Profil ---
const profileForm = reactive({
  fullName: authStore.user?.full_name || '',
  email: authStore.user?.email || '',
  contact: authStore.user?.contact || '',
});
const isSavingProfile = ref(false);
const profileError = ref('');
const profileSuccess = ref(false);

const mapErrorToMessage = (err) => {
  if (err.response) {
    const status = err.response.status;
    const detail = err.response.data?.detail;
    if (status === 422) return "Données invalides.";
    if (status === 400) return detail || "Requête invalide.";
    if (status === 409) return detail || "Cette adresse email est déjà utilisée.";
    return `Erreur serveur (${status}) : ${detail || 'veuillez réessayer'}`;
  }
  if (err.request) return "Erreur réseau. Veuillez vérifier votre connexion.";
  return err.message || "Une erreur inattendue est survenue.";
};

const handleProfileSubmit = async () => {
  isSavingProfile.value = true;
  profileError.value = '';
  profileSuccess.value = false;
  try {
    await authStore.updateProfile({
      full_name: profileForm.fullName.trim(),
      email: profileForm.email.trim() || null,
      contact: profileForm.contact.trim() || null,
    });
    profileSuccess.value = true;
  } catch (err) {
    profileError.value = mapErrorToMessage(err);
  } finally {
    isSavingProfile.value = false;
  }
};

// --- Mot de passe ---
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
});
const isSavingPassword = ref(false);
const passwordError = ref('');
const passwordSuccess = ref(false);

const passwordMismatch = computed(() =>
  passwordForm.newPassword.length > 0 &&
  passwordForm.confirmPassword.length > 0 &&
  passwordForm.newPassword !== passwordForm.confirmPassword
);

const handlePasswordSubmit = async () => {
  if (passwordMismatch.value) return;
  isSavingPassword.value = true;
  passwordError.value = '';
  passwordSuccess.value = false;
  try {
    await authStore.changePassword({
      old_password: passwordForm.oldPassword,
      new_password: passwordForm.newPassword,
      confirm_password: passwordForm.confirmPassword,
    });
    passwordSuccess.value = true;
    passwordForm.oldPassword = '';
    passwordForm.newPassword = '';
    passwordForm.confirmPassword = '';
  } catch (err) {
    passwordError.value = mapErrorToMessage(err);
  } finally {
    isSavingPassword.value = false;
  }
};
</script>
```

- [ ] **Step 2: Add i18n keys**

In `ah2-admin-web/src/i18n.js`, add a new top-level `account: { ... }` block as a sibling of `common:` in the `fr` locale block (right after `common: { ... }` closes, around line 20):

```javascript
    account: {
      title: "Mon compte",
      tab_profile: "Profil",
      tab_password: "Mot de passe",
      full_name: "Nom complet",
      email: "Email",
      contact: "Téléphone",
      old_password: "Mot de passe actuel",
      new_password: "Nouveau mot de passe",
      confirm_password: "Confirmer le nouveau mot de passe",
      password_mismatch: "Les nouveaux mots de passe ne correspondent pas.",
      profile_saved: "Profil mis à jour avec succès.",
      password_saved: "Mot de passe mis à jour avec succès.",
      save: "Enregistrer",
      saving: "Enregistrement...",
    },
```

And the English mirror, as a sibling of the `en` locale's `common: { ... }` block:

```javascript
    account: {
      title: "My Account",
      tab_profile: "Profile",
      tab_password: "Password",
      full_name: "Full Name",
      email: "Email",
      contact: "Phone",
      old_password: "Current Password",
      new_password: "New Password",
      confirm_password: "Confirm New Password",
      password_mismatch: "The new passwords do not match.",
      profile_saved: "Profile updated successfully.",
      password_saved: "Password updated successfully.",
      save: "Save",
      saving: "Saving...",
    },
```

Also add `my_account: "Mon compte"` (fr) / `my_account: "My Account"` (en) inside each locale's existing `common: { ... }` block, right after `logout:` — this key is used by Task 5's header button, not by this modal.

- [ ] **Step 3: Verify the build succeeds**

Run: `cd ah2-admin-web && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

No commit — see Task 1 Step 6.

---

## Task 5: Frontend — wire `AccountModal.vue` into the 3 layout headers

**Files:**
- Modify: `ah2-admin-web/src/components/layout/MainLayout.vue`
- Modify: `ah2-admin-web/src/components/layout/SecretaireLayout.vue`
- Modify: `ah2-admin-web/src/components/layout/MedicalLayout.vue`

**Interfaces:**
- Consumes: `AccountModal.vue` (Task 4), `common.my_account` i18n key (Task 4).
- Produces: none consumed by later tasks — last task of this plan.

The three headers are byte-identical in structure (verified before writing this plan) — the same 4 edits apply to each of the 3 files.

- [ ] **Step 1: `MainLayout.vue`**

Add `UserCircleIcon` to the Heroicons import (currently `HomeIcon, UsersIcon, ClipboardDocumentListIcon, BanknotesIcon, BeakerIcon, ChartBarIcon, CogIcon, ShieldCheckIcon, CubeIcon, Bars3Icon, Bars3CenterLeftIcon, ExclamationCircleIcon`):

```javascript
import {
  HomeIcon, UsersIcon, ClipboardDocumentListIcon, BanknotesIcon,
  BeakerIcon, ChartBarIcon, CogIcon, ShieldCheckIcon, CubeIcon,
  Bars3Icon, Bars3CenterLeftIcon, ExclamationCircleIcon, UserCircleIcon
} from '@heroicons/vue/24/outline';
```

Import the modal:

```javascript
import AccountModal from '@/components/account/AccountModal.vue';
```

Add a `showAccountModal` ref near the other `ref` declarations (e.g. right after `const isSidebarOpen = ref(true);`):

```javascript
const showAccountModal = ref(false);
```

In the template, change the header's `<div class="flex items-center space-x-4">` block from:

```html
        <div class="flex items-center space-x-4">
          <div class="flex bg-gray-100 rounded-lg p-1">
            <button 
              @click="changeLanguage('fr')"
              :class="locale === 'fr' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'"
              class="px-3 py-1 rounded-md text-sm font-medium transition-all duration-200"
            >FR</button>
            <button 
              @click="changeLanguage('en')"
              :class="locale === 'en' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'"
              class="px-3 py-1 rounded-md text-sm font-medium transition-all duration-200"
            >EN</button>
          </div>

          <button 
            @click="handleLogout"
            class="bg-red-500 hover:bg-red-600 text-white text-sm font-semibold py-2 px-4 rounded transition duration-150"
          >
            {{ $t('common.logout') }} 
          </button>
        </div>
```

to:

```html
        <div class="flex items-center space-x-4">
          <div class="flex bg-gray-100 rounded-lg p-1">
            <button 
              @click="changeLanguage('fr')"
              :class="locale === 'fr' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'"
              class="px-3 py-1 rounded-md text-sm font-medium transition-all duration-200"
            >FR</button>
            <button 
              @click="changeLanguage('en')"
              :class="locale === 'en' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'"
              class="px-3 py-1 rounded-md text-sm font-medium transition-all duration-200"
            >EN</button>
          </div>

          <button
            @click="showAccountModal = true"
            class="flex items-center text-gray-600 hover:text-gray-900 text-sm font-medium transition"
            :title="$t('common.my_account')"
          >
            <UserCircleIcon class="h-6 w-6" />
          </button>

          <button 
            @click="handleLogout"
            class="bg-red-500 hover:bg-red-600 text-white text-sm font-semibold py-2 px-4 rounded transition duration-150"
          >
            {{ $t('common.logout') }} 
          </button>
        </div>
```

Add the modal right before the closing `</template>` tag, as a sibling of the root element (outside the `<div class="flex w-full h-screen ...">` wrapper is also fine — place it as the last child inside that root wrapper div, right before its closing `</div>`):

```html
    <AccountModal v-if="showAccountModal" @close="showAccountModal = false" />
```

- [ ] **Step 2: `SecretaireLayout.vue`**

Same 4 edits. Add `UserCircleIcon` to the Heroicons import (currently `UserGroupIcon, CubeIcon, BanknotesIcon, ArrowUpTrayIcon, SparklesIcon, Bars3Icon, Bars3CenterLeftIcon, HomeIcon`):

```javascript
import {
  UserGroupIcon,
  CubeIcon,
  BanknotesIcon,
  ArrowUpTrayIcon,
  SparklesIcon,
  Bars3Icon,
  Bars3CenterLeftIcon,
  HomeIcon,
  UserCircleIcon
} from '@heroicons/vue/24/outline';
```

Import the modal, add `showAccountModal = ref(false)`, apply the exact same template change to the `<div class="flex items-center space-x-4">` block (this file's header block is byte-identical to `MainLayout.vue`'s except the username's color class `text-emerald-600` instead of `text-green-600` — that line is untouched, only the button block changes), and add `<AccountModal v-if="showAccountModal" @close="showAccountModal = false" />` as the last child inside the root wrapper div, same as Step 1.

- [ ] **Step 3: `MedicalLayout.vue`**

Same 4 edits. Add `UserCircleIcon` to the Heroicons import (currently `CalendarIcon, TagIcon, HeartIcon, UserGroupIcon, ChartBarIcon, SparklesIcon, BeakerIcon, Bars3Icon, Bars3CenterLeftIcon`):

```javascript
import {
  CalendarIcon,
  TagIcon,
  HeartIcon,
  UserGroupIcon,
  ChartBarIcon,
  SparklesIcon,
  BeakerIcon,
  Bars3Icon,
  Bars3CenterLeftIcon,
  UserCircleIcon
} from '@heroicons/vue/24/outline';
```

Import the modal, add `showAccountModal = ref(false)`, apply the exact same template change (this file's header block is also byte-identical to the other two), and add `<AccountModal v-if="showAccountModal" @close="showAccountModal = false" />` as the last child inside the root wrapper div.

- [ ] **Step 4: Verify the build succeeds**

Run: `cd ah2-admin-web && npm run build`
Expected: build succeeds, no unused-import errors.

- [ ] **Step 5: Commit**

No commit — see Task 1 Step 6.

---

## Manual QA checklist (not executable in this environment — no browser tool)

Record in the ledger as unexecuted, same as every prior chantier:

1. Log in as each of `admin`, `secretaire`, `medecin`, `laborantin` (or any role reaching `MainLayout.vue`/`SecretaireLayout.vue`/`MedicalLayout.vue`) → the "Mon compte" icon appears in the header next to the language toggle.
2. Open the modal → Profil tab pre-fills with the real `full_name`/`email`/`contact` (empty fields for `email`/`contact` if never set).
3. Edit `full_name` only, save → success message shown, header still shows the same username (only `full_name` changed, not `username`) — reload the page and reopen the modal to confirm the new `full_name` persisted (survives `localStorage` round-trip).
4. Try saving an email already used by another account → 409, clean error message ("Cette adresse email est déjà utilisée."), not a raw 500.
5. Password tab: wrong old password → clean 400 error ("L'ancien mot de passe est incorrect"). Mismatched new/confirm → client-side error before any network call. Correct old password + valid new password → success message, log out and log back in with the new password to confirm it actually changed.
6. Confirm `laborantin`/`biologiste` (nested under `MainLayout.vue` via `/dashboard/labo`) sees the same "Mon compte" button in `MainLayout.vue`'s outer header — no separate button needed inside `LabLayout.vue`'s own tab bar.

## Self-review

- **Spec coverage:** §3.1 (`GET /auth/me` extended) → Task 2 Step 4. §3.2 (`PUT /auth/profile` + the two real bugs found while writing the spec — circular import risk, swallowed `IntegrityError`) → Task 1 (bug fix) + Task 2 (new endpoint). §3.3 (`PUT /auth/password` unchanged) → no task touches it, correctly. §4.1 (`authStore` actions) → Task 3. §4.2 (`AccountModal.vue`) → Task 4. §4.3 (3 headers) → Task 5. §1's Laboratoire clarification → reflected in Task 5's scope (3 files, not 4) and the QA checklist's item 6.
- **Placeholder scan:** no TBD/TODO; every step has complete, real code, verified against the actual current file contents before this plan was written (imports, existing endpoint bodies, header markup all read from the real files, not assumed).
- **Type consistency:** `authStore.updateProfile(payload)`'s expected response shape (Task 3) matches exactly what `PUT /auth/profile` returns (Task 2: `{id, username, full_name, email, contact}`). `AccountModal.vue`'s `handleProfileSubmit`/`handlePasswordSubmit` (Task 4) call `authStore.updateProfile`/`authStore.changePassword` with the exact payload shapes those actions expect (Task 3), which in turn match the backend schemas (`SelfProfileUpdate`, `UserPasswordUpdate`) exactly.
