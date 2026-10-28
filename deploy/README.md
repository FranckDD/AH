# Deploiement AH2 (production)

Tout tourne en conteneurs sur le VPS (Docker Compose). Rien n'est compile sur le serveur :
les images viennent de GHCR.

## Fichiers
- `docker-compose.prod.yml` : les 9 services (caddy, api, worker, scheduler, db, redis, powersync, pg-storage, backup). Seuls 80 et 443 sont publies. Les alertes e-mail (tache 10) ne sont PAS un service : le conteneur `scheduler` les lance (`deploy/alerts/`, crontab `*/10`).
- `.env.example` : modele du fichier d'environnement. Copier en `deploy/.env` sur le serveur et remplacer chaque valeur. Ne jamais committer le vrai fichier.
- `Dockerfile.api`, `Dockerfile.web`, `Caddyfile`, `entrypoints/`, `scheduler/crontab` : images et commandes (taches 2 a 4).
- `postgres/postgresql.conf` : reglages Postgres pour 8 Go. `postgres/init/01-roles.sh` : au premier demarrage, cree les roles `app_medical` (sans connexion) et `powersync_repl` (replication, lecture seule).
- `powersync/service.prod.yaml` : configuration PowerSync pour le reseau Docker interne.
- `backup/` : image et scripts de sauvegarde (restic) : `hourly.sh`, `nightly.sh`, `offsite.sh`, `restore.sh`, `verify.sh`, `pull_backups.ps1` (PC de l'admin). Mode d'emploi : `docs/exploitation/sauvegardes.md`. Image : `docker build -t ghcr.io/<GHCR_OWNER>/ah2-backup:<tag> deploy/backup`.
- `tests/test_backup_restore.sh` : essai complet de sauvegarde et restauration (pile jetable `ah2backuptest`, ~15 min, Docker requis ; images `ah2-api:local` de `smoke.sh --build`).
- `tests/test_compose_config.sh` : verifie le compose sans rien demarrer (`bash deploy/tests/test_compose_config.sh`).

## Points a connaitre
- Le reseau `ah2` a un sous-reseau fixe (172.28.0.0/24) ; Caddy a l'adresse 172.28.0.10, que l'API croit pour `X-Forwarded-For`. Les autres conteneurs prennent leur adresse dans 172.28.0.128/25 (`ip_range`), jamais en collision avec Caddy.
- Adresse IP vue par l'API : les clients IPv6 passent par docker-proxy et apparaissent tous sous l'adresse de la passerelle du reseau (172.28.0.1) ; les postes du centre derriere l'unique adresse publique (NAT) apparaissent comme UNE seule adresse. Un compteur de connexions par adresse IP les confond donc ; une tache distincte adapte la protection de connexion (ne pas la traiter ici). Ne pas publier d'enregistrement AAAA tant que ce point n'est pas traite.
- HSTS : `HSTS_HEADER` (defaut `max-age=0`, aucun epinglage). La production met `max-age=31536000` seulement une fois le vrai certificat obtenu.
- `postgres/init/01-roles.sh` doit etre commite avec le bit executable (`git update-index --chmod=+x deploy/postgres/init/01-roles.sh`).
- `DATABASE_URL` et `REDIS_URL` sont assembles dans le compose depuis `POSTGRES_PASSWORD` et `REDIS_PASSWORD`.
- La cle PowerSync est calculee au demarrage depuis `JWT_SECRET` : ne pas definir `PS_APP_HS256_SECRET`.
- Mots de passe qui entrent dans une URL : generer avec `openssl rand -hex 32`.

## Usage prevu (tache 7 et suivantes)
1. `cp deploy/.env.example deploy/.env`, remplir les secrets, mettre `ACME_CA` sur l'autorite de test tant que le DNS n'est pas pret.
2. `docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml up -d db redis pg-storage`, puis `scripts/init_prod_db.sh` (tache 6) charge le schema.
3. Demarrer le reste (`up -d`) ; la tache 7 verifie PowerSync a travers Caddy, la limite d'envoi et l'adresse IP reelle.

## Sauvegardes (tache 9)
- Avant le premier `up` : `sudo install -d -o 10001 -g 10001 -m 0700 /srv/ah2-backups` (dossier du depot, jamais un volume nomme), puis `deploy/secrets/backup_sftp_key` (`chown 10001:10001`, mode 600) et `deploy/secrets/backup_known_hosts`. Voir `docs/exploitation/sauvegardes.md` pour la creation des cles et du mot de passe restic.
- Horaires et retention : variables `BACKUP_*_CRON` et `KEEP_*` de `.env`. Sante : le conteneur `backup` est `healthy` tant qu'un export horaire a reussi il y a moins de 2 h.
- Les alertes (tache 10, lancees par `scheduler`) lisent le volume `backup_status` en lecture seule : fichiers `last_success_{hourly,nightly,offsite,verify}` (secondes Unix), `last_failure_*`, `last_error_*`, `offsite_stats.json`.
- Budget memoire : la somme des `mem_limit` est de 6,25 Go (plafond du test : 6,5 Go), les alertes n'ajoutent aucun conteneur (elles tournent dans les 256 Mo de `scheduler`).

## Alertes e-mail (tache 10)
- Avant le premier `up` : `cp deploy/alerts/alerts.env.example deploy/alerts/alerts.env` et `cp deploy/alerts/recipients.txt.example deploy/alerts/recipients.txt`, puis les remplir (fichiers ignores par git, `chmod 600`, `chown 10001`). Dossier monte en lecture seule sur `/run/alerts` du conteneur `scheduler` (variable `ALERTS_CONFIG_DIR`).
- Essai : `docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml exec scheduler python -m deploy.alerts.run_checks --test-mail` (ou `--dry-run`).
- Les volumes `pgdata`, `ps_storage_data` et le depot de sauvegarde sont montes en lecture seule dans `scheduler` (controle disque). Aucun `docker.sock` : les sondes passent par le reseau interne. Voir `docs/exploitation/alertes-et-acces.md`.
