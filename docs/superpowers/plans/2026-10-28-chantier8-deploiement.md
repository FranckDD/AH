# Chantier 8 : deploiement en production - Plan d'implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tout ce qu'il faut dans le depot pour mettre le systeme en production sur le VPS OVH (conteneurs, sauvegardes, alertes, deploiement automatique, manuel), teste en repetition locale sur Docker Desktop avant tout contact avec le serveur.

**Architecture:** Un dossier `deploy/` (compose de production, Dockerfiles, Caddy, planificateur, sauvegardes, alertes, scripts de deploiement) et `docs/exploitation/` (manuel). Une seule image applicative (API, worker, planificateur, meme code), une image web (Caddy + interface compilee). Tout se parametre par un fichier `.env` de serveur. La phase "serveur reel" n'est PAS dans ce plan d'execution automatique : elle est guidee pas a pas avec l'utilisateur (tache 14, fichier de marche a suivre).

**Tech Stack:** Docker Compose, Caddy 2, Postgres 17, Redis, PowerSync, restic, supercronic, GitHub Actions + GHCR, bash, Python 3.12.

**Spec:** `docs/superpowers/specs/2026-10-24-chantier8-deploiement-design.md` (validee 2026-10-24). Le plan l'applique et ne la remplace pas.

## Global Constraints

- Hote : VPS OVH Londres, Ubuntu 26.04 LTS, 4 vCore, 8 Go, 75 Go NVMe. Tout en conteneurs, pas de PaaS, pas de Supabase.
- Fuseau : `TZ=Africa/Douala` sur chaque conteneur applicatif (avec `tzdata`) ; Postgres lance avec `-c timezone=Africa/Douala -c log_timezone=Africa/Douala`.
- Seuls les ports 80, 443 et SSH sont ouverts ; Postgres, Redis et PowerSync ne sont jamais exposes sur internet ni publies sur l'hote.
- Base de production **neuve** : `ci/schema_only.sql`, puis `ci/seed_application_roles.sql`, puis `alembic stamp head` (jamais `upgrade` sur base vide) ; aucune donnee de test migree ; **les donnees de reference validees par l'utilisateur sont reprises** (examens et leurs parametres et plages de reference, types de carnet de priere, regles de reduction du personnel, specialites, structure) par un script d'export/import (tache 6) ; comptes `doc_*` et donnees de demonstration jamais repris.
- Postgres applicatif : `wal_level=logical` et la publication `powersync` (deja dans `ci/schema_only.sql`) ; `pg-storage` separe pour l'etat interne de PowerSync (comme `powersync/docker-compose.yaml`).
- Planificateur (meme image que l'API) : `scripts/cash_closure_catchup.py` a `5 * * * *` ; `scripts/daily_control.py` chaque jour a 23 h 30 ; fuseau Douala.
- Volumes persistants sauvegardes avec la base : `storage/toxico_consents` (variable `CONSENT_STORAGE_DIR`), `storage/product_photos` (variable `PRODUCT_PHOTO_DIR`), `static/uploads` (logos de tickets et fichiers historiques). Les variables pointent vers les volumes montes, jamais vers l'interieur de l'image.
- Derriere le proxy : l'API lit l'adresse du client dans `X-Forwarded-For` envoyee par Caddy seulement (gunicorn/uvicorn `--forwarded-allow-ips` limite a l'adresse du conteneur Caddy ; Caddy ecrase l'en-tete recu d'internet).
- Taille des envois : Caddy limite le corps des requetes de `/api/*` a 6 Mo (les photos et les consentements sont plafonnes a 5 Mo par le code) ; les autres routes gardent la limite par defaut de Caddy.
- Images construites par GitHub Actions, publiees sur GHCR avec etiquette de version ; jamais de compilation sur le VPS. Le proprietaire GHCR est une variable (`GHCR_OWNER`) : le depot passera dans une organisation du centre.
- Migrations "ajout seulement" ; une migration destructive se deploie hors heures d'ouverture, apres sauvegarde juste avant.
- Sauvegardes (frequences revues par l'utilisateur le 2026-10-28, limite Hostinger de 600 000 fichiers dont 60 000 deja pris) : export chiffre de la base **toutes les heures** et sauvegarde complete (base et volumes) chaque nuit, gardes **sur le VPS** (depot restic local sur un volume separe) ; envoi chez Hostinger (SFTP) **une fois par semaine** ; copie sur le PC de l'admin **tous les 3 jours** ; toutes les frequences et la retention sont des reglages ; le nombre de fichiers du depot Hostinger est mesure pendant l'essai de restauration et rapporte. Limite assumee : si le VPS est perdu, la perte peut aller jusqu'a la derniere copie hors serveur (3 jours cote PC admin), attenuee par l'option OVH Daily backup. Essai de restauration obligatoire avant la mise en ligne. Pas d'archivage WAL.
- Alertes par e-mail au promoteur, a l'admin et au technicien responsable ; destinataires dans **un seul fichier** de reglages ; SMTP du domaine chez Hostinger ; mots de passe uniquement dans le fichier de secrets du serveur (jamais dans git, jamais dans une conversation).
- Le pont d'impression reste sur le PC de la secretaire (origines autorisees configurables, en-tete `Access-Control-Allow-Private-Network: true`).
- Aucun secret dans git ; `deploy/.env.example` ne contient que des noms et des valeurs fictives.
- Manuel en francais dans `docs/exploitation/`, court, pour une personne qui n'a pas construit le systeme.
- ASCII uniquement dans les textes affiches a l'ecran (regle du projet) ; les scripts et manuels peuvent contenir des accents.

## Review Focus

- Un fichier depose (photo produit, consentement) existe encore apres recreation des conteneurs ET apres une restauration complete sur une machine vide (tache 7, tache 9).
- PowerSync fonctionne a travers Caddy (WebSocket, meme domaine) : connexion maintenue plus de 60 s, reprise apres redemarrage de l'API (tache 7).
- Le premier admin est cree sans mot de passe dans les journaux ni dans l'historique du shell, et son mot de passe est refuse s'il est vide ou trop court (tache 6).
- Un deploiement dont la sante echoue apres le demarrage revient seul a l'image precedente et laisse le site disponible ; une sauvegarde a ete prise juste avant (tache 11).
- Derriere Caddy, l'API voit l'adresse IP reelle de chaque poste (limite de connexion de 5 par minute PAR poste, journal d'audit avec la vraie adresse) : sans cela, tout le centre partage une seule limite et un seul poste bloque tout le monde (taches 2 et 7).
- Une photo ou un consentement de 5 Mo passe le proxy ; un envoi plus gros est refuse proprement sans saturer le serveur (taches 4 et 7).
- Certificat HTTPS : tant que le DNS ne pointe pas vers le serveur, Caddy ne doit pas epuiser les limites de Let's Encrypt (autorite de test, tache 5) ; l'alerte d'expiration existe (tache 10).

---

## File Structure

- `deploy/Dockerfile.api` : image API/worker/planificateur. `deploy/Dockerfile.web` : build Vite puis Caddy. `deploy/Caddyfile`. `deploy/docker-compose.prod.yml`. `deploy/.env.example`. `deploy/postgres/` (conf et init). `deploy/scheduler/crontab`. `deploy/backup/` (scripts restic, restauration, copie hebdomadaire). `deploy/alerts/` (verifications et expediteur). `deploy/server-setup.sh` (durcissement). `deploy/deploy.sh`, `deploy/rollback.sh`. `deploy/smoke.sh` (repetition locale). `.github/workflows/deploy.yml`. `scripts/init_prod_db.sh`, `scripts/create_first_admin.py`. `docs/exploitation/*.md`.
- Modifies : `api_backend/backend_app/main.py` (CORS par environnement), `printer_bridge/server.py` (reseau prive), `.gitignore` (secrets de deploiement).

---

### Task 1: Reglages par environnement (CORS et sante)

**Files:**
- Modify: `api_backend/backend_app/main.py:132-152` (liste `origins`)
- Test: `tests/test_cors_origins.py`

**Interfaces:**
- Produces: variable d'environnement `CORS_ORIGINS` (liste separee par des virgules) ; si absente, la liste de developpement actuelle est conservee a l'identique ; fonction `parse_cors_origins(raw: str | None) -> list[str]` dans `api_backend/backend_app/config.py`.

- [ ] **Step 1: Tests** `test_parse_cors_origins_default_keeps_dev_list`, `test_parse_cors_origins_splits_trims_and_drops_empty` (`" https://app.x.org , ,http://a "` -> deux origines), `test_parse_cors_origins_rejects_wildcard_in_prod` (`"*"` avec `IS_PROD=true` leve `ValueError`).
- [ ] **Step 2: Lancer, voir echouer.** `REDIS_URL=redis://localhost:6379/0 python -m pytest tests/test_cors_origins.py -q -p no:cacheprovider`.
- [ ] **Step 3: Implementer** `parse_cors_origins` et l'utiliser dans `main.py` a la place de la liste en dur.
- [ ] **Step 4: Tests + suite des tests d'API existants touchant CORS** (`grep -rn "CORS\|allow_origins" tests`) passent.
- [ ] **Step 5: Commit** (le controleur decide).

### Task 2: Image API (API, worker, planificateur)

**Files:**
- Create: `deploy/Dockerfile.api`, `.dockerignore`, `deploy/entrypoints/api.sh`, `deploy/entrypoints/worker.sh`
- Test: `deploy/tests/test_image_api.sh`

**Interfaces:**
- Produces: image `ah2-api` ; commandes : `api` (gunicorn + UvicornWorker sur le port 8000, comme `Procfile`, nombre de workers par `WEB_CONCURRENCY`, defaut 2), `worker` (`celery -A celery_app worker`), `scheduler` (supercronic sur `/app/deploy/scheduler/crontab`) ; utilisateur non root ; `TZ=Africa/Douala` ; verification de sante `GET /health` ; la commande `api` ajoute `--forwarded-allow-ips` (variable `FORWARDED_ALLOW_IPS`) pour que `request.client.host` et `slowapi.get_remote_address` renvoient l'adresse du poste et non celle de Caddy.

- [ ] **Step 1: Test shell** `test_image_api.sh` : construit l'image, lance `python -c "import weasyprint; weasyprint.HTML(string='<p>ok</p>').write_pdf()"` (les libs Pango/Cairo doivent etre dans l'image), verifie `date +%Z` = `WAT`, `id -u` != 0, et que `/app/.env` n'existe pas dans l'image.
- [ ] **Step 2: Lancer, voir echouer** (pas d'image).
- [ ] **Step 3: Ecrire** `Dockerfile.api` (python 3.12-slim, tzdata, libs WeasyPrint, `requirements-api.txt` seulement, pas de PyQt, copie du code utile : exclure `view*`, `build`, `htmlcov`, `ah2-admin-web`, `docs`, `*.db`, `.env`, `storage`, `static/uploads` via `.dockerignore`), supercronic pour le planificateur, scripts d'entree.
- [ ] **Step 4: Relancer le test**, taille de l'image notee dans le rapport (objectif < 1,2 Go).
- [ ] **Step 5: Commit.**

### Task 3: Planificateur (crontab)

**Files:**
- Create: `deploy/scheduler/crontab`
- Test: `tests/test_scheduler_crontab.py`

**Interfaces:**
- Produces: crontab avec exactement : `5 * * * * python scripts/cash_closure_catchup.py`, `30 23 * * * python scripts/daily_control.py`, plus (apres tache 10) `*/10 * * * * python -m deploy.alerts.run_checks`.

- [ ] **Step 1: Test** : le fichier existe, chaque ligne a 5 champs cron valides, contient les deux commandes de la spec, chaque script cite existe dans le depot.
- [ ] **Step 2: Echoue, ecrire le fichier, le test passe.**
- [ ] **Step 3: Commit.**

### Task 4: Image web et Caddy

**Files:**
- Create: `deploy/Dockerfile.web`, `deploy/Caddyfile`
- Test: `deploy/tests/test_caddyfile.sh`

**Interfaces:**
- Produces: image `ah2-web` (etape node : `npm ci` puis `vite build` avec `VITE_API_URL=https://${DOMAIN}/api`, `VITE_POWERSYNC_URL=https://${DOMAIN}/sync`, `VITE_PRINT_BRIDGE_URL=http://127.0.0.1:9123`, passes en `ARG` ; etape caddy). Caddyfile : site `{$DOMAIN}`, `handle_path /api/*` vers `api:8000`, `handle_path /sync/*` vers `powersync:${PS_PORT}` (WebSocket compris), le reste = fichiers de l'interface avec repli `index.html` (PWA), en-tetes de securite usuels, pas de repertoire listable. Variable `ACME_CA` pour pointer sur l'autorite de test tant que le DNS n'est pas pret. `request_body { max_size 6MB }` sur `/api/*`. En-tete `X-Forwarded-For` pose par Caddy avec l'adresse reelle du client (valeur recue d'internet ecrasee).

- [ ] **Step 1: Test** : `caddy validate` du Caddyfile avec des variables fictives ; verification que `/api/health` et `/sync/probes/liveness` sont routes (test d'integration reporte a la tache 7).
- [ ] **Step 2: Ecrire les deux fichiers**, verifier que le service worker et le manifeste sont servis avec les bons types et sans cache sur `index.html` et `sw.js`.
- [ ] **Step 3: Test passe, commit.**

### Task 5: docker-compose de production

**Files:**
- Create: `deploy/docker-compose.prod.yml`, `deploy/.env.example`, `deploy/postgres/postgresql.conf`, `deploy/powersync/service.prod.yaml`
- Modify: `.gitignore` (`deploy/.env`, `deploy/secrets/`)
- Test: `deploy/tests/test_compose_config.sh`

**Interfaces:**
- Produces: services `caddy` (ports 80 et 443 seuls publies), `api`, `worker`, `scheduler`, `db` (postgres:17, volume, `wal_level=logical`, fuseau Douala), `redis` (sans port publie, mot de passe), `powersync`, `pg-storage` (comme le fichier de developpement), `backup` (tache 9), `alerts` (tache 10, ou execute par `scheduler`). Reseau interne unique ; `restart: unless-stopped` ; chaque service a un `healthcheck` ; versions d'images epinglees (relever la version de PowerSync utilisee en developpement avec `docker inspect`) ; volumes nommes `pgdata`, `ps_storage_data`, `uploads`, `product_photos`, `consents`, `caddy_data`, `redis_data`.
- Consumes: `.env` du serveur ; variables : `DOMAIN`, `GHCR_OWNER`, `IMAGE_TAG`, `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `AH2_API_BASE`, `IS_PROD=true`, `CORS_ORIGINS`, `REDIS_URL`, `PS_*`, `ACME_CA`.

- [ ] **Step 1: Test** : `docker compose --env-file deploy/.env.example -f deploy/docker-compose.prod.yml config` reussit ; un script verifie par analyse du JSON de `config` : seuls 80 et 443 sont publies, tous les services applicatifs ont `TZ=Africa/Douala`, aucun secret en clair dans le fichier compose, tous les services ont un healthcheck.
- [ ] **Step 2: Ecrire les fichiers** ; l'utilisateur PowerSync dans Postgres a le droit de replication (script d'init dans `deploy/postgres/init/`).
- [ ] **Step 3: Test passe, commit.**

### Task 6: Base neuve et premier admin

**Files:**
- Create: `scripts/init_prod_db.sh`, `scripts/create_first_admin.py`
- Test: `tests/test_create_first_admin.py`

**Interfaces:**
- Produces: `init_prod_db.sh` (idempotent : s'arrete si la base contient deja des tables ; sinon `psql -v ON_ERROR_STOP=1 -f ci/schema_only.sql`, puis le seed des roles, puis `alembic stamp head`) ; `create_first_admin.py` : `create_first_admin(session, username: str, password: str) -> int` (renvoie l'id), CLI lisant `AH2_ADMIN_USER` et `AH2_ADMIN_PASSWORD` ou une saisie masquee (jamais en argument de ligne de commande, jamais affiche).

- [ ] **Step 1: Tests** : `test_creates_admin_with_admin_role_and_hashed_password`, `test_refuses_empty_or_short_password` (moins de 12 caracteres), `test_refuses_second_run_when_an_admin_exists`, `test_password_never_in_output_or_logs` (capture stdout/stderr/log).
- [ ] **Step 2: Echouer, implementer, passer.** Suivre `create_test_user` de `tests/conftest.py` pour le hachage et le role ; utiliser le champ qui force le changement de mot de passe a la premiere connexion s'il existe, sinon le dire dans le manuel.
- [ ] **Step 3: Verifier `init_prod_db.sh`** sur une base Postgres vide jetable : toutes les tables, 035 en tete d'Alembic (`alembic current`), roles presents, rien d'autre.
- [ ] **Step 4: Donnees de reference** : `scripts/export_reference_data.py` (lit la base de developpement, ecrit un fichier SQL ou JSON par table de reference : `examens`, `parametres`, `reference_ranges`, `prayer_book_type`, `staff_discount_rules`, `role_permissions`, specialites medicales, `organization_config` sans les chemins de logos ; liste exacte a valider avec l'utilisateur apres relecture d'un inventaire lisible : nom des examens, nombre de parametres, prix) et `scripts/import_reference_data.py` (idempotent, dans une transaction, refuse de s'executer si les tables contiennent deja des donnees). Test : export puis import dans une base neuve redonne les memes lignes et les memes liens examen-parametre ; aucun compte, patient, vente ni resultat n'est exporte. Decision de l'utilisateur (2026-10-28) : a l'import, **tous les prix des examens sont mis a 0** (`examens.prix = 0`) : l'admin les fixe lui-meme avant la premiere vente ; test : apres import, `select count(*) from examens where prix <> 0` = 0. Les relations a respecter a l'export : `examens` <- `parametres` (examen_id) <- `reference_ranges` (parametre_id) ; ne pas exporter `lab_results`, `lab_result_details`, ni `prescriptions`. Produits de pharmacie et leurs prix : decision de l'utilisateur (voir inventaire).
- [ ] **Step 5: Commit.**

### Task 7: Repetition locale complete

**Files:**
- Create: `deploy/smoke.sh`, `deploy/tests/rehearsal.md` (resultat date)

**Interfaces:**
- Consumes: taches 1 a 6. Produces: preuve que l'ensemble demarre sur une machine vide.

- [ ] **Step 1: Ecrire `smoke.sh`** : monte la pile sur Docker Desktop avec `DOMAIN=localhost` et un `.env` jetable (Caddy en certificat interne), initialise la base, cree un admin, puis verifie : `/api/health` 200 ; connexion de l'admin ; creation d'un produit avec photo ; PDF de dossier ; `/sync/probes/liveness` 200 ; connexion WebSocket PowerSync tenue plus de 60 s ; redemarrage de l'API puis reprise ; recreation de tous les conteneurs (`down` sans `-v` puis `up`) : la photo est toujours la ; fuseau (`SHOW timezone` = `Africa/Douala`, `date` du conteneur `WAT`) ; aucun port autre que 80/443 ecoute sur l'hote ; limite de connexion par poste : 6 tentatives de connexion rapides depuis une adresse A sont limitees mais une tentative depuis une adresse B reussit, et le journal d'audit enregistre l'adresse envoyee (pas celle de Caddy) ; un envoi de 5 Mo passe, un envoi de 7 Mo recoit une erreur claire (413) ; une fausse valeur `X-Forwarded-For` envoyee par le client n'est pas crue ; une vente faite hors ligne puis synchronisee porte l'heure de Douala (aucun decalage d'une heure : si `paid_at` part du poste en UTC, corriger `caisseStore.js` ou laisser le serveur poser l'heure).
- [ ] **Step 2: Lancer**, corriger les taches precedentes si besoin, ecrire le resultat dans `rehearsal.md`.
- [ ] **Step 3: Commit.**

### Task 8: Pont d'impression en HTTPS

**Files:**
- Modify: `printer_bridge/server.py`, `printer_bridge/config.example.json`, `printer_bridge/README.md`
- Test: `printer_bridge/tests/test_private_network.py`

- [ ] **Step 1: Tests** : `test_preflight_from_allowed_https_origin_gets_allow_private_network_header` (requete `OPTIONS` avec `Access-Control-Request-Private-Network: true` et l'origine `https://app.ahandtohumanity-ngo.org`), `test_unlisted_origin_refused`, `test_wildcard_never_accepted`.
- [ ] **Step 2: Echouer, implementer** (ajout d'un middleware ou d'un gestionnaire de pre-requete ; liste d'origines deja configurable), tests passent, README mis a jour (origine de production a ajouter dans `config.json`).
- [ ] **Step 3: Commit.** Verification sur le PC de la secretaire avec le navigateur reel : etape de la tache 14.

### Task 9: Sauvegardes et restauration

**Files:**
- Create: `deploy/backup/Dockerfile`, `deploy/backup/hourly.sh`, `deploy/backup/nightly.sh`, `deploy/backup/restore.sh`, `deploy/backup/pull_weekly.ps1`, `deploy/backup/crontab`
- Test: `deploy/tests/test_backup_restore.sh`

**Interfaces:**
- Produces: `hourly.sh` (pg_dump au format personnalise, envoye chiffre par restic ; etiquette `hourly`) ; `nightly.sh` (base + les trois volumes ; etiquette `nightly`) ; politique `restic forget --keep-hourly 48 --keep-daily 14 --keep-weekly 8 --keep-monthly 6` en variables reglables ; `restore.sh <snapshot|latest> <dossier_cible>` (restaure base et fichiers) ; chaque script ecrit `last_success_<type>` (horodatage) lu par la tache 10 ; echec = code de sortie non nul et message pour l'alerte. `pull_weekly.ps1` : copie du depot restic vers le PC de l'admin.
- Consumes: variables `RESTIC_REPOSITORY` (SFTP Hostinger), `RESTIC_PASSWORD_FILE`.

- [ ] **Step 1: Test** (depot restic **local** a la place du SFTP) : peupler la base de la repetition (tache 7) et les trois volumes, lancer `nightly.sh`, detruire tous les volumes, lancer `restore.sh latest` dans une pile neuve : memes nombres de lignes par table, memes empreintes des fichiers, `alembic current` identique ; un `hourly.sh` apres une ecriture contient cette ecriture ; un mauvais mot de passe de depot echoue sans rien ecrire ; un dump tronque est detecte.
- [ ] **Step 2: Implementer** jusqu'au passage.
- [ ] **Step 3: Document** `docs/exploitation/sauvegardes.md` : ou est la cle, comment la restaurer sur un serveur vide, cout en stockage (la base est petite).
- [ ] **Step 4: Commit.** L'essai contre le vrai SFTP Hostinger se fait en tache 14.

### Task 10: Alertes

**Files:**
- Create: `deploy/alerts/checks.py`, `deploy/alerts/sender.py`, `deploy/alerts/run_checks.py`, `deploy/alerts/alerts.env.example`, `deploy/alerts/recipients.txt.example`
- Test: `tests/test_deploy_alerts.py`

**Interfaces:**
- Produces: `check_disk(path: str, threshold_pct: int = 80) -> Optional[str]`, `check_backup_fresh(marker: Path, max_age_hours: int, now: datetime) -> Optional[str]`, `check_container_restarts(inspect_json: list[dict], max_restarts: int = 3) -> Optional[str]`, `check_cert_expiry(host: str, port: int, min_days: int = 14) -> Optional[str]` (chacun renvoie `None` si tout va bien, sinon le message) ; `send_alert(subject: str, body: str, recipients: list[str], smtp: SmtpSettings) -> None` ; `load_recipients(path: Path) -> list[str]` (une adresse par ligne, `#` commentaires). `run_checks.py` ne renvoie pas deux fois la meme alerte dans un meme etat (fichier d'etat), et envoie un message « retabli » quand l'alerte disparait.

- [ ] **Step 1: Tests** : pour chaque `check_*`, cas sain et cas en defaut avec le message exact attendu ; `test_recipients_ignores_comments_and_blank_lines` ; `test_same_alert_sent_once_until_resolved` ; `test_smtp_failure_is_logged_not_raised_and_retried_next_run` ; `test_no_password_in_log_output`.
- [ ] **Step 2: Echouer, implementer, passer.**
- [ ] **Step 3: Ajouter** la ligne de crontab de la tache 3.
- [ ] **Step 4: Commit.** Surveillance externe (UptimeRobot) : etape de la tache 14.

### Task 11: Deploiement automatique et retour en arriere

**Files:**
- Create: `deploy/deploy.sh`, `deploy/rollback.sh`, `.github/workflows/deploy.yml`
- Test: `deploy/tests/test_deploy_rollback.sh`

**Interfaces:**
- Produces: `deploy.sh <tag>` : sauvegarde (`nightly.sh`), `docker compose pull`, `alembic upgrade head` dans un conteneur `api` jetable, redemarrage service par service, controle de sante de chaque service (delai borne) ; si un controle echoue : `rollback.sh` remet l'etiquette precedente (enregistree dans un fichier `.previous_tag`) et alerte ; `rollback.sh` seul est utilisable a la main. Workflow : sur push de la branche `production` seulement : tests serveur (comme `ci.yml`), tests web, build et push des images `ghcr.io/${GHCR_OWNER}/ah2-api` et `ah2-web` avec le SHA, puis SSH au VPS (cle de deploiement en secret GitHub, utilisateur non root) qui lance `deploy.sh`.

- [ ] **Step 1: Test** (pile de repetition) : `deploy.sh` vers une etiquette valide reussit sans coupure de plus de quelques secondes ; vers une etiquette dont l'API ne demarre pas : retour automatique, site toujours disponible, `.previous_tag` inchange ; migration ajoutant une colonne : l'ancienne image continue de fonctionner (regle « ajout seulement »).
- [ ] **Step 2: Implementer**, valider le workflow avec `actionlint` si disponible, sinon relecture ; aucune valeur secrete dans le fichier.
- [ ] **Step 3: Commit.** Mise en service reelle : apres creation de l'organisation GitHub (tache 13) et du serveur (tache 14).

### Task 12: Durcissement du serveur et manuel d'exploitation

**Files:**
- Create: `deploy/server-setup.sh`, `docs/exploitation/README.md`, `demarrer-arreter.md`, `mettre-a-jour.md`, `revenir-en-arriere.md`, `restaurer.md`, `alertes-et-acces.md`, `secrets.md`
- Test: `deploy/tests/test_server_setup_shellcheck.sh`

**Interfaces:**
- Produces: `server-setup.sh` (idempotent) : utilisateur non root `deploy` avec cle SSH, connexion SSH par cle seulement et sans root, pare-feu (ufw) 22/80/443, mises a jour de securite automatiques, fail2ban, Docker et plugin compose, fuseau de l'hote laisse en UTC avec NTP, dossier `/opt/ah2` ; manuel : demarrer, arreter, mettre a jour, revenir en arriere, restaurer, changer un destinataire d'alerte, ajouter ou retirer un acces technicien, renouveler un secret, que faire si le serveur est perdu ; chaque commande du manuel est copiable et a ete executee au moins une fois dans la repetition locale ou le serveur.

- [ ] **Step 1: Test** : `shellcheck` sans erreur sur tous les scripts de `deploy/` ; verification par script que chaque fichier cite dans le manuel existe.
- [ ] **Step 2: Ecrire script et manuel.** Le manuel tient en quelques pages ; une personne qui n'a pas construit le systeme doit pouvoir restaurer en suivant `restaurer.md` seul (a faire verifier par l'utilisateur en tache 14).
- [ ] **Step 3: Commit.**

### Task 13: Inventaire du depot, puis nettoyage et deplacement

**Files:**
- Create: `docs/superpowers/plans/chantier8-inventaire-depot.md` (liste des candidats a la suppression, groupes, avec taille et raison)

- [ ] **Step 1: Inventaire seulement** : lister, sans rien supprimer, version desktop (`view*`, `main*.py`, specs PyInstaller, `.iss`, `managers/`, `service/` si inutilises), sauvegardes, bases locales (`offline.db`, `onehandhumanity.sqlite`), exports, journaux, anciens SQL, dossiers de rapports, notes ; verifier par recherche d'imports ce qui est encore utilise par l'API, les scripts et les tests.
- [ ] **Step 2: L'utilisateur valide ligne par ligne** (rien n'est supprime avant). Les deux responsables des secrets sont designes ici.
- [ ] **Step 3: Suppression validee** en un commit separe, tests serveur et web complets verts ensuite.
- [ ] **Step 4 (utilisateur) : transfert du depot** dans l'organisation GitHub du centre (compte cree avec l'adresse de l'organisation, au moins deux administrateurs), mise a jour de `GHCR_OWNER`, du `remote` et de la branche `production`.

### Task 14: Mise en service guidee (avec l'utilisateur)

**Files:**
- Create: `docs/exploitation/mise-en-ligne.md` (marche a suivre cochable, ecrite en tache 12, completee pendant l'execution)

Cette tache n'est pas confiee a un sous-agent : elle est faite pas a pas avec l'utilisateur, une etape a la fois, chaque etape verifiee avant la suivante.

- [ ] **Step 1: Acces au serveur** : premiere connexion SSH a l'OVH, lancement de `server-setup.sh`.
- [ ] **Step 2: DNS** : entree A de `app.ahandtohumanity-ngo.org` chez Hostinger vers l'IP ; `ACME_CA` sur l'autorite de test, puis production quand le certificat de test est obtenu.
- [ ] **Step 3: Secrets** : generation du fichier de secrets, gestionnaire de mots de passe partage (au moins deux responsables), copie scellee de la cle de chiffrement des sauvegardes.
- [ ] **Step 4: Premier demarrage**, base neuve, premier admin, connexion depuis le PC de l'admin.
- [ ] **Step 5: Sauvegardes reelles** : activation SSH chez Hostinger, premier export, **restauration d'essai sur une machine vide**, copie hebdomadaire sur le PC de l'admin. Si Hostinger refuse : option payante, validee par le promoteur avant achat.
- [ ] **Step 6: Alertes** : SMTP du domaine, un message d'essai a chaque destinataire, surveillance externe toutes les 5 minutes.
- [ ] **Step 7: Pont d'impression** sur le PC de la secretaire avec le navigateur reel en HTTPS.
- [ ] **Step 8: Deploiement automatique** : un petit changement pousse sur `production` arrive sur le serveur ; un deploiement volontairement casse revient seul en arriere.
- [ ] **Step 9: Premier usage** : l'admin cree les comptes, definit les prix (produits, examens), initialise la caisse (solde de depart, une fois). Rien d'autre a nettoyer : la base de production est neuve.

### Task 15: Documentation finale (apres la mise en service)

Ajoutee le 2026-10-28 a la demande de l'utilisateur : cinq ensembles de documents, a produire quand le deploiement (tache 14) est termine, pour que le centre puisse maintenir le systeme sans les personnes qui l'ont construit. La longueur n'est pas limitee (plus de 200 pages acceptees) ; chaque document est exact par rapport au code et au serveur reels, jamais ecrit de memoire. Dossier : `docs/documentation/`. Sources : le depot, les specifications et plans de `docs/superpowers/`, `docs/superpowers/SUIVI-AVANCEMENT.md`, les guides de `docs/user-guides/`, le serveur en service. Versions PDF generees avec l'outillage des guides (`docs/user-guides/tools`), sources Markdown conservees dans le depot.

- [ ] **15a. Documentation d'utilisation** (`docs/documentation/utilisation/`) : pour chaque role, le guide existant (secretaire, caisse, medecin, infirmier, laboratoire, toxicologie, psychologue, conseiller spirituel, stock, production, promoteur, admin), reunis dans un seul recueil avec sommaire, glossaire commun et marche a suivre « premier jour » (comptes, prix, caisse). Les guides sont mis a jour pour tout ecart constate avec l'application en service ; la langue du recueil est celle des guides existants (anglais) sauf decision contraire de l'utilisateur.
- [ ] **15b. Documentation technique** (`docs/documentation/technique/`) : reference complete et detaillee : modeles de donnees et migrations (026 a 035 et suivantes, tables, colonnes, contraintes), toutes les routes de l'API par module (methode, chemin, roles, entrees, sorties, erreurs), controleurs et depots, interface web (ecrans, magasins, passerelles, composants `ui/`, i18n), synchronisation hors ligne PowerSync (tables, regles, file d'envoi, quarantaine), taches planifiees, scripts, configuration (toutes les variables d'environnement), conventions de code, procedures de test. Generee en partie par des scripts qui lisent le code (liste des routes avec leurs roles, liste des tables) pour ne pas deriver ; verification : un script compare la liste documentee a la liste reelle et echoue en cas d'ecart.
- [ ] **15c. Documentation d'architecture** (`docs/documentation/architecture/`) : vue d'ensemble (schemas des conteneurs, flux reseau, Caddy, API, worker, planificateur, Postgres, Redis, PowerSync), flux de donnees cles (connexion, vente hors ligne puis synchronisation, cloture de caisse, laboratoire, notifications), securite et roles, fuseau horaire, stockage des fichiers, sauvegardes et reprise apres sinistre, deploiement et retour arriere, montee en charge possible, limites connues. Schemas en Mermaid ou images generees, sources conservees.
- [ ] **15d. Documentation des decisions cles** (`docs/documentation/decisions/`) : un enregistrement par decision (contexte, options, choix, raisons, consequences, date, qui a decide), tire des specifications, des rulings des registres `.superpowers/sdd/*/progress.md` et du suivi : hebergement OVH sans PaaS ni Supabase, heure de Douala partout, une table sans lien patient pour les notes spirituelles, prix verrouille en caisse, regle de migration « ajout seulement », sauvegardes restic, repartition des roles, etc. Chaque enregistrement cite sa source ; les decisions revoquees sont marquees comme telles.
- [ ] **15e. Documentation des tests de securite** (`docs/documentation/securite/`) : plan de tests et RESULTATS reels, a executer sur la pile de repetition puis sur le serveur : matrice complete roles x routes (toute route refusee a tout role non autorise, y compris l'acces direct par identifiant), authentification (limite de connexion par poste, expiration du jeton, mot de passe), injection et entrees abusives (SQL, fichiers piegés, tailles limites, JSON invalide), controle d'acces aux fichiers (photos, consentements, logos), en-tetes de securite et HTTPS (analyse du certificat et des en-tetes), exposition des ports (seuls 80, 443 et SSH), secrets (aucun secret dans le depot ni dans les images : analyse), dependances (`pip-audit`, `npm audit`, analyse `bandit`), confidentialite des sauvegardes (depot chiffre, cle seule), journaux (aucun mot de passe ni texte de note). Chaque test : objectif, methode reproductible (commande), resultat attendu, resultat obtenu, date, correction si echec. Les echecs trouves sont corriges avant la fin, ou documentes comme risque accepte avec decision du promoteur.
- [ ] **15f. Revue** : relecture par un sous-agent independant de chaque ensemble contre le code et le serveur ; l'utilisateur valide le recueil d'utilisation et le plan de tests de securite avant diffusion ; les documents sont sauvegardes avec le depot.
