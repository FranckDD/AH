# Chantier 4, sous-projet 1 — Pilote PowerSync + PWA : Rendez-vous (medecin/nurse)

**Date :** 2026-09-14
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** premier sous-projet du chantier 4 (PowerSync + PWA, remplace le mode hors ligne maison `repo_offline/`). Établit le pattern d'intégration PowerSync avant de le déployer aux autres modules/rôles. Fait suite au chantier 3 (les deux fenêtres web indépendantes, médicale et secrétariat, sont terminées).

## Contexte

### Pourquoi ce chantier, et pourquoi ce module en premier

`repositories/repo_offline/` (SQLite côté desktop PyQt6 uniquement) coexiste avec trois mécanismes de synchronisation jamais reliés entre eux (colonnes `revision`/`sync_status` jamais relues, table `sync_queue`/`sync_conflicts` avec triggers jamais consommée, `SyncManager` Redis jamais instancié) — un remplacement, pas une extension. Décision utilisateur explicite (2026-09-13/14) : le desktop n'est plus la cible, la trajectoire est une conversion totale vers le web — l'hors ligne doit à terme bénéficier à toutes les interfaces déjà portées (chantier 3), pas seulement aux modules les plus récents.

**PowerSync n'a aucun SDK client Python** (SDKs officiels : JS/Web, Node.js, Flutter/Dart, Kotlin, Swift, .NET, Rust — vérifié sur `docs.powersync.com/resources/supported-platforms`, 2026-09-13). Il ne peut donc techniquement pas remplacer `repo_offline/` pour le client PyQt6, quelle que soit la conception. La cible réelle de ce chantier est exclusivement `ah2-admin-web/`, cohérent avec la décision ci-dessus.

Périmètre trop large pour un seul plan ("tout le web, pour tous les rôles") — décomposé en sous-projets, comme le chantier 3. **Module pilote : Rendez-vous (Appointments), rôles `medecin`/`nurse`**, en lecture ET écriture hors ligne (pas juste consultation) — le vrai cas d'usage hospitalier (créer/annuler un RDV sans réseau, synchronisation au retour), plus complexe à spécifier que la lecture seule mais celui qui prouve réellement le pattern.

### Infrastructure déjà en place (vérifiée fonctionnelle, 2026-09-14)

- **PowerSync self-hosted (Open Edition, Docker)**, en local à côté du Postgres natif Windows existant — pas PowerSync Cloud. Décision explicite : PowerSync Cloud exigerait un Postgres public avec SSL (`sslmode: verify-ca`), ce qui couplerait ce chantier au chantier 5 (hébergement) ; le self-hosted n'exige que la joignabilité réseau du service vers Postgres, qui fonctionne déjà en local.
- Répertoire `powersync/` à la racine du repo : `docker-compose.yaml` (2 conteneurs — service PowerSync + Postgres dédié au stockage interne PowerSync, aucune donnée AH2 dans ce dernier), `service.yaml`, `sync-config.yaml`, `.env`/`.env.example`.
- `wal_level` du Postgres natif passé de `replica` à `logical` (`C:/Program Files/PostgreSQL/17/data/postgresql.conf`), service Windows redémarré.
- `CREATE PUBLICATION powersync FOR ALL TABLES` créée sur la base `AH2` (choix explicite de l'utilisateur : toutes les tables plutôt qu'une publication restreinte, pour ne pas avoir à l'étendre à chaque nouveau module).
- Réplication confirmée active (`curl http://localhost:18080/probes/liveness` → `{"ready":true,"started":true}`, logs `Initial replication already done`).
- **Ce qui reste volontairement placeholder, à remplacer par ce sous-projet** : `client_auth` utilise une clé HS256 de développement jetable (pas le vrai `JWT_SECRET`) ; `sync-config.yaml` contient un stream brut (`SELECT * FROM appointments`, `SELECT * FROM patients`) sans portée par rôle ni chemin d'écriture.

### Découverte de cadrage majeure : aucun filtrage par rôle n'existe aujourd'hui côté backend

Vérifié directement dans le code (pas supposé) : `GET /appointments/` sans `doctor_id` renvoie **tous les rendez-vous de tous les médecins**, à n'importe quel rôle authentifié (`appointment_endpoints.py`, aucun `Depends(role_required(...))` sur les routes de lecture/écriture ; `appointment_repo.py::list_paginated_with_relations` n'applique aucun filtre si `doctor_id`/`patient_id` sont `None`). Le frontend actuel ne passe jamais `doctor_id` sur l'appel de liste principal. Aucune table "équipe de soins" ne relie une infirmière à des médecins précis — la relation n'existe pas en base.

**Décision produit explicite de l'utilisateur** : les règles de sync PowerSync introduisent une vraie portée pour `medecin` (chacun ne synchronise que ses propres RDV), et laissent `nurse` inchangé (tout voir, comme aujourd'hui) — faute de relation infirmière↔médecins en base, inventer une restriction pour `nurse` serait une fonctionnalité nouvelle hors périmètre de ce pilote, pas un correctif.

### Identifiants — piège déjà rencontré à plusieurs reprises dans ce projet

`appointments` a pour clé primaire applicative **`id`** (pas `appointment_id` — le paramètre de route `{appointment_id}` mappe sur la colonne `id`). `patients` a pour clé primaire **`patient_id`** (différent). Les deux tables ont chacune une colonne `uuid` (`gen_random_uuid()` par défaut) **jamais exposée aujourd'hui** dans les schémas Pydantic ni l'ORM — voir "Identité des lignes hors ligne" ci-dessous, cette colonne devient centrale pour ce pilote.

### `status` des RDV — vérifié, pas de contrainte CHECK (leçon déjà apprise ce projet)

`ci/schema_only.sql` : `status character varying(20) DEFAULT 'pending'`, **aucune contrainte CHECK**. Le domaine (`pending`/`cancelled`/`completed`) n'est imposé que côté application (`appointmentStore.js::APPOINTMENT_STATUSES`). Confirmé par lecture directe du schéma, pas supposé — une écriture hors ligne avec un statut hors domaine ne serait rejetée par rien côté Postgres, seulement par la validation applicative qu'il faut donc préserver côté client PowerSync.

## Portée

### 1. Identité des lignes hors ligne — utiliser la colonne `uuid` existante, pas l'`id` entier

PowerSync a besoin qu'un client hors ligne puisse créer une ligne avec une identité stable **avant** qu'un serveur ne lui attribue quoi que ce soit — un entier auto-incrémenté (`id`) ne peut pas être prédit côté client. Les tables `appointments` et `patients` ont déjà une colonne `uuid` avec `gen_random_uuid()` par défaut, jamais utilisée aujourd'hui par l'ORM/les schémas Pydantic.

**Décision :** la ligne PowerSync locale (SQLite navigateur) est clée par `uuid` (généré côté client à la création, format UUID v4 standard). Changements backend additifs requis :
- `AppointmentCreate` (Pydantic) gagne un champ optionnel `uuid: Optional[str] = None`.
- `AppointmentRepository.create()` utilise le `uuid` fourni par le payload s'il est présent (au lieu de laisser Postgres générer le sien) ; si absent (création via l'UI en ligne classique, chemin existant inchangé), comportement actuel préservé (Postgres génère `gen_random_uuid()`).
- `AppointmentResponse` expose `uuid` en lecture, pour que le client puisse faire correspondre sa ligne locale à la ligne confirmée par le serveur après upload.

Aucune migration de schéma nécessaire (la colonne existe déjà) — uniquement des champs Pydantic/ORM à exposer.

### 2. Règles de sync PowerSync (remplace le placeholder de bring-up)

`powersync/sync-config.yaml` définit deux streams distincts, **ni l'un ni l'autre en `auto_subscribe: true`** — contrairement au stream unique de bring-up, la souscription doit être décidée par le client selon le rôle (lu depuis le claim `roles` du JWT, déjà disponible dans `authStore` avant l'initialisation de PowerSync), pas automatique : un `medecin` qui recevrait les deux streams se retrouverait avec la portée large de `all_appointments` en plus de la sienne, annulant la restriction voulue. Le code client appelle explicitement `db.syncStream('my_appointments').subscribe()` ou `db.syncStream('all_appointments').subscribe()`, jamais les deux à la fois pour un même utilisateur.

- **`my_appointments`** (paramétré par l'utilisateur connecté, via le claim JWT `sub`) : `SELECT * FROM appointments WHERE doctor_id = request.user_id()` — souscrit par le client uniquement quand le rôle actif est `medecin`. `request.user_id()` résout `sub` du JWT (voir section Auth ci-dessous) ; nécessite un cast cohérent avec le type de `doctor_id` (entier) alors que `sub` est stocké comme chaîne dans le JWT actuel (`str(user.user_id)`) — point à vérifier empiriquement pendant l'implémentation (cast `request.user_id()::int` côté règle de sync si nécessaire).
- **`all_appointments`** : `SELECT * FROM appointments` sans filtre — souscrit par le client uniquement quand le rôle actif est `nurse`.
- **`patients_lookup`** : `SELECT patient_id, code_patient, first_name, last_name, contact_phone FROM patients WHERE is_deleted = false` — colonnes explicitement listées (pas `SELECT *`, les données patients sont sensibles et ce pilote n'a besoin que de l'affichage nom/contact dans la liste de RDV), disponible aux deux rôles.

Pas de bucket paramétré par `patient_id` — la volumétrie patients justifie une synchronisation complète en lecture pour ce pilote (à revisiter si le volume réel s'avère trop important une fois mesuré).

### 3. Chemin d'écriture hors ligne — relié aux endpoints REST existants, pas de nouvelle API

Le SDK JS de PowerSync met les écritures locales dans une file CRUD ; l'app fournit un connecteur (`uploadData()`) qui traduit chaque opération en appel REST vers l'API FastAPI existante — le backend reste l'unique source de vérité en écriture, PowerSync ne le contourne jamais.

**Opérations couvertes par ce pilote** (mapping CRUD PowerSync → endpoint existant) :
- `PUT` (création locale) → `POST /appointments/` avec le `uuid` client dans le payload (voir section 1). Réponse contient l'`id` serveur définitif ; le connecteur met à jour la ligne locale.
- `PATCH` (modification) → `PUT /appointments/{id}` si la ligne a déjà un `id` serveur confirmé ; si la ligne est encore "en attente de confirmation" (créée hors ligne, jamais uploadée), le connecteur doit fusionner les modifications dans l'opération de création encore en file plutôt que d'émettre un PUT sur un `id` qui n'existe pas encore côté serveur — détail d'implémentation à trancher dans le plan, pas entièrement résolu ici.
- Annulation/complétion → `POST /appointments/{id}/cancel` et `.../complete` (endpoints existants, inchangés).

**Explicitement hors périmètre de ce pilote — suppression matérielle (`DELETE /appointments/{id}`)** : l'endpoint backend existe déjà mais **n'est appelé par aucun code frontend actuel** (aucune UI de suppression de RDV n'existe aujourd'hui). Ce pilote ne câble pas ce chemin — fidèle à ce que l'app fait réellement aujourd'hui, pas une fonctionnalité nouvelle. Si un besoin de suppression hors ligne émerge plus tard, ce sera une extension explicite, pas un oubli.

**Validation de `status`** : puisque rien ne la garantit côté Postgres (section Contexte), le connecteur d'upload ne doit jamais transmettre de valeur de statut hors du domaine `{pending, cancelled, completed}` — la validation déjà présente côté `appointmentStore.js`/`AppointmentModal.vue` s'applique de la même façon avant la mise en file PowerSync, pas seulement avant un appel réseau direct.

### 4. Authentification — remplacer la clé de développement par le vrai JWT

Le JWT applicatif (créé dans `auth_endpoints.py::login()`, bibliothèque `python-jose`, HS256) contient déjà `sub` (user_id), `roles`, `exp`, `ver`, `jti`, `iss` (`ah2-api`), `aud` (`ah2-web`) — **aucun header `kid`** n'est actuellement défini sur le token émis.

Changements requis :
- `client_auth` de `powersync/service.yaml` passe d'une clé de dev à une clé statique HS256 correspondant au vrai `JWT_SECRET` applicatif (même mécanisme JWKS `kty: oct`, mais avec le secret réel plutôt qu'un secret jetable — voir `docs.powersync.com/configuration/auth/custom`).
- `audience` de `client_auth` doit accepter `"ah2-web"` (l'`aud` réel émis par le backend), pas l'`audience` de dev actuelle.
- Point à vérifier empiriquement pendant l'implémentation, pas supposé résolu ici : PowerSync exige-t-il une correspondance stricte de `kid` entre le JWT et la clé JWKS configurée, ou accepte-t-il une clé unique sans `kid` sur le token ? Si une correspondance stricte est exigée, `auth_endpoints.py::login()` devra ajouter un header `kid` fixe (ex. `jose_jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM, headers={"kid": "ah2-hs256-1"})`) et `service.yaml` devra déclarer le même `kid` — changement additif d'une ligne, sans impact sur les consommateurs JWT existants (`get_current_user` ne vérifie pas le header).
- Le JWT expire après `JWT_EXPIRE_MINUTES` (60 par défaut) et devient invalide immédiatement après un logout (`ver` incrémenté en base) — le connecteur PowerSync côté client doit donc rafraîchir ses credentials (nouvelle réponse à `fetchCredentials()`) de façon cohérente avec le cycle de vie du JWT déjà en place (SEC-09), pas inventer un mécanisme de refresh parallèle.

### 5. PWA — coquille installable, aucun asset de marque n'existe aujourd'hui

Aucune infrastructure PWA n'existe (`ah2-admin-web/public/` ne contient que le SVG par défaut de Vite ; `index.html` n'a ni `theme-color`, ni lien de manifeste). Le nom/logo de l'app est aujourd'hui **dynamique par tenant** (`configStore.js::structureInfo`, uploadé par l'admin via `POST /config/structure`) — incompatible avec un manifeste PWA statique, qui exige des icônes fichiers fixes au moment de l'installation.

**Décision pour ce pilote :** générer un jeu d'icônes provisoire (favicon, 192×192, 512×512, variante "maskable"), remplaçable plus tard sans impact sur le reste — ce n'est pas un travail de design de marque, juste ce qu'exige un manifeste PWA valide. `vite-plugin-pwa` (Workbox sous le capot) gère le manifeste + service worker de cache d'assets statiques — une préoccupation distincte de la synchronisation de données PowerSync (le service worker ne cache pas les données, seulement le shell applicatif JS/CSS/icônes).

**Contexte sécurisé requis** : OPFS (stockage SQLite persistant du SDK PowerSync web) et les service workers exigent un contexte sécurisé (HTTPS, ou l'exception `localhost` que les navigateurs accordent). L'environnement actuel (API sur `127.0.0.1:8000`, dev server Vite local) reste dans l'exception `localhost` — aucun blocage pour le développement/test de ce pilote, mais toute exposition future hors `localhost` (chantier 5) devra être en HTTPS pour que la PWA continue de fonctionner.

## Vérification

- Le container `powersync/` réplique bien uniquement `appointments`/`patients` selon les nouveaux streams (pas le `SELECT *` de bring-up).
- Connexion en tant que `medecin` : ne reçoit que ses propres RDV côté PowerSync (vérifier avec un 2e compte médecin que ses RDV ne sont pas visibles). Connexion en tant que `nurse` : reçoit tous les RDV, comme le comportement actuel.
- Test réel de coupure réseau : couper la connexion (DevTools "Offline" ou arrêt du conteneur PowerSync), créer un RDV, modifier son statut, reconnecter — le RDV apparaît côté serveur avec le bon `doctor_id`/`patient_id`, et la ligne locale se met à jour avec l'`id` serveur définitif.
- La PWA est installable (Chrome/Edge "Installer l'application" visible), fonctionne au chargement initial hors ligne après une première visite en ligne.
- Aucune régression sur le chemin en ligne existant (`AppointmentsList.vue`/`AppointmentModal.vue` continuent de fonctionner à l'identique quand le réseau est disponible — PowerSync est une couche additive, pas un remplacement du gateway REST direct pour les vues non encore migrées).

## Hors périmètre

- Suppression matérielle de RDV hors ligne (endpoint existant, jamais câblé côté UI — voir section 3).
- Relation infirmière↔médecins (nécessaire pour scoper `nurse` un jour) — nouvelle table/logique métier hors périmètre de ce pilote.
- Déploiement PowerSync hors du réseau local (PowerSync Cloud, hébergement distant) — chantier 5.
- Extension du pattern à d'autres modules (Patients, Prescriptions, Dossier Médical, Stock, Caisse, Consultations) — sous-projets suivants du chantier 4, une fois ce pilote validé.
- Design de marque réel pour les icônes PWA (logo définitif, charte graphique) — le jeu d'icônes de ce pilote est provisoire.
- Résolution de conflits avancée (fusion à trois voies, historique de versions) — ce pilote s'appuie sur ce que l'API REST existante fait déjà (dernière écriture gagnante via les timestamps `updated_at`), pas de logique de fusion PowerSync-spécifique.
