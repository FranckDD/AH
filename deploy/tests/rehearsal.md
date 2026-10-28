# Repetition locale de la pile de production (tache 7)

Date : 2026-10-28. Machine : PC Windows 11, Docker Desktop, Git Bash. Projet compose `ah2rehearsal`
(la pile de developpement n'a pas ete touchee). Script : `deploy/smoke.sh`.

Resultat du dernier passage complet : **PASS=74 FAIL=0** (une ligne INFO, voir section 11).
Le passage final apres les derniers reglages du script est consigne en fin de document.

## Versions et images reellement utilisees

| Element | Valeur |
|---|---|
| Postgres applicatif | `postgres:17.6-bookworm` (existe, tire tel quel) |
| Postgres PowerSync | `postgres:18.0-bookworm` (existe, tire tel quel) |
| Redis | `redis:7.4.5-alpine` (existe, tire tel quel) |
| PowerSync | `journeyapps/powersync-service:1.23.2@sha256:51a59176...b5b29` (deja en local, digest valide) |
| Caddy | 2.10.2 (`caddy:2.10.2-alpine`) |
| API | `ghcr.io/rehearsal/ah2-api:local`, 655 392 273 octets (625 Mio) |
| Web | `ghcr.io/rehearsal/ah2-web:local`, 99 365 444 octets (95 Mio) |

Aucun tag du compose n'a du etre change. Les images locales ne sont jamais poussees.

Taille de l'image API : 574 727 334 octets avant l'ajout de `postgresql-client` (tache 6), 655 392 273 apres,
soit **+80,7 Mo** (psql 17.11 et ses bibliotheques ; bien plus que les 10 a 20 Mo estimes). Toujours sous
la limite de 1,5 Go. Image web : +1,8 Mo (ajout de `tzdata`, voir bugs).

## Resultats (extraits de `smoke.sh`)

Chaque ligne a ete produite par le script ; la preuve est entre crochets.

### Demarrage, base, roles
- PASS db, redis, pg-storage healthy.
- PASS role `app_medical` existe et `rolcanlogin = f` : `01-roles.sh` a bien tourne au premier demarrage (le bit
  executable n'est pas en cause : l'entrypoint postgres execute OU source le fichier, et le script est ecrit
  pour etre source ; sous Windows le montage le montre `-rwxr-xr-x`). Sur le VPS le depot cloné doit quand meme
  porter le mode 100755 (`git update-index --chmod=+x`), voir `deploy/README.md`.
- PASS role `powersync_repl` : REPLICATION + LOGIN (`t|t`).
- PASS `scripts/init_prod_db.sh` dans l'image api contre le conteneur db : 82 tables, `alembic_version = 035_spiritual_notes`,
  11 roles applicatifs. Second lancement refuse (code 2, "la base contient deja 160 objet(s)").
- PASS publication `powersync` presente.
- PASS `create_first_admin.py` : identifiants passes par l'entree standard (rien dans la ligne de commande ni dans
  `ps` de l'hote), "Compte administrateur cree (user_id=1)".
- PASS `import_reference_data.py` avec `reference_data.json` du chantier (non modifie) ; 0 examen avec prix different de 0.

### Fuseaux, PowerSync, ports
- PASS `SHOW timezone` = `Africa/Douala` ; `wal_level` = `logical`.
- PASS `date +%Z` = `WAT` dans api, worker, scheduler et caddy.
- PASS PowerSync a cree sa fente de replication (`powersync_1_xxxx:pgoutput:true`).
- PASS seuls les ports 80 et 443 sont publies (`docker ps`), aucun autre service que caddy n'est publie.
- PASS le port 443 de l'hote atteint Caddy (poignee de main TLS avec le nom `localhost`, `/healthz` 200).

### HTTPS, routes
- PASS `/healthz` 200 ; `/api/health` `{"success":true,"status":"ok","database":"connected"}` ; `/sync/probes/liveness` 200.
- PASS `/api` et `/sync` sans barre finale : 404. `/` 200. Lien profond `/dashboard/x` 200 (repli `index.html`).
- PASS `http://localhost/` : 308 vers HTTPS.

### Connexion et protection
- PASS connexion admin : jeton de 300 caracteres.
- PASS 6 mauvais mots de passe sur un compte : six 401 identiques ; le bon mot de passe est ensuite refuse (401) ;
  un AUTRE compte depuis la meme adresse se connecte (200) pendant le verrou ; `POST /users/{id}/unlock` par l'admin : 204 ;
  le compte reconnecte (200).
- PASS limite par adresse : sur 61 tentatives rapides avec 61 identifiants differents, la 61e (et la premiere) recoit 429.
- PASS compteurs dans Redis : cles `LIMITS:LIMITER/<ip>//auth/login/60/1/minute` et `login:fail:*` / `login:lock:*`.

### Adresse IP du client derriere Caddy
- PASS deux `X-Forwarded-For` falsifies (`203.0.113.7`, `198.51.100.9, 192.0.2.1`) envoyes par le client : les cles de limite
  ne contiennent aucune de ces adresses, une seule adresse client est vue (`172.28.0.136`).
- PASS client interne (conteneur du reseau) avec `X-Forwarded-For: 203.0.113.99` : la cle porte l'adresse reelle du client
  (`172.28.0.137`), ni l'adresse falsifiee ni celle de Caddy (`172.28.0.10`).
- Note : depuis l'hote Windows, Docker Desktop presente tous les clients sous l'adresse de la passerelle du reseau
  (`172.28.0.1`) ; ce n'est pas teste ici. Voir le point "journal d'audit" plus bas.

### Journal d'acces Caddy
- PASS apres une requete `?q=secretterm` avec un cookie et un jeton Bearer : aucune de ces trois valeurs n'apparait dans
  les journaux du conteneur.

### Donnees metier et tailles d'envoi
- PASS creation d'un produit, envoi d'une photo PNG de ~5 Mo (200), telechargement du JPEG redimensionne (~96 Ko).
- PASS 7 Mo avec Content-Length : 413 (refus immediat de Caddy).
- PASS 7 Mo vraiment en morceaux (HTTP/1.1, `Transfer-Encoding: chunked`, aucun Content-Length, corps multipart complet) : 413.
  Une premiere version du test (corps non multipart, route POST) ne prouvait rien : l'API repondait 405/422 sans lire le corps.
- PASS 5 Mo en morceaux : passe Caddy et atteint l'API (400, le corps de test n'est pas une image).
- PASS creation d'un patient, PDF du dossier (`/patients/{id}/dossier/export?format=pdf`, WeasyPrint dans le conteneur, 16 Ko, `application/pdf`).

### Heure d'une vente synchronisee hors ligne
Lecture du code :
- `caisseStore.js` (`createInvoice`, role secretaire) ecrit `paid_at = new Date().toISOString()` (UTC) dans la table locale `caisse`.
- `DossierConnector.js`, cas `caisse:PUT`, construit le corps envoye a `POST /caisse/` **sans** `paid_at` (champs : patient_id,
  patient_label, amount, advance_amount, payment_method, transaction_type, note, items, staff_discount_amount, uuid). Meme
  chose pour les versements (`payment_date` n'est pas envoye).
- `caisse_repo.create_transaction` : `paid_at = data.get("paid_at") or business_now()`.

Verification contre l'API reelle (script, section 11) :
- vente rejouee comme le fait le connecteur (avec `uuid`, sans `paid_at`) : stockee `2026-10-28T11:39:00` quand l'heure de Douala etait 11:39
  (UTC 10:39) : **PASS, aucun decalage d'une heure**. Contrepartie : l'heure stockee est celle de la **synchronisation**, pas celle de
  la vente faite hors ligne. Une vente faite a 09:00 hors ligne et synchronisee a 14:00 porte 14:00 (impacte les rapports du jour,
  la cloture de caisse si la synchronisation passe apres minuit).
- hypothese : si `paid_at` etait envoye tel que le poste l'ecrit (`2026-10-28T10:39:04.000Z`), le serveur le stocke **tel quel,
  sans conversion** (`2026-10-28T10:39:04`) : decalage de -1 h par rapport a Douala. Ce n'est PAS le cas aujourd'hui.

Correction minimale proposee (non appliquee, a decider) pour conserver l'heure reelle de la vente : (1) `DossierConnector.js` ajoute
`paid_at: op.opData.paid_at` au corps du `caisse:PUT` ; (2) `caisse_controller.create_transaction` convertit une chaine ISO
avec fuseau vers l'heure de Douala naive avant d'appeler le depot (`datetime.fromisoformat(...)`, puis `.astimezone(BUSINESS_TZ).replace(tzinfo=None)`,
comme `business_now`). Sans (2), (1) cree le decalage d'une heure.

### Flux PowerSync a travers Caddy
- PASS `POST https://localhost/sync/sync/stream` (jeton de l'API, comme le client : `Authorization: Token ...`, corps `streams`), tenu
  plus de 60 s : `checkpoint`, `checkpoint_complete`, `token_expires_in`, puis des `keep_alive` jusqu'a la fin ; aucune coupure par Caddy.
  Le chemin est bien `/sync/sync/stream` (le client ajoute `/sync/stream` a `https://DOMAIN/sync`).
- Non teste : la variante WebSocket (le SDK utilise le flux HTTP par defaut).

### Planificateur
- PASS supercronic charge la crontab (journal du conteneur scheduler) ; `cash_closure_catchup.py` et `daily_control.py` lances dans le conteneur : code 0.

### Redemarrage et recreation
- PASS `restart api` : api healthy, `/api/health` 200, connexion 200, sync liveness 200, interface 200.
- PASS `down` SANS `-v` puis `up` : lignes patients|caisse|users identiques (1|2|3), photo du produit identique (SHA-256 egal),
  utilisateurs conserves, volume `caddy_data` conserve.

## Bugs trouves et corriges

1. `deploy/Dockerfile.web` : le conteneur Caddy affichait `UTC` (image alpine sans `tzdata`) malgre `TZ=Africa/Douala`. Cause : `tzdata`
   absent. Correction : `apk add --no-cache libcap tzdata`. Image reconstruite (`date +%Z` = WAT).
2. Pas de bug dans les fichiers du compose, du Caddyfile, de `01-roles.sh`, du script d'init ni des entrypoints : tout a demarre
   au premier essai, les tags d'images existent.
3. Bugs de `smoke.sh` lui-meme, corriges pendant la mise au point : chemins `/c/...` illisibles par `docker compose` natif (chemins relatifs),
   motif Redis de la limite (`*LIMITER*`, la bibliotheque prefixe `LIMITS:`), id de role (`id` et non `role_id`), test "chunked" invalide (voir plus haut).

## Constats pour le proprietaire (non corriges, hors perimetre de la tache)

- **Le journal d'audit des connexions n'enregistre pas l'adresse IP** : `AuthController._record_access` appelle `audit_repo.log_access(...)`
  sans `ip_address` (colonne `audit_access.ip_address` toujours vide pour les connexions). Seule la lecture du consentement toxico
  enregistre `request.client.host`. L'objectif "journal d'audit avec la vraie adresse" n'est donc atteint que pour la limite de debit
  (verifie) ; pour l'audit de connexion il faut passer `request.client.host` depuis `auth_endpoints.login` (code applicatif, non modifie).
- `psql` ajoute +80,7 Mo a l'image API.
- La connexion TLS de `curl` Windows (Schannel) vers Caddy en autorite interne est coupee sur ce PC (Kaspersky, voir la note de la tache 4) ;
  Python (OpenSSL) passe. `smoke.sh` bascule alors sur un conteneur `curlimages/curl` du reseau de la pile (une seule adresse pour tout le test).

## Non verifiable ici

- Vrai DNS et certificat Let's Encrypt (ici autorite interne `local_certs`) ; delivrance reelle, renouvellement.
- Navigateur reel du PC du centre derriere l'interception HTTPS de Kaspersky ; installation du certificat, PWA, impression via le pont local.
- Envoi SFTP vers Hostinger (taches 9 et suivantes).
- IPv6 et adresses reelles des postes derriere le NAT du centre.
- Variante WebSocket de PowerSync.
- Clients reels hors ligne puis resynchronises (le test envoie la requete que le connecteur envoie, pas un navigateur).

## Commandes pour recommencer

```bash
# images (une fois, a la racine du depot)
docker build -f deploy/Dockerfile.api -t ghcr.io/rehearsal/ah2-api:local .
docker build -f deploy/Dockerfile.web --build-arg DOMAIN=localhost -t ghcr.io/rehearsal/ah2-web:local .
# repetition complete (genere deploy/rehearsal.env, ignore par git ; ports 80/443 libres requis)
bash deploy/smoke.sh            # nettoie a la fin
bash deploy/smoke.sh --keep     # garde la pile pour explorer
bash deploy/smoke.sh --down     # supprime la pile et ses volumes
```

## Passage final

Apres les derniers reglages du script (flux observe 95 s, condition stricte "plus de 60 s") : `bash deploy/smoke.sh` -> **PASS=74 FAIL=0**,
flux PowerSync : 6 lignes, derniere a t=83 s. Pile supprimee avec ses volumes a la fin ; espace libre sur C: 9,5 Go au depart, 8,8 Go a la fin
(images conservees : ah2-api, ah2-web, postgres 17.6 et 18.0, redis 7.4.5, curl).
