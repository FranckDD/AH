# Chantier 1 — Unification des rôles (chemin web) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire de `role_map.py` la source de vérité canonique pour les 9 rôles réels de la base plus le rôle réservé `manager`, débloquer les comptes actuellement verrouillés (`Psychologist`, `ToxicoManager`, `SpiritualCounsellor`, `Assistant`), fermer `WEB-04`, supprimer le code mort à 3 systèmes de rôles concurrents, et corriger le compte `secretaire1`.

**Architecture:** Extension additive de la table de correspondance existante (`role_map.py`), retrait d'un repli permissif isolé dans `role_required()`, suppression d'un module mort, et normalisation de la comparaison de rôles côté garde de navigation front. Aucune nouvelle couche introduite.

**Tech Stack:** Python (FastAPI, pytest), JavaScript (Vue Router), PostgreSQL.

## Global Constraints

- Périmètre strict : `role_map.py`, `role_required()`, le garde de navigation front, la donnée `secretaire1`. **Ne pas toucher** `get_current_user()` (déjà fail-closed sur `HEAD`, voir spec section 2), `patient_controller.py`, le mode hors ligne, `UserModal.vue`/`GROUP_MAPPING`.
- Le dépôt contient du travail en cours non lié à ce chantier sur plusieurs fichiers cibles (`auth_endpoints.py` a une version de travail avec repli permissif sur `get_current_user()` — **ne pas la committer**, ne pas y toucher du tout ; `router/index.js` a un module labo entier non commité). Isoler chaque correctif de ce travail en cours, comme au chantier 0 : committer le fichier entier seulement s'il est propre par rapport à `HEAD` ; sinon injecter précisément le correctif dans l'index à partir du contenu de `HEAD`, sans jamais utiliser `git add` brut sur un fichier déjà modifié par autre chose.
- `manager` est un canonique **réservé, sans ligne en base** — ne pas créer de ligne `application_roles` pour lui dans ce chantier.

---

## Task 1: Étendre `role_map.py` aux 9 rôles réels + `manager` réservé

**Files:**
- Modify: `api_backend/backend_app/security/role_map.py` (fichier propre, aucun travail en cours dessus)
- Test: `tests/test_role_map.py` (nouveau)

**Interfaces:**
- Consumes: rien
- Produces: `normalize_role_name(name: str | None) -> str | None` et `normalize_roles_list(names: list[str] | None) -> list[str]`, déjà exportées, comportement étendu. Consommées par `auth_endpoints.py` (Task 2) sans changement de signature.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `tests/test_role_map.py` :

```python
# tests/test_role_map.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.security.role_map import normalize_role_name, normalize_roles_list


def test_normalizes_the_five_original_roles():
    assert normalize_role_name("admin") == "admin"
    assert normalize_role_name("médecin") == "medecin"
    assert normalize_role_name("infirmiere") == "nurse"
    assert normalize_role_name("secrétaire") == "secretaire"
    assert normalize_role_name("laboratory_technician") == "laborantin"


def test_normalizes_the_four_db_roles_previously_uncovered():
    assert normalize_role_name("Psychologist") == "psychologist"
    assert normalize_role_name("psychologue") == "psychologist"
    assert normalize_role_name("SpiritualCounsellor") == "spiritualcounsellor"
    assert normalize_role_name("conseiller_spirituel") == "spiritualcounsellor"
    assert normalize_role_name("ToxicoManager") == "toxicomanager"
    assert normalize_role_name("toxico_manager") == "toxicomanager"
    assert normalize_role_name("Assistant") == "assistant"
    assert normalize_role_name("assistante") == "assistant"


def test_normalizes_the_reserved_manager_role():
    assert normalize_role_name("manager") == "manager"
    assert normalize_role_name("Manager") == "manager"


def test_unknown_role_returns_none():
    assert normalize_role_name("biologiste") is None
    assert normalize_role_name("role_qui_nexiste_pas") is None


def test_normalize_roles_list_dedupes_and_drops_unknown():
    result = normalize_roles_list(["Psychologist", "psychologue", "biologiste", None, ""])
    assert result == ["psychologist"]
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

```bash
pytest tests/test_role_map.py -v
```

Attendu : `test_normalizes_the_four_db_roles_previously_uncovered`, `test_normalizes_the_reserved_manager_role` échouent (`assert None == "psychologist"` etc.) ; les autres passent déjà (comportement des 5 rôles d'origine inchangé).

- [ ] **Step 3: Réécrire `role_map.py`**

Remplacer tout le contenu du fichier par :

```python
# app/security/role_map.py
from typing import Dict, Set

# Codes canoniques : strict equivalent en minuscules des role_name reels
# de la table application_roles, plus 'manager', reserve sans ligne en
# base (role en developpement, niveau d'acces inferieur a admin).
ADMIN = "admin"
MEDECIN = "medecin"
NURSE = "nurse"
SECRETAIRE = "secretaire"
LABORANTIN = "laborantin"
PSYCHOLOGIST = "psychologist"
SPIRITUALCOUNSELLOR = "spiritualcounsellor"
TOXICOMANAGER = "toxicomanager"
ASSISTANT = "assistant"
MANAGER = "manager"

ROLE_CANONICALS = {
    ADMIN, MEDECIN, NURSE, SECRETAIRE, LABORANTIN,
    PSYCHOLOGIST, SPIRITUALCOUNSELLOR, TOXICOMANAGER, ASSISTANT,
    MANAGER,
}

# mapping canonical -> set d'alias (fr, en, variations possibles)
ROLE_ALIASES: Dict[str, Set[str]] = {
    ADMIN: {"admin", "administrateur", "administrator", "adm"},
    MEDECIN: {"medecin", "médecin", "doctor", "dr", "physician"},
    NURSE: {"nurse", "infirmier", "infirmiere", "infirmière", "nurse_fr"},
    SECRETAIRE: {"secretaire", "secrétaire", "secretary", "secretary_fr"},
    LABORANTIN: {"laborantin", "lab_tech", "laboratory", "laboratory_technician", "technicien_lab"},
    PSYCHOLOGIST: {"psychologist", "psychologue"},
    SPIRITUALCOUNSELLOR: {"spiritualcounsellor", "spiritual_counsellor", "conseiller_spirituel", "conseiller spirituel"},
    TOXICOMANAGER: {"toxicomanager", "toxico_manager", "responsable_toxico"},
    ASSISTANT: {"assistant", "assistante"},
    MANAGER: {"manager", "gestionnaire"},
}

# Construire reverse map alias (lowercase) -> canonical
_ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canon, aliases in ROLE_ALIASES.items():
    for a in aliases:
        _ALIAS_TO_CANONICAL[a.strip().lower()] = canon

def normalize_role_name(name: str | None) -> str | None:
    """
    Retourne le code canonique (ex: 'medecin') pour un alias donné (insensible à la casse),
    ou None si inconnu.
    """
    if not name:
        return None
    key = name.strip().lower()
    # si on reçoit déjà un canonical connu, le retourner directement
    if key in ROLE_CANONICALS:
        return key
    return _ALIAS_TO_CANONICAL.get(key)

def normalize_roles_list(names: list[str] | None) -> list[str]:
    """
    Normalise une liste d'aliases en codes canoniques (déduplique et enlève les inconnus).
    """
    out: list[str] = []
    for n in names or []:
        canon = normalize_role_name(n)
        if canon and canon not in out:
            out.append(canon)
    return out
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

```bash
pytest tests/test_role_map.py -v
```

Attendu : 5 tests `PASS`.

- [ ] **Step 5: Commit**

```bash
git add api_backend/backend_app/security/role_map.py tests/test_role_map.py
git commit -m "feat(security): etendre role_map aux 9 roles reels + manager reserve (ARC-01)

role_map.py ne couvrait que 5 des 9 roles de la table application_roles.
Les comptes Psychologist, ToxicoManager, SpiritualCounsellor et Assistant
obtenaient roles=[] (verrouilles) puisque get_current_user() est deja
fail-closed sur HEAD. Ajoute aussi manager comme 10e canonique reserve
(role reel en developpement, niveau d'acces inferieur a admin, sans
ligne en base pour l'instant).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Nettoyer le repli permissif de `role_required()`

**Files:**
- Modify: `api_backend/backend_app/routes/auth/auth_endpoints.py` (isolation requise — voir Global Constraints)
- Test: `tests/test_role_required.py` (nouveau)

**Interfaces:**
- Consumes: `normalize_role_name` de `role_map.py` (Task 1)
- Produces: rien consommé par une tâche suivante

- [ ] **Step 1: Vérifier que `role_required()` est identique entre `HEAD` et la copie de travail**

```bash
diff <(git show HEAD:api_backend/backend_app/routes/auth/auth_endpoints.py | sed -n '/^def role_required/,/^    return wrapper/p') \
     <(sed -n '/^def role_required/,/^    return wrapper/p' api_backend/backend_app/routes/auth/auth_endpoints.py)
```

Attendu : aucune différence. Si une différence apparaît (le travail en cours a évolué depuis la rédaction de ce plan), **s'arrêter et signaler** avant de continuer — l'isolation décrite plus bas suppose cette fonction identique aux deux endroits.

- [ ] **Step 2: Écrire le test qui échoue**

Ce test importe l'application FastAPI complète, ce qui nécessite un backend joignable ou un mock — plus simple d'isoler `role_required` de sa dépendance `get_current_user` via une substitution de dépendance FastAPI. Créer `tests/test_role_required.py` :

```python
# tests/test_role_required.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from api_backend.backend_app.routes.auth.auth_endpoints import role_required, get_current_user


class FakeUser:
    def __init__(self, roles):
        self.roles = roles


def make_app(user_roles):
    app = FastAPI()

    def fake_current_user():
        return FakeUser(user_roles)

    app.dependency_overrides[get_current_user] = fake_current_user

    @app.get("/protected", dependencies=[Depends(role_required("admin", "manager"))])
    def protected():
        return {"ok": True}

    return app


def test_manager_role_is_recognized_as_valid_even_without_db_row():
    client = TestClient(make_app(["manager"]))
    resp = client.get("/protected")
    assert resp.status_code == 200


def test_admin_still_allowed():
    client = TestClient(make_app(["admin"]))
    resp = client.get("/protected")
    assert resp.status_code == 200


def test_unrecognized_allowed_role_does_not_leak_through_as_raw_string():
    # role_required("admin", "biologiste") : "biologiste" n'est pas un canonical connu
    # et ne doit plus etre accepte tel quel en minuscules (repli retire).
    app = FastAPI()

    def fake_current_user():
        return FakeUser(["biologiste"])  # un attaquant qui aurait ce role brut en DB

    app.dependency_overrides[get_current_user] = fake_current_user

    @app.get("/protected2", dependencies=[Depends(role_required("admin", "biologiste"))])
    def protected2():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/protected2")
    assert resp.status_code == 403
```

- [ ] **Step 3: Lancer le test pour vérifier l'échec**

```bash
pytest tests/test_role_required.py -v
```

Attendu : `test_manager_role_is_recognized_as_valid_even_without_db_row` échoue avec `403` au lieu de `200` (avant Task 1, `manager` n'était pas encore un canonical — si Task 1 est déjà faite, ce test précis passe déjà ; c'est `test_unrecognized_allowed_role_does_not_leak_through_as_raw_string` qui doit échouer ici, puisque le repli actuel accepte `"biologiste"` tel quel).

- [ ] **Step 4: Modifier `role_required()` dans la copie de travail**

Remplacer :

```python
    # normaliser la liste autorisée en codes canoniques (lowercase)
    allowed_canon = set()
    for r in allowed_roles:
        if not r:
            continue
        c = normalize_role_name(r) or r.strip().lower()
        allowed_canon.add(c)
```

par :

```python
    # normaliser la liste autorisée en codes canoniques (lowercase)
    allowed_canon = set()
    for r in allowed_roles:
        if not r:
            continue
        c = normalize_role_name(r)
        if c:
            allowed_canon.add(c)
```

- [ ] **Step 5: Lancer le test pour vérifier qu'il passe**

```bash
pytest tests/test_role_required.py -v
```

Attendu : 3 tests `PASS`.

- [ ] **Step 6: Isoler et stager uniquement ce correctif (le fichier porte du travail en cours ailleurs)**

```bash
SCRATCH="C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad"
git show HEAD:api_backend/backend_app/routes/auth/auth_endpoints.py > "$SCRATCH/auth_endpoints_base_c1.py"
python - <<PYEOF
old = '''    # normaliser la liste autorisée en codes canoniques (lowercase)
    allowed_canon = set()
    for r in allowed_roles:
        if not r:
            continue
        c = normalize_role_name(r) or r.strip().lower()
        allowed_canon.add(c)'''
new = '''    # normaliser la liste autorisée en codes canoniques (lowercase)
    allowed_canon = set()
    for r in allowed_roles:
        if not r:
            continue
        c = normalize_role_name(r)
        if c:
            allowed_canon.add(c)'''
path = r"$SCRATCH/auth_endpoints_base_c1.py"
content = open(path, encoding="utf-8").read()
assert old in content, "pattern introuvable dans HEAD - la fonction a-t-elle divergé ? Voir Step 1."
content = content.replace(old, new)
open(path, "w", encoding="utf-8").write(content)
print("ok")
PYEOF
BLOB=$(git hash-object -w "$SCRATCH/auth_endpoints_base_c1.py")
git update-index --cacheinfo 100644,$BLOB,api_backend/backend_app/routes/auth/auth_endpoints.py
git diff --cached -- api_backend/backend_app/routes/auth/auth_endpoints.py
```

Vérifier que le diff affiché ne montre **que** ce hunk (4 lignes changées dans `role_required`), rien sur `get_current_user()`.

- [ ] **Step 7: Commit**

```bash
git add tests/test_role_required.py
git commit -m "fix(security): retirer le repli permissif de role_required (ARC-01)

Le repli 'normalize_role_name(r) or r.strip().lower()' sur la liste des
roles AUTORISES (fournie par le code) est retire : un role non reconnu
est desormais ignore plutot que conserve tel quel en minuscules.

Grace au canonical reserve 'manager' ajoute en Task 1, les appels
role_required(\"admin\", \"manager\") continuent de fonctionner sans
changement de comportement observable.

auth_endpoints.py porte du travail en cours non lie a ce chantier sur
get_current_user() (repli permissif local, non commite - voir spec) :
seul le hunk de role_required() est inclus dans ce commit (injection
directe dans l'index), get_current_user() reste intact et non touche.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Supprimer le code mort `routes/core/permissions.py`

**Files:**
- Delete: `api_backend/backend_app/routes/core/permissions.py`

**Interfaces:**
- Consumes: rien
- Produces: rien

- [ ] **Step 1: Confirmer l'absence de tout import (dernière vérification avant suppression)**

```bash
grep -rln "from.*core.permissions\|core\.permissions\|CAISSE_PERMISSION\|require_permission" --include=*.py . | grep -v __pycache__ | grep -v "routes/core/permissions.py"
```

Attendu : **aucune ligne**. Si une ligne apparaît, s'arrêter — le fichier n'est plus mort, ne pas le supprimer.

- [ ] **Step 2: Supprimer le fichier**

```bash
git rm api_backend/backend_app/routes/core/permissions.py
```

- [ ] **Step 3: Vérifier que l'API démarre toujours**

```bash
PYTHONIOENCODING=utf-8 uvicorn api_backend.backend_app.main:app --port 8000 &
sleep 5
curl -s -o /dev/null -w "healthcheck: %{http_code}\n" http://127.0.0.1:8000/health
```

Attendu : `200`.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: supprimer routes/core/permissions.py, code mort (ARC-01)

3e systeme de rules incompatible avec role_map.py et la DB, importait
un package 'app' inexistant, jamais importe nulle part dans le depot
(verifie par recherche exhaustive avant suppression). Sa presence
contredisait l'objectif de source unique de verite pour les roles.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Front — comparaison de rôles insensible à la casse (`WEB-04`)

**Files:**
- Modify: `ah2-admin-web/src/router/index.js` (isolation requise pour la partie committée — voir Global Constraints)

**Interfaces:**
- Consumes: rien
- Produces: rien

- [ ] **Step 1: Corriger la copie de travail (garde de navigation + retrait des rôles morts)**

Remplacer dans `ah2-admin-web/src/router/index.js` :

```javascript
    // Si le rôle de l'utilisateur N'EST PAS dans la liste autorisée
    if (!requiredRoles.includes(userRole)) {
      // Cas spécial : L'Admin a accès à tout, même si pas listé explicitement (Super User)
      if (userRole === ROLES.ADMIN) {
          return next();
      }
```

par :

```javascript
    // Comparaison insensible à la casse : userRole vient de l'API (casse DB),
    // requiredRoles est ecrit a la main dans les meta de route.
    const normalizedUserRole = (userRole || '').toLowerCase();
    const normalizedRequired = requiredRoles.map((r) => r.toLowerCase());

    // Si le rôle de l'utilisateur N'EST PAS dans la liste autorisée
    if (!normalizedRequired.includes(normalizedUserRole)) {
      // Cas spécial : L'Admin a accès à tout, même si pas listé explicitement (Super User)
      if (normalizedUserRole === ROLES.ADMIN.toLowerCase()) {
          return next();
      }
```

- [ ] **Step 2: Corriger les deux rôles morts/mal orthographiés dans la copie de travail**

Remplacer :

```javascript
                meta: { requiresAuth: true, roles: ['admin', 'laborantin', 'ToxicoManager', 'biologiste'] }
```

par :

```javascript
                meta: { requiresAuth: true, roles: ['admin', 'laborantin', 'ToxicoManager'] }
```

Remplacer :

```javascript
                meta: { requiresAuth: true, roles: ['admin', 'laborantin', 'ToxicoManager', 'assistant'] }
```

par :

```javascript
                meta: { requiresAuth: true, roles: ['admin', 'laborantin', 'ToxicoManager', 'Assistant'] }
```

Remplacer :

```javascript
                meta: { 
                  requiresAuth: true, 
                  roles: ['admin', 'biologiste', 'laborantin', 'ToxicoManager'] 
                }
```

par :

```javascript
                meta: { 
                  requiresAuth: true, 
                  roles: ['admin', 'laborantin', 'ToxicoManager'] 
                }
```

**Note :** ces trois lignes appartiennent au module labo, entièrement non commité (`HEAD` ne contient pas encore ces routes). Elles ne peuvent donc pas être isolées/commitées séparément à cette étape — elles seront commitées avec le reste du module labo par l'utilisateur. Cette étape corrige la copie de travail pour que le comportement soit correct dès maintenant en développement local.

- [ ] **Step 3: Isoler et stager uniquement le correctif du garde de navigation (existe déjà dans `HEAD`, contrairement au module labo)**

```bash
SCRATCH="C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad"
git show HEAD:ah2-admin-web/src/router/index.js > "$SCRATCH/router_base_c1.js"
python - <<PYEOF
old = '''    if (!requiredRoles.includes(userRole)) {
      if (to.path !== '/forbidden') {'''
new = '''    const normalizedUserRole = (userRole || '').toLowerCase();
    const normalizedRequired = requiredRoles.map((r) => r.toLowerCase());

    if (!normalizedRequired.includes(normalizedUserRole)) {
      if (to.path !== '/forbidden') {'''
path = r"$SCRATCH/router_base_c1.js"
content = open(path, encoding="utf-8").read()
assert old in content, "pattern introuvable dans HEAD - le fichier a-t-il divergé davantage ?"
content = content.replace(old, new)
open(path, "w", encoding="utf-8").write(content)
print("ok")
PYEOF
BLOB=$(git hash-object -w "$SCRATCH/router_base_c1.js")
git update-index --cacheinfo 100644,$BLOB,ah2-admin-web/src/router/index.js
git diff --cached -- ah2-admin-web/src/router/index.js
```

Vérifier que le diff affiché ne contient **que** ce hunk (normalisation de la comparaison), rien sur le reste du fichier (imports, module labo, etc.).

- [ ] **Step 4: Vérifier le build**

```bash
cd ah2-admin-web
npm run build
cd -
```

Attendu : succès (le build porte sur la copie de travail complète, avec le module labo non commité — c'est normal et attendu, ce n'est pas ce qui est vérifié ici, seulement l'absence d'erreur de syntaxe introduite par cette étape).

- [ ] **Step 5: Commit**

```bash
git commit -m "fix(web): comparaison de roles insensible a la casse (WEB-04)

Le garde de navigation comparait authStore.userRole (casse exacte de
la base) a des tableaux de roles ecrits a la main sans normalisation.
Corrige : comparaison en minuscules des deux cotes.

router/index.js porte un module labo entier non commite dans la copie
de travail, avec deux roles morts/mal orthographies ('biologiste' qui
n'existe dans aucune ligne de la base, 'assistant' en minuscule alors
que la base stocke 'Assistant'). Corriges dans la copie de travail
pour un comportement correct en developpement local, mais non
commites ici : ce contenu n'existe pas encore sur HEAD, il sera
commite avec le reste du module labo par l'utilisateur.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Corriger le compte `secretaire1`

**Files:** aucun (opération base de données uniquement)

**Interfaces:**
- Consumes: Task 1 (le rôle `secretaire` doit déjà être un canonical reconnu — c'était déjà le cas avant ce chantier, cette tâche n'a donc pas de dépendance stricte sur les tâches précédentes)
- Produces: rien

- [ ] **Step 1: Confirmer l'état actuel avant modification**

```bash
PGPASSWORD='<mot_de_passe_postgres_actuel>' "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -d AH2 -c "SELECT username, role_id FROM users WHERE username = 'secretaire1';"
```

Attendu : `role_id` est `NULL` (confirme l'état constaté pendant la rédaction de la spec).

- [ ] **Step 2: Appliquer la correction**

```bash
PGPASSWORD='<mot_de_passe_postgres_actuel>' "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -d AH2 -c "UPDATE users SET role_id = (SELECT role_id FROM application_roles WHERE role_name = 'secretaire') WHERE username = 'secretaire1';"
```

Attendu : `UPDATE 1`.

- [ ] **Step 3: Vérifier**

```bash
PGPASSWORD='<mot_de_passe_postgres_actuel>' "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -d AH2 -c "SELECT u.username, r.role_name FROM users u JOIN application_roles r ON r.role_id = u.role_id WHERE u.username = 'secretaire1';"
```

Attendu : une ligne, `secretaire1 | secretaire`.

- [ ] **Step 4: Pas de commit** — modification de donnée en base, aucun fichier à committer pour cette étape.

---

## Task 6: Vérification finale de bout en bout

**Files:** aucun (vérification uniquement)

- [ ] **Step 1: Suite de tests complète**

```bash
pytest tests/ -v
```

Attendu : tous les tests passent, y compris les 8 nouveaux (5 de Task 1 + 3 de Task 2). Les 3 échecs pré-existants (`test_patient_repo.py`, `test_prescription_repo.py`, cf. chantier 0) restent présents et non liés à ce chantier — à confirmer qu'aucun nouvel échec n'apparaît.

- [ ] **Step 2: Vérification manuelle par connexion réelle — comptes précédemment verrouillés**

Démarrer l'API, puis pour `kouam2` (Psychologist) et `thegoat` (Assistant) — mots de passe connus de l'utilisateur, non rotés par ce chantier :

```bash
curl -s -X POST http://127.0.0.1:8000/auth/login -d "username=kouam2&password=<mot_de_passe>" -w "\nHTTP:%{http_code}\n"
curl -s -X POST http://127.0.0.1:8000/auth/login -d "username=thegoat&password=<mot_de_passe>" -w "\nHTTP:%{http_code}\n"
```

Attendu : `200` pour les deux, avec un token contenant `"roles":["psychologist"]` et `"roles":["assistant"]` respectivement (décoder le payload JWT pour vérifier, ou passer par `/auth/me`).

- [ ] **Step 3: Vérification manuelle — `secretaire1`**

```bash
curl -s -X POST http://127.0.0.1:8000/auth/login -d "username=secretaire1&password=<mot_de_passe>" -w "\nHTTP:%{http_code}\n"
```

Attendu : `200`, rôle `secretaire` dans le token.

- [ ] **Step 4: Récapitulatif**

Confirmer un par un :
- [ ] `role_map.py` couvre les 9 rôles + `manager` réservé, 5 tests passent
- [ ] `role_required()` n'a plus de repli permissif, `manager` reste fonctionnel, 3 tests passent
- [ ] `routes/core/permissions.py` supprimé, API démarre toujours
- [ ] Garde de navigation front insensible à la casse, build réussit
- [ ] `secretaire1` a le rôle `secretaire` en base
- [ ] `kouam2` et `thegoat` se connectent avec leur rôle correctement résolu
- [ ] `get_current_user()` n'a subi aucune modification par ce chantier — vérifier que `git log -p --follow -- api_backend/backend_app/routes/auth/auth_endpoints.py` sur les commits de ce chantier (ceux dont le message commence par le sujet de la Task 2) ne montre de diff que sur `role_required()`, jamais sur `get_current_user()`
