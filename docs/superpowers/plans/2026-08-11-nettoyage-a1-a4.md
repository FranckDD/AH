# Nettoyage A1-A4 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corriger 4 découvertes indépendantes issues des chantiers précédents, sans dépendance au travail en cours de l'utilisateur : fuseau horaire JWT, trigger non idempotent, tables non modélisées exposées à l'autogénération, CSP absent.

**Architecture:** Chaque correctif est isolé et indépendant des 3 autres — aucune interface partagée entre les tâches.

**Tech Stack:** Python, Alembic, PostgreSQL, FastAPI, Vue.

## Global Constraints

- `api_backend/backend_app/routes/auth/auth_endpoints.py` porte du travail en cours (repli permissif non commité sur `get_current_user()`) — `login()` en est identique à `HEAD`, isolable comme aux chantiers précédents.
- `api_backend/backend_app/main.py` porte du travail en cours (config CORS) — la section middleware d'en-têtes en est identique à `HEAD`, isolable.
- `alembic/env.py` est propre (aucun travail en cours dessus) — éditable directement.

---

## Task 1 (A1): Fuseau horaire du JWT

**Files:**
- Modify: `api_backend/backend_app/routes/auth/auth_endpoints.py` (isolation requise — voir Global Constraints)
- Test: `tests/test_jwt_lifecycle.py` (existant, étendu)

**Interfaces:**
- Consumes: rien
- Produces: rien consommé par une tâche suivante

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_jwt_lifecycle.py` :

```python
def test_login_issues_token_with_correct_utc_expiry():
    import time
    from unittest.mock import MagicMock, patch
    from fastapi.testclient import TestClient
    from fastapi.security import OAuth2PasswordRequestForm

    fake_user = make_fake_user(user_id=1, token_version=0)
    fake_user.application_role = None

    fake_ctrl = MagicMock()
    fake_ctrl.authenticate.return_value = fake_user

    with patch.object(auth_mod, "AuthController", return_value=fake_ctrl):
        app = FastAPI()
        app.include_router(auth_mod.router)

        client = TestClient(app)
        before = time.time()
        resp = client.post(
            "/auth/login",
            data={"username": "admin_test", "password": "whatever"},
        )
        after = time.time()

    assert resp.status_code == 200
    token = resp.json()["access_token"]
    payload = jose_jwt.decode(
        token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
        issuer=auth_mod.JWT_ISSUER, audience=auth_mod.JWT_AUDIENCE,
    )

    from api_backend.backend_app.config import JWT_EXPIRE_MINUTES
    expected_exp = before + JWT_EXPIRE_MINUTES * 60
    # tolerance de 5s pour le temps d'execution du test, pas pour le bug de fuseau
    # (le bug de fuseau introduit un ecart de plusieurs minutes selon le fuseau serveur)
    assert abs(payload["exp"] - expected_exp) < 5
    assert payload["exp"] <= after + JWT_EXPIRE_MINUTES * 60 + 5
```

Note : ce test nécessite que `/auth/login` fonctionne dans une app FastAPI isolée avec le rate limiter — vérifier que `limiter` (dépendance de `login()`) ne bloque pas le test (le rate limiter est basé sur l'IP source, un `TestClient` unique par test ne devrait pas accumuler de requêtes).

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

```bash
pytest tests/test_jwt_lifecycle.py::test_login_issues_token_with_correct_utc_expiry -v
```

Attendu : échoue avec un écart de l'ordre de l'heure entre `payload["exp"]` et `expected_exp` (dépend du fuseau de la machine — sur cette machine, UTC+1, l'écart observé sera d'environ 3600 secondes).

- [ ] **Step 3: Appliquer le correctif**

Dans `api_backend/backend_app/routes/auth/auth_endpoints.py`, remplacer :

```python
    # construire le token (sub + roles + exp + hygiene JWT : ver/jti/iss/aud)
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)
```

par :

```python
    # construire le token (sub + roles + exp + hygiene JWT : ver/jti/iss/aud)
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

```bash
pytest tests/test_jwt_lifecycle.py -v
```

Attendu : tous les tests passent (les 4 existants + le nouveau).

- [ ] **Step 5: Isoler et stager (le fichier porte du travail en cours ailleurs)**

```bash
SCRATCH="C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad"
git show HEAD:api_backend/backend_app/routes/auth/auth_endpoints.py > "$SCRATCH/auth_endpoints_base_a1.py"
python - <<PYEOF
old = '''    # construire le token (sub + roles + exp + hygiene JWT : ver/jti/iss/aud)
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)'''
new = '''    # construire le token (sub + roles + exp + hygiene JWT : ver/jti/iss/aud)
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)'''
path = r"$SCRATCH/auth_endpoints_base_a1.py"
content = open(path, encoding="utf-8").read()
assert old in content, "pattern introuvable"
content = content.replace(old, new)
open(path, "w", encoding="utf-8").write(content)
print("ok")
PYEOF
BLOB=$(git hash-object -w "$SCRATCH/auth_endpoints_base_a1.py")
git update-index --cacheinfo 100644,$BLOB,api_backend/backend_app/routes/auth/auth_endpoints.py
git diff --cached -- api_backend/backend_app/routes/auth/auth_endpoints.py
```

Vérifier que le diff ne contient que cette ligne.

- [ ] **Step 6: Commit**

```bash
git add tests/test_jwt_lifecycle.py
git commit -m "fix(security): corriger le fuseau horaire de l'expiration JWT (A1)

datetime.utcnow() retourne un datetime naif interprete a tort comme
heure locale par .timestamp(). Sur un serveur non-UTC, la duree de
vie reelle du token etait plus courte que JWT_EXPIRE_MINUTES.
Remplace par datetime.now(timezone.utc), conscient du fuseau.

auth_endpoints.py porte du travail en cours non lie a ce correctif :
seule la ligne concernee est incluse dans ce commit (injection
directe dans l'index).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2 (A2): Trigger `create_metier_profile()` idempotent

**Files:**
- Create: `alembic/versions/<hash>_idempotent_metier_profile_trigger.py`

**Interfaces:**
- Consumes: rien
- Produces: fonction PostgreSQL `create_metier_profile()` mise à jour

- [ ] **Step 1: Créer une migration manuelle (pas d'autogénération — modification de fonction non détectée automatiquement)**

```bash
alembic revision -m "idempotent_metier_profile_trigger"
```

Attendu : un nouveau fichier apparaît dans `alembic/versions/`, chaîné sur la révision `6ea9b46b7a65` (baseline) via `down_revision`.

- [ ] **Step 2: Écrire le contenu de la migration**

Ouvrir le fichier généré et remplacer le corps de `upgrade()` et `downgrade()` :

```python
def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.create_metier_profile()
         RETURNS trigger
         LANGUAGE plpgsql
        AS $function$
        DECLARE
          role_nom TEXT;
        BEGIN
          SELECT ar.role_name
            INTO role_nom
            FROM public.application_roles ar
           WHERE ar.role_id = NEW.role_id;

          IF role_nom = 'medecin' THEN
            INSERT INTO public.doctor(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          ELSIF role_nom = 'nurse' THEN
            INSERT INTO public.nurse(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          ELSIF role_nom = 'secretaire' THEN
            INSERT INTO public.secretaire(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          ELSIF role_nom = 'admin' THEN
            INSERT INTO public.admin(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          ELSIF role_nom = 'laborantin' THEN
            INSERT INTO public.laborantin(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          END IF;

          RETURN NEW;
        END;
        $function$
    """)


def downgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.create_metier_profile()
         RETURNS trigger
         LANGUAGE plpgsql
        AS $function$
        DECLARE
          role_nom TEXT;
        BEGIN
          SELECT ar.role_name
            INTO role_nom
            FROM public.application_roles ar
           WHERE ar.role_id = NEW.role_id;

          IF role_nom = 'medecin' THEN
            INSERT INTO public.doctor(user_id) VALUES (NEW.user_id);
          ELSIF role_nom = 'nurse' THEN
            INSERT INTO public.nurse(user_id) VALUES (NEW.user_id);
          ELSIF role_nom = 'secretaire' THEN
            INSERT INTO public.secretaire(user_id) VALUES (NEW.user_id);
          ELSIF role_nom = 'admin' THEN
            INSERT INTO public.admin(user_id) VALUES (NEW.user_id);
          ELSIF role_nom = 'laborantin' THEN
            INSERT INTO public.laborantin(user_id) VALUES (NEW.user_id);
          END IF;

          RETURN NEW;
        END;
        $function$
    """)
```

- [ ] **Step 3: Appliquer la migration**

```bash
alembic upgrade head
```

Attendu : succès (cette migration, contrairement à la baseline, doit réellement s'exécuter — elle ne fait que remplacer une définition de fonction, aucune donnée n'est touchée).

- [ ] **Step 4: Vérifier avec un cas qui échouait avant le correctif**

Trouver un compte ayant déjà un profil métier (par exemple `secretaire1`, qui a un profil `secretaire` depuis mai 2025 d'après le chantier 1), et changer temporairement son rôle puis le remettre, via une requête SQL directe reproduisant ce que fait l'API :

```bash
PGPASSWORD='<mot_de_passe_postgres_actuel>' "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -d AH2 -c "
UPDATE users SET role_id = (SELECT role_id FROM application_roles WHERE role_name = 'nurse') WHERE username = 'secretaire1';
UPDATE users SET role_id = (SELECT role_id FROM application_roles WHERE role_name = 'secretaire') WHERE username = 'secretaire1';
"
```

Attendu : les deux `UPDATE` réussissent sans l'erreur `duplicate key value violates unique constraint` rencontrée au chantier 1 (qui avait nécessité de désactiver le trigger manuellement).

- [ ] **Step 5: Confirmer l'état final cohérent**

```bash
PGPASSWORD='<mot_de_passe_postgres_actuel>' "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -d AH2 -c "SELECT username, role_id FROM users WHERE username = 'secretaire1';"
```

Attendu : `role_id` correspond au rôle `secretaire` (état inchangé après l'aller-retour de vérification).

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/
git commit -m "fix(db): trigger create_metier_profile() idempotent (A2)

Ajoute ON CONFLICT (user_id) DO NOTHING aux 5 INSERT (doctor, nurse,
secretaire, admin, laborantin). Le trigger plantait auparavant sur
tout compte changeant vers un role deja pourvu d'un profil metier
(rencontre au chantier 1 sur secretaire1, contourne a l'epoque en
desactivant le trigger manuellement au lieu de corriger la cause).

Premiere migration Alembic reelle (execution via upgrade, pas stamp)
depuis la mise en place du chantier 2a.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3 (A3): Exclure les 17 tables non modélisées de l'autogénération

**Files:**
- Modify: `alembic/env.py` (fichier propre)

**Interfaces:**
- Consumes: rien
- Produces: `include_object` appliqué aux deux modes (`run_migrations_offline`, `run_migrations_online`)

- [ ] **Step 1: Ajouter la liste des tables exclues et la fonction de filtre**

Remplacer :

```python
target_metadata = Base.metadata
```

par :

```python
target_metadata = Base.metadata

# Tables reelles sans modele SQLAlchemy (decouvertes lors de la baseline,
# chantier 2a). Exclues de l'autogeneration pour ne jamais etre proposees
# a la suppression tant qu'elles n'ont pas de modele.
TABLES_WITHOUT_MODEL = {
    "admin", "doctor", "nurse", "secretaire", "laborantin",
    "audit_logs", "audit_user_actions_old", "audit_access_old",
    "permissions", "role_permissions", "motif_translations",
    "spiritual_sessions", "spiritual_attendance", "admissions",
    "psych_evaluations", "patient_contacts", "lab_results_audit",
}


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in TABLES_WITHOUT_MODEL:
        return False
    return True
```

- [ ] **Step 2: Passer `include_object` aux deux modes**

Remplacer :

```python
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
```

par :

```python
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
```

Remplacer :

```python
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
```

par :

```python
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            include_object=include_object,
        )
```

- [ ] **Step 3: Vérifier qu'une autogénération à blanc ne propose plus leur suppression**

```bash
alembic revision --autogenerate -m "verif_a3"
grep -c "drop_table" alembic/versions/*verif_a3*.py
```

Attendu : le fichier généré ne contient aucun `op.drop_table` pour les 17 tables listées (peut encore contenir d'autres différences pré-existantes sans rapport, cf. chantier 2a — ce n'est pas ce qui est vérifié ici).

```bash
grep -E "drop_table\('(admin|doctor|nurse|secretaire|laborantin|audit_logs|audit_user_actions_old|audit_access_old|permissions|role_permissions|motif_translations|spiritual_sessions|spiritual_attendance|admissions|psych_evaluations|patient_contacts|lab_results_audit)'" alembic/versions/*verif_a3*.py
```

Attendu : **aucune ligne**.

- [ ] **Step 4: Supprimer le fichier de vérification (ne pas le committer)**

```bash
rm alembic/versions/*verif_a3*.py
```

- [ ] **Step 5: Commit**

```bash
git add alembic/env.py
git commit -m "fix(db): exclure les 17 tables non modelisees de l'autogeneration (A3)

Decouvertes au chantier 2a : admin, doctor, nurse, secretaire,
laborantin, audit_logs et 11 autres tables reelles n'ont aucun
modele SQLAlchemy. Sans ce filtre, toute autogeneration future les
proposerait a la suppression - risque reel si quelqu'un execute une
migration generee sans lire attentivement son contenu.

Ne les rend pas gerables par l'ORM (hors perimetre) : empeche
seulement leur suppression accidentelle.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4 (A4): Content-Security-Policy

**Files:**
- Modify: `api_backend/backend_app/main.py` (isolation requise — voir Global Constraints)

**Interfaces:**
- Produces: en-tête `Content-Security-Policy` sur toute réponse

- [ ] **Step 1: Ajouter l'en-tête au middleware existant**

Remplacer :

```python
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response
```

par :

```python
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https://*.supabase.co; "
    "connect-src 'self' http://localhost:8000 http://127.0.0.1:8000"
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    if IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response
```

- [ ] **Step 2: Isoler et stager (le fichier porte du travail en cours ailleurs)**

```bash
SCRATCH="C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad"
git show HEAD:api_backend/backend_app/main.py > "$SCRATCH/main_base_a4.py"
python - <<PYEOF
old = '''@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response'''
new = '''CONTENT_SECURITY_POLICY = (
    "default-src \\'self\\'; "
    "script-src \\'self\\'; "
    "style-src \\'self\\' \\'unsafe-inline\\'; "
    "img-src \\'self\\' data: https://*.supabase.co; "
    "connect-src \\'self\\' http://localhost:8000 http://127.0.0.1:8000"
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    if IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response'''
path = r"$SCRATCH/main_base_a4.py"
content = open(path, encoding="utf-8").read()
assert old in content, "pattern introuvable"
content = content.replace(old, new)
open(path, "w", encoding="utf-8").write(content)
print("ok")
PYEOF
BLOB=$(git hash-object -w "$SCRATCH/main_base_a4.py")
git update-index --cacheinfo 100644,$BLOB,api_backend/backend_app/main.py
git diff --cached -- api_backend/backend_app/main.py
```

Vérifier que le diff ne contient que l'ajout du CSP, rien sur la section CORS.

- [ ] **Step 3: Build et test manuel en navigateur (obligatoire — un CSP cassé ne se voit pas forcément dans les logs serveur)**

```bash
cd ah2-admin-web
npm run build
npm run dev &
```

Démarrer aussi l'API (`uvicorn ...`). Ouvrir le navigateur sur l'URL du dev server, se connecter avec `admin_test`, et naviguer dans au moins 3 modules différents (dashboard, patients, un module labo ou toxico). Ouvrir la console développeur du navigateur (F12) et confirmer l'absence d'erreurs `Content-Security-Policy` (souvent affichées en rouge, mentionnant la directive violée).

- [ ] **Step 4: Si des violations apparaissent**

Ne pas les ignorer — noter la directive et la ressource bloquée, ajuster `CONTENT_SECURITY_POLICY` en conséquence (par exemple élargir `img-src` ou `connect-src` si une ressource légitime est bloquée), puis répéter Step 3 jusqu'à absence de violation.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(security): Content-Security-Policy (A4)

Politique calibree sur l'inventaire reel des ressources chargees par
la console Vue (verifie pendant le cadrage : aucun CDN externe,
aucune police externe, un seul domaine d'API). style-src inclut
'unsafe-inline', necessaire pour les liaisons :style de Vue.

Verifie par usage reel en navigateur (pas seulement curl -I) sur au
moins 3 modules, console developpeur sans violation CSP.

main.py porte du travail en cours non lie a ce correctif (config
CORS) : seul l'en-tete CSP est inclus dans ce commit (injection
directe dans l'index).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Vérification finale

**Files:** aucun (vérification uniquement)

- [ ] **Step 1: Suite de tests complète**

```bash
pytest tests/ -v
```

Attendu : tous les tests passent, y compris le nouveau de Task 1. Les échecs pré-existants et non liés restent identiques.

- [ ] **Step 2: L'API démarre toujours normalement**

```bash
PYTHONIOENCODING=utf-8 uvicorn api_backend.backend_app.main:app --port 8000 &
sleep 5
curl -s -o /dev/null -w "healthcheck: %{http_code}\n" http://127.0.0.1:8000/health
```

Attendu : `200`.

- [ ] **Step 3: `alembic current` reflète les deux migrations**

```bash
alembic current
alembic history
```

Attendu : la révision courante est celle du trigger idempotent (Task 2), chaînée après la baseline.

- [ ] **Step 4: Récapitulatif**

Confirmer un par un :
- [ ] A1 — token émis avec la bonne expiration UTC, quel que soit le fuseau serveur
- [ ] A2 — changement de rôle vers un rôle déjà pourvu d'un profil métier ne plante plus
- [ ] A3 — autogénération à blanc ne propose plus la suppression des 17 tables
- [ ] A4 — CSP actif, vérifié sans violation dans un navigateur réel sur plusieurs modules
- [ ] Aucun fichier de travail en cours de l'utilisateur n'a été altéré au-delà des hunks isolés prévus
