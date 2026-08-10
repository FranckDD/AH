# Chantier 2a — Alembic + migration de référence

**Date :** 2026-08-10
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** audit `ARC-06` ; premier des 5 sous-chantiers du chantier 2

## Contexte

Le chantier 2 (« socle d'évolution ») regroupe en réalité 5 sous-chantiers indépendants : Alembic, CI, split des dépendances, tests des chemins critiques, piste d'audit non silencieuse. Comme pour le découpage initial des chantiers 0-5, les traiter en bloc produirait un plan trop large. Ce document couvre uniquement **2a — Alembic**, le premier retenu, car c'est le fondement qui sécurise les 4 suivants et qui a déjà justifié le report de migrations SQL directes aux chantiers 1 (`secretaire1`) et SEC-09 (`token_version`).

Aujourd'hui, `migrations/` ne contient qu'un script ponctuel de synchronisation PostgreSQL → SQLite (`import_users_pg_to_sqlite.py`), sans rapport avec la gestion de schéma. Il n'existe aucun outil de migration de schéma : toute évolution passe par des `ALTER TABLE` manuels, non versionnés, non reproductibles d'un environnement à l'autre.

## Découvertes pendant le cadrage

- **Alembic est déjà installé** (`1.18.5`) dans cet environnement, mais absent de `requirements.txt` — même situation que `slowapi` au chantier 0 : le fichier est en plein travail en cours (remplacé par un `pip freeze` complet non commité, sans base commune avec `HEAD`). Il sera ajouté au fichier de travail sans être commité, comme précédemment.
- **21 modules de modèles** existent sous `models/`, tous s'importent sans erreur. `models/__init__.py` n'en importe que 3 (`Patient`, `MedicalRecord`, `Prescription`) — insuffisant pour qu'Alembic voie le schéma complet lors de l'autogénération.
- **`models/App.py`** est un reliquat sans rapport avec la persistance : un gabarit `customtkinter` (interface graphique de démonstration), pas un modèle SQLAlchemy. À exclure explicitement de l'enregistrement des métadonnées.
- La base contient déjà des données réelles (102 patients, 13 comptes utilisateurs, etc.) — la migration de référence ne doit **jamais être exécutée**, seulement servir de point de départ marqué comme déjà appliqué.

## Détail de l'implémentation

### 1. Initialisation d'Alembic

`alembic init alembic` — dossier dédié `alembic/` à la racine, distinct de `migrations/` (qui garde son script de synchronisation SQLite, sans rapport, aucun renommage nécessaire).

### 2. Configuration de `env.py`

- Ajout du chemin racine du projet à `sys.path` (même pattern que `migrations/import_users_pg_to_sqlite.py`), pour pouvoir importer `api_backend.backend_app.config` et `models.*` depuis un script exécuté hors du contexte FastAPI.
- `DATABASE_URL` importé depuis `api_backend.backend_app.config` (source unique de vérité) et injecté dans la config Alembic via `config.set_main_option("sqlalchemy.url", DATABASE_URL)` — pas de duplication de la chaîne de connexion dans `alembic.ini`.
- Import explicite des 19 modules de modèles réels (`App.py` et `medical.py`, tous deux vides de contenu SQLAlchemy — `App.py` un reliquat customtkinter, `medical.py` un fichier entièrement vide — exclus) pour que `Base.metadata` (import depuis `models.database`) reflète le schéma complet au moment de l'autogénération.

### 3. `models/__init__.py` étendu

Actuellement 3 imports sur 21 fichiers. Étendu pour importer les 19 modèles réels (`App.py` et `medical.py` exclus, vides de contenu SQLAlchemy). Corrige un manque réel indépendant d'Alembic : aujourd'hui, tout code qui fait `import models` sans plus n'a pas accès à un `Base.metadata` complet.

### 4. Migration de référence

```bash
alembic revision --autogenerate -m "baseline"
alembic stamp head
```

`stamp head` marque la base comme étant déjà à cette révision **sans exécuter la migration** — les tables existent déjà, les recréer casserait tout. À partir de ce point, toute évolution de schéma future passe par `alembic revision --autogenerate` + `alembic upgrade head`, versionnée et reproductible.

## Hors périmètre

- Migrer les `ALTER TABLE` déjà appliqués manuellement (chantier 1 : `secretaire1` ; SEC-09 : `token_version`) en migrations Alembic rétroactives — la colonne existe déjà en base, la migration de référence (baseline) la capture telle quelle dans son état actuel. Pas de valeur à recréer un historique de migrations pour du passé déjà appliqué.
- Les 4 autres sous-chantiers (CI, split des dépendances, tests, audit non silencieux) — cadrés un par un ensuite.

## Vérification

- `alembic current` affiche la révision baseline après le `stamp`
- ~~`alembic revision --autogenerate` à blanc ne détecte aucune différence~~ — **attente incorrecte, corrigée après exécution** : `stamp head` ne modifie que la table de suivi des versions, pas le schéma réel. Une autogénération ultérieure continue de montrer les mêmes divergences pré-existantes entre modèles et base (voir Notes post-implémentation), et c'est normal — ce n'est pas ce que `stamp` est censé neutraliser
- L'API démarre toujours normalement après ces changements (aucun impact sur le chemin d'exécution habituel, Alembic est un outil hors-ligne)
- `python -c "import models; from models.database import Base; print(len(Base.metadata.tables))"` retourne un nombre de tables cohérent avec les 19 modèles

## Risques et hypothèses

- L'autogénération compare les modèles SQLAlchemy à l'état réel de la base ; toute divergence pré-existante entre les deux (colonnes en base sans modèle correspondant, ou l'inverse) apparaîtra dans la migration de référence générée. Comme cette migration n'est jamais exécutée (`stamp` seulement), ce n'est pas un risque opérationnel — mais la migration générée servira aussi de documentation du schéma réel, donc ces divergences seront visibles et pourront révéler d'autres découvertes à traiter séparément.

## Notes post-implémentation

- **Découverte critique confirmant la contrainte "jamais exécuter"** : la lecture du fichier `upgrade()` généré a révélé qu'il contient `op.drop_table(...)` pour **17 tables réelles et peuplées**, sans modèle SQLAlchemy correspondant : `admin`, `doctor`, `nurse`, `secretaire`, `laborantin` (les tables « profil métier » du trigger `create_metier_profile()`, chantier 1), `audit_logs`, `audit_user_actions_old`, `audit_access_old`, `permissions`, `role_permissions`, `motif_translations`, `spiritual_sessions`, `spiritual_attendance`, `admissions`, `psych_evaluations`, `patient_contacts`, `lab_results_audit`. Si cette migration avait été exécutée (`alembic upgrade head`) au lieu d'être stampée, elle aurait supprimé ces 17 tables. Confirme que la précaution de conception (ne jamais exécuter la baseline) n'était pas superflue.
- **Ces 17 tables n'ont aucun modèle SQLAlchemy** — découverte pour un chantier futur : tant qu'elles ne sont pas modélisées, toute autogénération continuera de proposer leur suppression, et quiconque exécuterait une migration autogénérée sans lire attentivement son contenu risquerait une perte de données réelle. Hors périmètre de 2a (qui ne fait qu'établir le suivi de version), mais un risque à connaître avant le chantier suivant qui touchera au schéma.
- **`alembic stamp head` ne neutralise pas les divergences modèles/base** : contrairement à l'hypothèse initiale de la section Vérification, une autogénération immédiatement après le `stamp` montre exactement les mêmes différences qu'avant — `stamp` ne fait que marquer la table de suivi des versions, il ne touche jamais au schéma réel. C'est attendu et sans conséquence pour ce chantier ; la réconciliation de ces divergences (dont les 17 tables non modélisées ci-dessus) est un chantier séparé, pas un signe d'échec de la baseline.
- Migration baseline : révision `6ea9b46b7a65`, commitée dans `alembic/versions/6ea9b46b7a65_baseline.py`.
