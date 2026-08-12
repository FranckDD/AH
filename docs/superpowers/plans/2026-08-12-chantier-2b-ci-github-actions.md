# Chantier 2b — CI (GitHub Actions) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire tourner la suite de tests d'intégration (~130 tests, livrée par 2d-0 à 2d-4) dans GitHub Actions, sur une base Postgres 17 fraîche à chaque run, sans jamais toucher la base `AH2` de développement locale.

**Architecture:** Le workflow ne fait jamais tourner `alembic upgrade head` contre une base neuve (la migration baseline contient ~70 `DROP` générés par autogénération contre une base déjà peuplée — voir Corrections empiriques). À la place : un service Postgres 17 neuf est provisionné en restaurant un **dump schéma-seulement** (`ci/schema_only.sql`, capture fidèle et à jour de la base `AH2` locale réelle) puis en seedant les **9 lignes de référence** `application_roles` (`ci/seed_application_roles.sql`) dont dépendent les fixtures de test elles-mêmes, puis en exécutant `alembic stamp head` (marque l'historique comme à jour sans rien exécuter — même principe que la base `AH2` réelle, jamais migrée pour de vrai depuis sa baseline).

**Tech Stack:** GitHub Actions, service container `postgres:17`, Python 3.12, `pip`, Alembic, pytest.

## Global Constraints

- Versions exactes des 4 paquets manquants (validées dans l'environnement de dev actuel, tous les tests y passent) : `slowapi==0.1.9`, `limits==5.8.0`, `Deprecated==1.3.1`, `fpdf2==2.8.3`.
- Workflow déclenché sur `push` et `pull_request` vers `AH2_V3-1`.
- Python 3.12, Postgres 17.
- Variables d'environnement requises par l'application (`api_backend/backend_app/config.py`) : `DATABASE_URL` (obligatoire, sinon `RuntimeError`), `JWT_SECRET` (obligatoire, sinon `RuntimeError`), `JWT_ALGORITHM` (obligatoire pour que `python-jose` fonctionne — pas de valeur par défaut dans le code, contrairement à `JWT_EXPIRE_MINUTES` qui retombe sur `60`). Utiliser `JWT_ALGORITHM=HS256` (valeur de `.env` local) et un `JWT_SECRET` factice codé en dur dans le workflow, jamais le secret réel.
- **Ordre impératif de provisionnement de la base CI** : créer le rôle Postgres `app_medical` **avant** de restaurer `ci/schema_only.sql` — le schéma contient `CREATE POLICY medical_policy ON public.patients TO app_medical USING (true)`, qui échoue si le rôle n'existe pas encore (découvert empiriquement pendant le cadrage de ce plan, absent de la spec initiale).
- **Ne jamais exécuter `alembic upgrade head` contre une base neuve, ni en CI ni ailleurs** — utiliser exclusivement `alembic stamp head` après restauration du schéma. Voir Corrections empiriques ci-dessous pour la raison précise.
- Aucune tâche de ce plan n'exécute de DDL ni de commande Alembic contre la base `AH2` locale réelle — cette étape a déjà été réalisée et vérifiée par le contrôleur avant l'écriture de ce plan (voir Corrections empiriques). Les tâches 2 et 3 ne font que committer des fichiers déjà générés et déjà vérifiés ; aucun sub-agent de ce plan n'a besoin d'accès à la base `AH2` réelle.

## Corrections empiriques par rapport à la spec

La spec (`docs/superpowers/specs/2026-08-12-chantier-2b-ci-github-actions-design.md`) prévoyait : (1) extraire les définitions manquantes du dump `ah2_v3_dashmedical.sql` tracké au dépôt, (2) les intégrer dans une migration Alembic chaînée, (3) vérifier que `alembic upgrade head` réussit contre une base neuve. Le cadrage empirique de ce plan a invalidé cette approche sur trois points, chacun vérifié directement contre une base isolée (jamais `AH2`) :

1. **Le dump tracké est périmé.** `update_patient`/`create_patient` y manquent les paramètres `p_is_clinical`/`p_is_toxicology`/`p_is_spiritual`, présents sur la base réelle et utilisés par `repositories/patient_repo.py`. Les définitions ont été extraites directement de la base `AH2` locale via `pg_get_functiondef()`/`pg_get_triggerdef()` (source vivante, vérifiée à jour), pas du dump.

2. **`alembic upgrade head` ne peut fondamentalement pas réussir contre une base neuve**, indépendamment du problème des procédures manquantes : la migration baseline (`6ea9b46b7a65_baseline.py`) contient environ 70 `op.drop_table`/`op.drop_index`/`op.drop_constraint`, générés par autogénération contre une base déjà peuplée. Contre une base vide, elle échoue immédiatement (`UndefinedTable: patient_contacts`). Corriger ces ~70 suppressions serait un chantier disproportionné par rapport à l'objectif (faire tourner la CI). **Stratégie retenue** : provisionner la base CI par restauration d'un dump schéma-seulement (`pg_dump --schema-only --no-owner --no-privileges` de la base `AH2` locale réelle — capture automatiquement les 54 tables et les 69 fonctions/procédures, sans dépendre d'aucune migration Alembic pour les créer), puis `alembic stamp head` pour marquer l'historique à jour sans rien exécuter. Exactement le même principe que celui déjà utilisé pour la baseline de la vraie base `AH2` (jamais exécutée pour de vrai, seulement stampée).

3. **Une migration Alembic réelle a quand même été écrite et appliquée pour de vrai** contre la base `AH2` locale (`alembic/versions/002_add_missing_procedures_triggers.py`, approuvé explicitement par l'utilisateur avant exécution) — non pas pour la CI (qui ne l'exécute jamais, elle stamp), mais pour que l'historique Alembic réel redevienne enfin exact : ces 4 procédures/fonctions + 4 fonctions de trigger + `current_user_id()` (dépendance cachée non documentée dans la spec, découverte via `track_patient_changes()`) existaient sur `AH2` depuis longtemps sans jamais avoir été suivies. Tout le corps de la migration est écrit en `CREATE OR REPLACE` (fonctions/procédures) et `CREATE OR REPLACE TRIGGER` (PG ≥ 14, confirmé PG 17.4 en local) — strictement idempotent, aucun `DROP`, sans risque même exécuté contre une base qui possède déjà ces objets. Appliquée et vérifiée : `AH2` réelle est maintenant stampée à `002_add_missing_procs`, suite de tests re-exécutée après coup (patients/prescriptions/caisse/retrait) — zéro régression introduite, les seuls échecs observés sont les 2 tests `test_patient_repo.py` déjà connus comme obsolètes (item ci-dessous) et le couplage WIP déjà documenté aux chantiers 2d-3/2d-4 (fichiers `controller/prescription_controller.py`, `controller/caisse_controller.py`, `repositories/caisse_repo.py`, `repositories/prescription_repo.py`, `controller/patient_controller.py` sont en travail non commité).

4. **Découverte supplémentaire, absente de la spec : la CI a aussi besoin de données de référence, pas seulement du schéma.** Un dump schéma-seulement contient zéro ligne dans **toutes** les tables, y compris les tables de configuration statique. `tests/conftest.py::create_test_user()` fait `session.query(ApplicationRole).filter_by(role_name=role_name).one()` — sans les 9 lignes de `application_roles` (`admin`, `medecin`, `nurse`, `secretaire`, `laborantin`, `Psychologist`, `SpiritualCounsellor`, `ToxicoManager`, `Assistant`), **toute** création d'utilisateur de test échoue (`NoResultFound`), donc quasiment tous les tests échouent en cascade. Vérifié : sans le seed, 88 tests échouent sur la base CI reconstruite ; avec le seed (`ci/seed_application_roles.sql`, extrait via `pg_dump --data-only -t application_roles`), 12 échouent — exactement les 2 tests connus obsolètes + le couplage WIP déjà documenté, zéro échec inexpliqué. `medical_specialties` n'est pas nécessaire : le trigger `set_default_specialty()` qui la consulte ne se déclenche que si `postgres_role = 'app_medical'`, jamais le cas pour les utilisateurs créés par `create_test_user()` (`postgres_role` non renseigné).

5. **Vérification end-to-end complète, réalisée avant l'écriture de ce plan** : une seconde instance Postgres 17 jetable (répertoire de données et port dédiés, jamais la base `AH2` réelle) a été démarrée, une base nommée littéralement `AH2` y a été créée (miroir exact de ce qu'un service GitHub Actions avec `POSTGRES_DB: AH2` produit), le rôle `app_medical` créé, `ci/schema_only.sql` puis `ci/seed_application_roles.sql` restaurés, `alembic stamp head` exécuté, puis la suite `pytest tests/ -v` complète lancée contre cette base : **118 passed, 12 failed** — les 12 échecs sont exactement les 2 tests connus obsolètes + le couplage WIP déjà documenté à l'identique. Contre un `HEAD` propre (sans travail en cours), la CI serait verte à l'exception des 2 `xfail` prévus.

## Limite connue à documenter (hors périmètre de correction, pas hors périmètre de mention)

`ci/schema_only.sql` et `ci/seed_application_roles.sql` sont des instantanés figés de la base `AH2` locale au moment de ce chantier. Toute future migration Alembic qui modifie réellement le schéma (nouvelle table, colonne, procédure) devra être accompagnée d'une régénération manuelle de ces deux fichiers, sinon la CI continuera de stamper un historique qui ne correspond plus à ce qu'elle a réellement provisionné — silencieusement. Documenté dans `SUIVI-AVANCEMENT.md` (Tâche 6) comme nouvel item de registre, pas corrigé ici (aucune régénération automatique n'existe, ce serait un chantier séparé disproportionné pour l'objectif actuel).

## File Structure

- Modify: `requirements.txt` — ajout des 4 paquets manquants
- Create (déjà écrit et déjà appliqué pour de vrai contre `AH2` locale, committer tel quel) : `alembic/versions/002_add_missing_procedures_triggers.py`
- Create (déjà généré et déjà vérifié, committer tel quel) : `ci/schema_only.sql`, `ci/seed_application_roles.sql`
- Create: `.github/workflows/ci.yml`
- Modify: `tests/test_patient_repo.py` — `xfail` sur les 2 tests connus obsolètes
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md` — clôture `D2`, nouveau registre `G` (découvertes de ce chantier), mise à jour de "Prochaine étape"

**Note pour le contrôleur (pas une tâche d'implémenteur) :** `alembic/versions/002_add_missing_procedures_triggers.py`, `ci/schema_only.sql` et `ci/seed_application_roles.sql` existent déjà comme fichiers non suivis dans le checkout principal. Avant de dispatcher la Tâche 2 et la Tâche 3, copier ces trois fichiers depuis le checkout principal vers le worktree isolé de ce plan (`cp` simple, même machine, aucun accès base de données requis). Les implémenteurs de ces deux tâches ne font que vérifier la présence du fichier et le committer — ils ne le régénèrent jamais et n'exécutent aucune commande contre une base de données.

---

### Task 1: `requirements.txt` — ajouter les 4 paquets manquants

**Files:**
- Modify: `requirements.txt`
- Test: aucun test dédié — vérifié par le succès de `pip install -r requirements.txt` en Tâche 4 (CI) et par le fait que l'environnement de dev actuel (qui a déjà ces 4 paquets) fait passer toute la suite

**Interfaces:**
- Consumes: rien
- Produces: rien (fichier de config, pas de code consommé par une autre tâche)

- [ ] **Step 1: Lire `requirements.txt` et localiser la section `# === Tests ===`**

Le fichier actuel (sur `HEAD`) contient notamment :
```
# === Tests ===
pytest==8.2.2
httpx==0.27.0
```

- [ ] **Step 2: Ajouter les 4 paquets manquants dans une nouvelle section dédiée, juste après la section `# === Tests ===`**

```
# === Rate limiting (SEC-05) ===
slowapi==0.1.9
limits==5.8.0
Deprecated==1.3.1

# === Génération PDF factures ===
fpdf2==2.8.3
```

Ne modifier aucune autre ligne du fichier.

- [ ] **Step 3: Vérifier que le fichier reste syntaxiquement valide**

Run: `pip install -r requirements.txt --dry-run 2>&1 | tail -20` (ou, si `--dry-run` indisponible sur la version de pip installée, `python -c "import pkg_resources; [print(l) for l in open('requirements.txt') if l.strip() and not l.startswith('#')]"` pour confirmer qu'aucune ligne n'est malformée).

Expected: aucune erreur de parsing.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add slowapi, limits, Deprecated, fpdf2 to requirements.txt"
```

---

### Task 2: Committer la migration Alembic `002_add_missing_procedures_triggers.py`

**Files:**
- Create (fichier déjà présent dans le worktree, copié par le contrôleur avant dispatch — ne pas régénérer) : `alembic/versions/002_add_missing_procedures_triggers.py`

**Interfaces:**
- Consumes: rien
- Produces: la révision Alembic `002_add_missing_procs` (chaînée après `001_fix_delete_patient`), consommée par la Tâche 4 (le workflow CI exécute `alembic stamp head`, qui doit pointer vers cette révision)

- [ ] **Step 1: Vérifier que le fichier existe déjà dans le worktree**

Run: `ls alembic/versions/002_add_missing_procedures_triggers.py`

Expected: le fichier existe (copié par le contrôleur depuis le checkout principal avant dispatch de cette tâche — voir la note contrôleur dans File Structure).

**Ne pas modifier le contenu de ce fichier.** Il a déjà été écrit, appliqué pour de vrai contre la base `AH2` locale avec l'accord explicite de l'utilisateur, et vérifié (suite de tests re-exécutée après application, zéro régression). Réexécuter ou modifier cette migration contre une base de données quelconque n'est **pas** le rôle de cette tâche.

- [ ] **Step 2: Vérifier que la révision s'enchaîne correctement dans l'historique Alembic (lecture statique uniquement, aucune connexion base de données)**

Run: `grep -n "^revision\|^down_revision" alembic/versions/002_add_missing_procedures_triggers.py alembic/versions/001_fix_delete_patient_procedure.py`

Expected :
```
alembic/versions/002_add_missing_procedures_triggers.py:revision: str = '002_add_missing_procs'
alembic/versions/002_add_missing_procedures_triggers.py:down_revision: Union[str, Sequence[str], None] = '001_fix_delete_patient'
alembic/versions/001_fix_delete_patient_procedure.py:revision: str = '001_fix_delete_patient'
```

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/002_add_missing_procedures_triggers.py
git commit -m "feat: track create_patient, update_patient, create/update_prescription and 4 trigger functions in Alembic history

Ces objets existaient deja sur AH2 hors historique Alembic. Definitions
extraites de la base live (pg_get_functiondef/pg_get_triggerdef), pas du
dump ah2_v3_dashmedical.sql (perime). Ecrit en CREATE OR REPLACE partout :
idempotent, deja applique et verifie contre AH2 locale (zero regression)."
```

---

### Task 3: Committer les artefacts de provisionnement CI (`ci/schema_only.sql`, `ci/seed_application_roles.sql`)

**Files:**
- Create (fichiers déjà présents dans le worktree, copiés par le contrôleur avant dispatch — ne pas régénérer) : `ci/schema_only.sql`, `ci/seed_application_roles.sql`

**Interfaces:**
- Consumes: rien
- Produces: les deux fichiers restaurés par le workflow CI en Tâche 4, dans cet ordre exact (schéma puis données) après création du rôle `app_medical`

- [ ] **Step 1: Vérifier que les deux fichiers existent déjà dans le worktree**

Run: `ls -la ci/schema_only.sql ci/seed_application_roles.sql`

Expected: les deux fichiers existent (`schema_only.sql` fait environ 4200 lignes, `seed_application_roles.sql` une trentaine de lignes avec une commande `COPY application_roles ... FROM stdin;` suivie de 9 lignes de données).

**Ne régénérer ni modifier le contenu d'aucun des deux fichiers.** Ils ont été générés par le contrôleur directement depuis la base `AH2` locale réelle (`pg_dump --schema-only --no-owner --no-privileges` et `pg_dump --data-only -t application_roles --no-owner --no-privileges`) et déjà vérifiés bout en bout (restauration propre + `alembic stamp head` + suite `pytest` complète contre une instance Postgres jetable dédiée — voir Corrections empiriques). Cette tâche ne fait que les committer.

- [ ] **Step 2: Vérifier qu'aucun des deux fichiers ne contient de donnée autre que le rôle `application_roles` (garde-fou : aucune donnée patient/utilisateur réelle ne doit être committée)**

Run: `grep -c "^COPY " ci/seed_application_roles.sql`

Expected: `1` (une seule commande `COPY`, portant sur `application_roles`). Si ce nombre est différent de `1`, ou si `grep "^COPY " ci/seed_application_roles.sql` révèle une table autre que `application_roles`, **arrêter la tâche et remonter au contrôleur** — ne jamais committer un dump de données contenant potentiellement des informations patients.

- [ ] **Step 3: Commit**

```bash
git add ci/schema_only.sql ci/seed_application_roles.sql
git commit -m "chore: add CI database provisioning artifacts (schema-only dump + application_roles seed)

Snapshot fige de la base AH2 locale reelle, utilise par le workflow CI
pour provisionner une base fraiche sans dependre d'alembic upgrade head
(la migration baseline contient ~70 DROP incompatibles avec une base vide).
A regenerer manuellement apres toute future migration modifiant le schema."
```

---

### Task 4: Workflow GitHub Actions (`.github/workflows/ci.yml`)

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `requirements.txt` (Task 1), `alembic/versions/002_add_missing_procedures_triggers.py` (Task 2, via `alembic stamp head`), `ci/schema_only.sql` + `ci/seed_application_roles.sql` (Task 3)
- Produces: le workflow CI lui-même, déclenché sur push/PR

- [ ] **Step 1: Créer le répertoire et le fichier de workflow**

Créer `.github/workflows/ci.yml` avec le contenu suivant, exact et complet :

```yaml
name: CI

on:
  push:
    branches: [AH2_V3-1]
  pull_request:
    branches: [AH2_V3-1]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: AH2
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10

    env:
      DATABASE_URL: postgresql://postgres:postgres@localhost:5432/AH2
      JWT_SECRET: ci-only-fake-secret-never-use-in-production-a1b2c3d4
      JWT_ALGORITHM: HS256

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Create app_medical role (RLS policy dependency)
        run: psql "$DATABASE_URL" -c "CREATE ROLE app_medical;"

      - name: Restore schema (schema-only, no data)
        run: psql "$DATABASE_URL" -f ci/schema_only.sql

      - name: Seed application_roles reference data
        run: psql "$DATABASE_URL" -f ci/seed_application_roles.sql

      - name: Stamp Alembic history (schema already matches head, never run migrations against a fresh DB)
        run: python -m alembic stamp head

      - name: Run test suite
        run: python -m pytest tests/ -v
```

- [ ] **Step 2: Vérifier la syntaxe YAML localement (aucune connexion réseau/base de données requise)**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "YAML valide"`

Expected: `YAML valide`, aucune exception.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow (Postgres 17 service, schema restore + stamp, pytest)"
```

**Note pour le contrôleur (pas pour l'implémenteur) :** ce step ne peut pas être vérifié par un run réel de GitHub Actions depuis un sub-agent (pousser une branche est une action visible/partagée nécessitant l'accord explicite de l'utilisateur — hors périmètre d'un sub-agent). La vérification réelle (`Vérification` de la spec : "le workflow lui-même est vérifié via un push réel... pas seulement lu comme YAML plausible") a lieu après le merge de ce plan, au moment de `finishing-a-development-branch`, si l'utilisateur choisit de pousser la branche.

---

### Task 5: `xfail` les 2 tests connus obsolètes de `test_patient_repo.py`

**Files:**
- Modify: `tests/test_patient_repo.py:19` (`test_update_patient_success`), `tests/test_patient_repo.py:42` (`test_update_patient_not_found`)

**Interfaces:**
- Consumes: rien
- Produces: rien

- [ ] **Step 1: Lire l'état actuel des deux tests**

```python
def test_update_patient_success():
    repo, mock_session = make_repo_with_mock_session()

    patient = MagicMock()
    patient.id = 1
    patient.first_name = "Alice"

    mock_session.query.return_value.filter.return_value.one_or_none.return_value = patient

    data = {
        "first_name": "Alicia",
        "residence": "Douala"
    }

    res = repo.update_patient(patient_id=1, data=data, current_user={"id": 99, "name": "admin"})
    assert res is not None
    assert patient.first_name == "Alicia"
    assert patient.residence == "Douala"
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once_with(patient)

def test_update_patient_not_found():
    repo, mock_session = make_repo_with_mock_session()

    mock_session.query.return_value.filter.return_value.one_or_none.return_value = None

    res = repo.update_patient(patient_id=999, data={"first_name": "X"}, current_user={"id": 1})
    assert res is None
    mock_session.commit.assert_not_called()
```

- [ ] **Step 2: Ajouter le marqueur `xfail` avec raison renvoyant au registre, sur les deux tests**

```python
@pytest.mark.xfail(
    reason="Test pre-existant obsolete, sans lien avec les chantiers de securite/CI. "
    "Voir docs/superpowers/SUIVI-AVANCEMENT.md, 'Autres points ouverts'.",
    strict=False,
)
def test_update_patient_success():
    repo, mock_session = make_repo_with_mock_session()

    patient = MagicMock()
    patient.id = 1
    patient.first_name = "Alice"

    mock_session.query.return_value.filter.return_value.one_or_none.return_value = patient

    data = {
        "first_name": "Alicia",
        "residence": "Douala"
    }

    res = repo.update_patient(patient_id=1, data=data, current_user={"id": 99, "name": "admin"})
    assert res is not None
    assert patient.first_name == "Alicia"
    assert patient.residence == "Douala"
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once_with(patient)

@pytest.mark.xfail(
    reason="Test pre-existant obsolete, sans lien avec les chantiers de securite/CI. "
    "Voir docs/superpowers/SUIVI-AVANCEMENT.md, 'Autres points ouverts'.",
    strict=False,
)
def test_update_patient_not_found():
    repo, mock_session = make_repo_with_mock_session()

    mock_session.query.return_value.filter.return_value.one_or_none.return_value = None

    res = repo.update_patient(patient_id=999, data={"first_name": "X"}, current_user={"id": 1})
    assert res is None
    mock_session.commit.assert_not_called()
```

`strict=False` : si l'un de ces deux tests se met un jour à passer (par exemple si `repositories/patient_repo.py::update_patient` change), pytest le rapporte comme `XPASS` sans faire échouer la CI — signal visible sans bloquer personne.

`pytest.mark` est déjà importé (`import pytest` en tête de fichier, ligne 3) — aucun nouvel import nécessaire.

- [ ] **Step 3: Exécuter les deux tests pour confirmer qu'ils sont bien comptés `xfail`, pas `failed`**

Run: `python -m pytest tests/test_patient_repo.py -v`

Expected: `test_update_patient_success XFAIL` et `test_update_patient_not_found XFAIL`, code de sortie `0` (un `xfail` non strict ne fait pas échouer pytest).

- [ ] **Step 4: Commit**

```bash
git add tests/test_patient_repo.py
git commit -m "test: mark 2 known-obsolete test_patient_repo.py tests as xfail

Non lies aux chantiers de securite/CI, deja documentes au registre
SUIVI-AVANCEMENT.md avant ce chantier. La CI reste verte, le probleme
reste visible et trace (XFAIL dans le rapport pytest), pas cache."
```

---

### Task 6: Mettre à jour `docs/superpowers/SUIVI-AVANCEMENT.md`

**Files:**
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md`

**Interfaces:**
- Consumes: le contenu final de toutes les tâches précédentes (pour référencer les bons chemins de fichiers)
- Produces: rien

- [ ] **Step 1: Mettre à jour la ligne `D2` (section "D — Écarts révélés par l'incident `delete_patient`") pour refléter la résolution**

Remplacer la ligne actuelle :
```
| D2 | La migration baseline (`6ea9b46b7a65_baseline.py`) ne contient aucune définition `FUNCTION`/`PROCEDURE` — un `alembic upgrade head` sur une base neuve donnerait des tables sans les fonctions/procédures stockées `create_patient()`/`update_patient()`/`delete_patient()` : le module patients (et les tests de ce chantier) ne peut pas tourner contre une base fraîchement provisionnée. | `alembic/versions/6ea9b46b7a65_baseline.py` | Bloque le chantier 2b (CI) tant que non traité |
```

Par :
```
| D2 | ~~La migration baseline ne contenait aucune définition `FUNCTION`/`PROCEDURE`.~~ **Résolu au chantier 2b** : `create_patient`/`update_patient`/`create_prescription`/`update_prescription` + 4 fonctions de trigger + `current_user_id()` (dépendance cachée) désormais suivies (`alembic/versions/002_add_missing_procedures_triggers.py`, appliquée pour de vrai contre `AH2` locale, `CREATE OR REPLACE` partout donc idempotente). `delete_patient` restait déjà couvert depuis 2d-2. La baseline elle-même (`6ea9b46b7a65_baseline.py`, ~70 `DROP` générés par autogénération) reste inutilisable contre une base vide — voir `G1` : la CI la contourne, ne la corrige pas. | `alembic/versions/002_add_missing_procedures_triggers.py` | Résolu pour l'usage réel et pour la CI ; la baseline elle-même reste un `DROP`-miné non exécutable tel quel contre une base neuve |
```

- [ ] **Step 2: Ajouter une nouvelle section de registre `G` après la section `F` (avant "### Autres points ouverts, hors registre A/B/C")**

Insérer ce bloc juste avant la ligne `### Autres points ouverts, hors registre A/B/C` :

```markdown
### G — Découvertes du chantier 2b (CI GitHub Actions)

| # | Découverte | Fichier | Gravité / statut |
|---|---|---|---|
| G1 | La migration baseline (`6ea9b46b7a65_baseline.py`) contient environ 70 `op.drop_table`/`op.drop_index`/`op.drop_constraint`, générés par autogénération contre une base déjà peuplée. Contre une base Postgres neuve et vide, `alembic upgrade head` échoue immédiatement (`UndefinedTable: patient_contacts`). Corriger individuellement ces ~70 suppressions serait disproportionné par rapport à l'objectif de ce chantier. | `alembic/versions/6ea9b46b7a65_baseline.py` | Non corrigé — contourné en CI par restauration d'un dump schéma-seulement (`ci/schema_only.sql`) + `alembic stamp head`, jamais `upgrade head`, contre une base neuve |
| G2 | Le schéma contient une politique RLS (`CREATE POLICY medical_policy ON public.patients TO app_medical USING (true)`) référençant le rôle Postgres `app_medical`. Un dump `--no-owner --no-privileges` ne supprime pas cette dépendance (ce n'est pas une métadonnée de propriété, c'est une vraie référence d'objet) — restaurer `ci/schema_only.sql` échoue si le rôle n'existe pas déjà. | `ci/schema_only.sql`, `.github/workflows/ci.yml` | Résolu — le workflow crée le rôle avant de restaurer le schéma |
| G3 | Un dump schéma-seulement contient zéro ligne dans toutes les tables, y compris les tables de configuration statique. `tests/conftest.py::create_test_user()` dépend de 9 lignes dans `application_roles` pour résoudre `role_name` → `role_id` ; sans elles, toute création d'utilisateur de test échoue en cascade (`NoResultFound`), soit la quasi-totalité de la suite. | `tests/conftest.py`, `ci/seed_application_roles.sql` | Résolu — seed dédié restauré après le schéma, avant `alembic stamp head` |
| G4 | `ci/schema_only.sql` et `ci/seed_application_roles.sql` sont des instantanés figés de `AH2` locale au moment de ce chantier. Toute future migration Alembic modifiant réellement le schéma doit être accompagnée d'une régénération manuelle de ces deux fichiers (`pg_dump --schema-only`/`--data-only -t application_roles`), sinon la CI stampera silencieusement un historique qui ne correspond plus à ce qu'elle a réellement provisionné. | `ci/schema_only.sql`, `ci/seed_application_roles.sql` | Limitation connue, non automatisée — à surveiller à chaque nouvelle migration touchant le schéma |
```

- [ ] **Step 3: Mettre à jour la ligne sur les 2 tests pré-existants dans "Autres points ouverts, hors registre A/B/C"**

Remplacer :
```
- **2 tests pré-existants en échec** (`test_patient_repo.py`), sans lien avec les chantiers de sécurité.
```

Par :
```
- **2 tests pré-existants obsolètes** (`test_patient_repo.py::test_update_patient_success`, `test_update_patient_not_found`), sans lien avec les chantiers de sécurité — marqués `xfail` au chantier 2b (`strict=False`) : visibles dans le rapport pytest sans faire échouer la CI.
```

- [ ] **Step 4: Mettre à jour "Prochaine étape"**

Remplacer :
```
Chantier **2b — CI (GitHub Actions)**, puis reconsidérer **2c** (toujours bloqué). Ensuite : audit des versions Vue/Tailwind/dépendances front.
```

Par :
```
Chantier **2b — CI (GitHub Actions)** terminé (voir registre `G` pour les découvertes). Reconsidérer **2c** (toujours bloqué). Ensuite : audit des versions Vue/Tailwind/dépendances front.
```

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/SUIVI-AVANCEMENT.md
git commit -m "docs: close out chantier 2b in SUIVI-AVANCEMENT.md (registry G, D2 resolved)"
```

---

## Vérification finale (contrôleur, après la revue de branche complète)

- `alembic stamp head` réussit contre une base Postgres 17 entièrement neuve provisionnée par `ci/schema_only.sql` + `ci/seed_application_roles.sql` (déjà vérifié pendant le cadrage de ce plan — la revue finale de branche doit confirmer que rien dans les Tâches 1-6 n'a modifié ces fichiers).
- `pytest tests/ -v` contre cette base neuve reproduit exactement le même motif que celui déjà vérifié (2 `xfail` + couplage WIP éventuel si le worktree n'est pas basé sur un `HEAD` propre — contre un `HEAD` sans travail en cours, uniquement les 2 `xfail`, tout le reste vert).
- Le workflow GitHub Actions lui-même ne peut être vérifié pour de vrai qu'après un push réel — demander explicitement l'accord de l'utilisateur avant de pousser (`finishing-a-development-branch`, option "Push et créer une Pull Request", ou push manuel si l'utilisateur choisit de merger localement puis de pousser `AH2_V3-1` ensuite).
