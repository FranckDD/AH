# Chantier 2b — CI (GitHub Actions)

**Date :** 2026-08-12
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** dernier maillon de la feuille de route avant 2c (bloqué) et le portage web — s'appuie sur toute l'infrastructure de test livrée par 2d-0 à 2d-4

## Contexte

Le projet n'a aucune CI. La suite de tests (2d-0 à 2d-4, ~130 tests) tourne aujourd'hui uniquement en local, contre une base `AH2` réelle déjà provisionnée manuellement au fil du temps. Deux blocages réels, déjà identifiés au registre (`C2`, `D2`), empêchent une CI de fonctionner telle quelle — un `pip install` frais casserait l'import de l'application, et un `alembic upgrade head` sur une base neuve produirait un schéma sans les procédures/fonctions stockées dont les modules patients et prescriptions dépendent. Les deux sont résolubles et traités dans ce même chantier (décision utilisateur explicite : pas de découpage en 2b-0/2b-1).

## Découvertes pendant le cadrage

### Blocage 1 — `requirements.txt` incomplet sur `HEAD`

Confirmé par extraction de tous les imports des fichiers Python committés pertinents pour l'API (hors `view_pyqt6/`, code desktop) : 4 paquets manquent, tous requis par du code déjà committé (pas le travail en cours) :
- `slowapi` — importé par `api_backend/backend_app/main.py`, `api_backend/backend_app/rate_limit.py`, `tests/conftest.py`, `tests/test_rate_limit.py` (`SEC-05`, limitation de débit)
- `limits`, `Deprecated` — dépendances transitives de `slowapi`
- `fpdf2` (le module s'appelle `fpdf` à l'import, mais le paquet PyPI est `fpdf2`) — utilisé par `utils/invoice_pdf_generator.py`, exercé par les tests de facture du chantier 2d-4

Vérifié explicitement que `redis`/`celery` ne sont **pas** nécessaires : les versions committées de `controller/caisse_controller.py` et `controller/prescription_controller.py` (`git show HEAD:...`) n'importent ni l'un ni l'autre — ces dépendances n'existent que dans le travail en cours de l'utilisateur.

Versions à utiliser (déjà validées dans l'environnement de développement actuel, où tous les tests passent) : `slowapi==0.1.9`, `limits==5.8.0`, `Deprecated==1.3.1`, `fpdf2==2.8.3`.

### Blocage 2 — Procédures et fonctions stockées absentes de la baseline Alembic (`D2`)

La migration baseline (`6ea9b46b7a65_baseline.py`) ne contient aucune définition `FUNCTION`/`PROCEDURE`/`TRIGGER`. Confirmé par comparaison entre les triggers réellement actifs sur la base locale (`pg_trigger`) et le contenu du dossier `alembic/versions/` : sur les 6 triggers actifs sur les tables `patients`/`prescriptions`/`users`/`caisse`, un seul (`create_metier_profile`, chantier "Nettoyage A1-A4") est tracé par Alembic. Il manque :

**Procédures** (déjà utilisées par les tests 2d-1 à 2d-3) :
- `create_patient`, `update_patient` (`delete_patient` déjà couvert par la migration `001_fix_delete_patient_procedure.py` du chantier 2d-2)
- `create_prescription`, `update_prescription`

**Fonctions de trigger** (avec leurs `CREATE TRIGGER` correspondants) :
- `fn_caisse_protect_cancelled` (trigger `trg_caisse_protect_cancelled` sur `caisse`)
- `set_default_specialty` (trigger `trg_default_specialty` sur `users`)
- `track_patient_changes` (trigger `trg_patient_tracking` sur `patients`)
- `update_prescribed_names` (trigger `trg_prescription_names` sur `prescriptions` — auto-remplit `prescribed_by_name`, exercé par les tests 2d-3)

**Bonne nouvelle, confirmée** : toutes ces définitions existent dans `ah2_v3_dashmedical.sql` (dump `pg_dump -Fc` traqué par git à la racine du dépôt), extractibles proprement via `pg_restore` — contrairement à l'ancienne procédure `delete_patient` du chantier 2d-2, dont la définition d'origine était irrécupérable. Aucune improvisation nécessaire : les corps réels et déjà éprouvés sont disponibles.

### Item hors périmètre confirmé — les 17 tables non modélisées (`A3`)

L'exclusion de ces tables de l'autogénération Alembic (déjà traitée au chantier "Nettoyage A1-A4") n'a pas besoin d'être revisitée : aucun test de la suite actuelle ne les touche.

## Portée

1. **`requirements.txt`** : ajout ciblé des 4 paquets manquants avec leurs versions exactes. Aucune autre modification de ce fichier — le reste du travail en cours de l'utilisateur sur ce fichier (réécriture complète, item `C2`) reste hors périmètre et non touché.
2. **Nouvelle migration Alembic**, chaînée après la dernière révision existante, ajoutant les 4 procédures et les 4 fonctions de trigger (+ leurs triggers) listées ci-dessus, avec les corps réels extraits du dump. `downgrade()` documenté honnêtement selon le même principe que `001_fix_delete_patient_procedure.py` (irréversible si le corps d'origine n'est pas autrement récupérable, avec justification écrite).
3. **Workflow GitHub Actions** (`.github/workflows/ci.yml`) : déclenché sur `push` et `pull_request` vers `AH2_V3-1`. Service Postgres 17 conteneurisé, Python 3.12, `pip install -r requirements.txt`, `alembic upgrade head` contre la base fraîche du service, puis `pytest tests/ -v`. Variables d'environnement nécessaires (`DATABASE_URL` pointant vers le service Postgres du workflow, `JWT_SECRET` généré ou codé en dur pour la CI uniquement — jamais le secret réel) définies dans le fichier de workflow, jamais committées ailleurs.
4. **`tests/test_patient_repo.py`** : les 2 tests déjà connus comme obsolètes (indépendants des deux blocages ci-dessus, cassés sur du code déjà committé) sont marqués `@pytest.mark.xfail` avec une raison explicite renvoyant au registre — la CI reste verte, le problème reste visible et tracé, sans devenir un correctif caché.

## Vérification

- `alembic upgrade head` réussit contre une base Postgres 17 **entièrement neuve** (aucune donnée, aucun objet préexistant) — vérifié localement contre une base de test dédiée avant d'écrire le workflow, pas seulement supposé.
- La suite de tests complète (`pytest tests/ -v`) tourne contre cette base fraîchement migrée et produit le même résultat qu'en local aujourd'hui (mêmes tests verts, les 2 `xfail` marqués comme tels, pas d'autre échec).
- Le workflow GitHub Actions lui-même est vérifié via un push réel sur une branche de test (ou `gh workflow run` / l'onglet Actions), pas seulement lu comme YAML plausible.
- Aucune donnée résiduelle dans la base `AH2` de développement locale (les vérifications ci-dessus utilisent une base neuve dédiée, jamais `AH2`).

## Hors périmètre

- La réécriture complète de `requirements.txt` du travail en cours de l'utilisateur (`C2`) — seuls les 4 paquets confirmés manquants sur `HEAD` sont ajoutés.
- Toute correction du contenu des 2 tests obsolètes de `test_patient_repo.py` — seulement marqués `xfail`, le correctif reste un chantier séparé.
- Les 17 tables non modélisées (`A3`, déjà traité, non concerné).
- `redis`/`celery`/le module `tasks/` — n'existent que dans le travail en cours, hors périmètre de `HEAD` et donc de la CI.
- Tout déploiement continu (CD) — ce chantier couvre uniquement l'intégration continue (tests), pas le déploiement (`D3`, item de registre séparé sur l'absence d'étape `alembic upgrade head` au déploiement).
