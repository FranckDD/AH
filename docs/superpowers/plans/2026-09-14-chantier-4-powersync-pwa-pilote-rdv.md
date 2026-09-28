# Chantier 4, sous-projet 1 : Pilote PowerSync + PWA (Rendez-vous) — Plan d'implémentation

> **Pour les exécutants agentiques :** SOUS-COMPÉTENCE REQUISE : utiliser superpowers:subagent-driven-development pour exécuter ce plan tâche par tâche. Les étapes utilisent la syntaxe case à cocher (`- [ ]`) pour le suivi.

**Objectif :** faire fonctionner le module Rendez-vous (`medecin`/`nurse`) en lecture ET écriture hors ligne, via PowerSync (self-hosted, déjà en place) + une coquille PWA installable, en remplaçant le chemin de données direct REST de ce seul module par une synchronisation locale — sans toucher aux autres modules ni casser le chemin en ligne existant.

**Architecture :** le backend FastAPI reste l'unique source de vérité en écriture — PowerSync ajoute une file CRUD locale (SQLite navigateur) et un connecteur qui traduit chaque opération en appel vers les endpoints REST `/appointments/*` déjà existants. Les lignes créées hors ligne sont identifiées par la colonne `uuid` déjà présente (mais jamais exposée) sur `appointments`/`patients`, utilisée comme clé primaire locale PowerSync (convention officielle : `SELECT uuid::text AS id, ... FROM appointments`) — l'entier `id` généré par Postgres devient une simple colonne synchronisée (`server_id`), disponible seulement après confirmation serveur.

**Tech Stack :** `@powersync/web` (SDK JS core, pas le package `@powersync/vue` — encore en version bêta 0.0.x, écarté pour ce pilote au profit d'un `db.watch()` géré à la main dans le store Pinia existant), `vite-plugin-wasm` + `vite-plugin-top-level-await` (requis par `@powersync/web`), `vite-plugin-pwa` (manifeste + service worker), Vue 3 / Pinia (conventions déjà établies dans ce projet).

**Spec :** `docs/superpowers/specs/2026-09-14-chantier-4-powersync-pwa-pilote-rdv-design.md`

## Contraintes globales

- **Aucun commit git à aucun moment de ce plan**, comme tout le chantier 3 précédent — l'utilisateur a des dizaines de fichiers modifiés non commités dans son arbre de travail. Diffing manuel (snapshot + `diff -u`), pas de commits.
- **Le backend FastAPI reste l'unique chemin d'écriture.** PowerSync ne parle jamais directement à Postgres en écriture applicative — le connecteur (`AppointmentConnector.js`) appelle les endpoints REST existants (`AppointmentGateway.js`), jamais de nouvelle route API pour ce pilote.
- **Identifiants — piège déjà rencontré à plusieurs reprises dans ce projet :** `appointments.id` (entier, Postgres) ≠ `appointments.uuid` (déjà présent, `gen_random_uuid()` en défaut serveur, jamais exposé aujourd'hui) ≠ l'`id` (texte) implicite de chaque table locale PowerSync, qui **doit contenir la valeur du `uuid` Postgres**, pas l'entier. `patients.patient_id` (entier) est la clé primaire patients, différente de `appointments.id`. Ne jamais confondre ces quatre identifiants dans le code de ce plan.
- **`status` n'a aucune contrainte CHECK côté Postgres** (vérifié dans `ci/schema_only.sql` — leçon déjà apprise dans ce projet, ne pas resupposer une contrainte qui n'existe pas, mais ne pas non plus supposer qu'on peut écrire n'importe quoi : le domaine `{pending, cancelled, completed}` n'est imposé que côté application, donc le connecteur d'upload doit continuer à le respecter strictement).
- **Aucune régression sur le chemin en ligne existant.** Si un test manuel de ce plan échoue à distinguer "PowerSync déconnecté" de "erreur", le chemin REST direct (`AppointmentGateway.js` tel qu'il existe aujourd'hui) doit continuer à fonctionner pour les autres vues qui ne passent pas par ce pilote.
- **Portée gelée par la spec, ne pas l'élargir pendant l'implémentation :** pas de suppression matérielle de RDV hors ligne (endpoint existant, jamais câblé côté UI), pas de relation infirmière↔médecins, pas de résolution de conflit avancée (dernière écriture gagnante, comme le REST existant le fait déjà), pas de design de marque réel pour les icônes PWA (jeu provisoire).
- **Infrastructure déjà en place, ne pas la recréer** : conteneurs Docker dans `powersync/` (service PowerSync port `18080`, stockage interne `pg-storage` port `5433`), `wal_level=logical` déjà actif sur le Postgres natif, publication `powersync FOR ALL TABLES` déjà créée. Ce plan modifie `powersync/service.yaml`/`sync-config.yaml` (contenu, pas la structure des conteneurs) et redémarre le conteneur PowerSync (`docker restart powersync-powersync-1`), jamais `docker compose down -v` (détruirait le volume de stockage interne).

---

## Tâche 1 : Backend — exposer `uuid` sur les RDV, sécuriser le JWT pour PowerSync

**Fichiers :**
- Modifier : `api_backend/backend_app/routes/appointment/appointment_schemas.py`
- Modifier : `repositories/appointment_repo.py`
- Modifier : `api_backend/backend_app/routes/auth/auth_endpoints.py`

**Interfaces :**
- Produit : `AppointmentCreate.uuid: Optional[str]`, `AppointmentResponse.uuid: str` — consommés par le connecteur PowerSync (Tâche 4).
- Produit : header JWT `kid: "ah2-hs256-1"` sur tout token émis par `/auth/login` — consommé par `powersync/service.yaml` (Tâche 2).

- [ ] **Étape 1 : Ajouter `uuid` à `AppointmentCreate` et `AppointmentResponse`**

Dans `api_backend/backend_app/routes/appointment/appointment_schemas.py`, `AppointmentCreate` (actuellement lignes 25-33) :

```python
class AppointmentCreate(BaseModel):
    # on ne hérite PAS de AppointmentBase pour éviter les conflits Pylance
    patient_id: int = Field(..., description="Identifiant du patient")
    appointment_date: date = Field(..., description="Date du rendez-vous")
    appointment_time: time = Field(..., description="Heure du rendez-vous")
    specialty: Optional[str] = Field(None, description="Spécialité médicale")
    reason: Optional[str] = Field(None, description="Motif / commentaire")
    uuid: Optional[str] = Field(None, description="UUID client (creation hors ligne PowerSync) - si absent, Postgres en genere un")

    model_config = {"from_attributes": True}
```

`AppointmentResponse` (actuellement lignes 47-55) :

```python
class AppointmentResponse(AppointmentBase):
    id: int
    uuid: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # si tu préfères, remplace dict par un schéma Pydantic pour patient/doctor
    patient: Optional[dict] = None
    doctor: Optional[dict] = None

    model_config = {"from_attributes": True}
```

- [ ] **Étape 2 : Faire passer `uuid` dans `AppointmentRepository.create()`**

Dans `repositories/appointment_repo.py`, méthode `create()` (actuellement lignes 17-65), le tuple `allowed` (ligne 54) et la construction de l'objet ORM (lignes 57-60) :

```python
            # Allowed fields — adapt to your model if names differ
            allowed = ("patient_id", "doctor_id", "specialty",
                    "appointment_date", "appointment_time", "reason", "status", "uuid")

            appt = Appointment()
            for k in allowed:
                if k in data:
                    value = data[k]
                    # Le modele attend un uuid.UUID (colonne UUID(as_uuid=True)),
                    # pas une chaine brute - convertir si un uuid client (string)
                    # est fourni (creation hors ligne PowerSync, Tache 4). Si
                    # absent, le defaut Postgres (gen_random_uuid()) s'applique.
                    if k == "uuid" and value is not None and not isinstance(value, uuid.UUID):
                        value = uuid.UUID(str(value))
                    setattr(appt, k, value)
```

Ajouter `import uuid` en tête de `repositories/appointment_repo.py` (le fichier n'importe actuellement que `Session`/`joinedload`, `func`/`and_`/`extract`, des types `typing`, `datetime`/`date`/`time`, `Appointment`, `DatabaseManager`, `Patient` — aucun import `uuid` existant, pas de risque de doublon).

**Note pour l'exécutant :** la colonne `appointments.uuid` a `unique=True` (`models/appointment.py:29`). Si le connecteur PowerSync (Tâche 4) retente un upload après un timeout réseau sur une création déjà réussie côté serveur, ce second `POST /appointments/` avec le même `uuid` lèvera une erreur d'intégrité (contrainte unique violée) — c'est le comportement correct et attendu (preuve que la création a déjà réussi), pas un bug à corriger ici. Le connecteur doit traiter cette erreur spécifique comme un succès plutôt que comme un échec à re-essayer indéfiniment — traité en Tâche 4, juste documenté ici pour que l'implémenteur de cette tâche ne la "corrige" pas à tort en assouplissant la contrainte.

- [ ] **Étape 3 : Ajouter un `kid` fixe aux JWT émis**

Dans `api_backend/backend_app/routes/auth/auth_endpoints.py`, fonction `login()` (actuellement ligne 69) :

```python
    token = jose_jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM, headers={"kid": "ah2-hs256-1"})  # pyright: ignore[reportArgumentType]
```

C'est un changement additif — `get_current_user` (même fichier) ne vérifie pas le header `kid` aujourd'hui et continuera de fonctionner à l'identique pour tous les tokens déjà émis ou à émettre. Ce `kid` sera repris tel quel dans `powersync/service.yaml` (Tâche 2).

- [ ] **Étape 4 : Vérification**

Lancer le backend (`uvicorn` ou la commande habituelle du projet), faire un `POST /auth/login` réel (via curl ou l'UI), décoder le token reçu (ex. sur jwt.io ou `python -c "from jose import jwt; print(jwt.get_unverified_header('<token>'))"`) et confirmer que `{"kid": "ah2-hs256-1"}` apparaît dans le header. Faire un `POST /appointments/` sans `uuid` dans le payload (chemin en ligne existant, ex. via `AppointmentModal.vue` dans le navigateur) et confirmer que ça fonctionne toujours à l'identique (pas de régression) — la réponse doit maintenant inclure un champ `uuid` non nul (généré par Postgres).

---

## Tâche 2 : Config PowerSync réelle — auth JWT + règles de sync par rôle

**Fichiers :**
- Modifier : `powersync/service.yaml`
- Modifier : `powersync/sync-config.yaml`
- Modifier : `powersync/.env` et `powersync/.env.example`

**Interfaces :**
- Consomme : `JWT_SECRET`/`JWT_ALGORITHM` réels (déjà dans `.env` racine du projet, PAS `powersync/.env` — copier la valeur, ne jamais committer `powersync/.env`), le `kid` fixé en Tâche 1.
- Produit : streams `my_appointments`, `all_appointments`, `patients_lookup` — consommés par `powersync-client.js` (Tâche 4).

- [ ] **Étape 1 : Encoder le vrai `JWT_SECRET` en clé JWKS**

Récupérer la valeur réelle de `JWT_SECRET` depuis le `.env` racine du projet (pas `powersync/.env`). L'encoder en base64url (le format `k` attendu par une clé JWK `oct`) :

```bash
printf '%s' "<valeur reelle de JWT_SECRET>" | openssl base64 -A | tr '+/' '-_' | tr -d '='
```

Ajouter le résultat dans `powersync/.env` (remplace `PS_DEV_HS256_SECRET`, qui devient inutile — supprimer cette variable, la remplacer par) :

```
PS_APP_HS256_SECRET=<resultat de la commande ci-dessus>
```

Faire de même dans `powersync/.env.example` (avec `CHANGEME` comme valeur, comme les autres secrets de ce fichier), en remplaçant la ligne `PS_DEV_HS256_SECRET=CHANGEME` par `PS_APP_HS256_SECRET=CHANGEME`.

- [ ] **Étape 2 : Mettre à jour `client_auth` dans `service.yaml`**

Remplacer le bloc `client_auth` actuel de `powersync/service.yaml` :

```yaml
client_auth:
  audience: ["ah2-web"]
  jwks:
    keys:
      - kty: oct
        alg: HS256
        kid: ah2-hs256-1
        k: !env PS_APP_HS256_SECRET
```

(`audience` passe de `["ah2-dev"]` à `["ah2-web"]` — le vrai `aud` émis par `auth_endpoints.py::login()`. `kid` doit être identique au `kid` fixé en Tâche 1, Étape 3.)

Mettre à jour aussi `docker-compose.yaml` : remplacer la variable d'environnement `PS_DEV_HS256_SECRET` par `PS_APP_HS256_SECRET` dans le bloc `environment` du service `powersync` (deux occurrences : la clé et sa valeur `${PS_APP_HS256_SECRET}`).

- [ ] **Étape 3 : Remplacer le placeholder de bring-up par les vraies règles de sync**

Remplacer entièrement le contenu de `powersync/sync-config.yaml` :

```yaml
# yaml-language-server: $schema=https://unpkg.com/@powersync/service-sync-rules@latest/schema/sync_rules.json
#
# Regles de sync du pilote Rendez-vous (chantier 4, sous-projet 1).
# Convention PowerSync : la colonne locale "id" (implicite, cle primaire
# de chaque table SQLite cote client) DOIT correspondre a une colonne
# texte stable connue avant confirmation serveur - on utilise donc la
# colonne "uuid" (deja presente sur appointments/patients, generee par
# Postgres) aliasee "AS id", jamais l'entier auto-incremente "id" de
# Postgres (renomme "server_id" ici pour eviter toute confusion).
#
# my_appointments/all_appointments/patients_lookup ne sont PAS
# auto_subscribe : c'est le client (ah2-admin-web) qui choisit lequel
# souscrire selon le role de l'utilisateur connecte (voir
# powersync-client.js, Tache 4) - sinon un medecin recevrait aussi la
# portee large de all_appointments, annulant la restriction voulue.
#
# Le service doit etre redemarre apres toute modification de ce fichier
# (docker restart powersync-powersync-1).

config:
  edition: 3

streams:
  my_appointments:
    auto_subscribe: false
    queries:
      - SELECT uuid::text AS id, id AS server_id, patient_id, doctor_id,
          specialty, appointment_date::text AS appointment_date,
          appointment_time::text AS appointment_time, reason, status,
          created_at::text AS created_at, updated_at::text AS updated_at
        FROM appointments
        WHERE doctor_id = request.user_id()

  all_appointments:
    auto_subscribe: false
    queries:
      - SELECT uuid::text AS id, id AS server_id, patient_id, doctor_id,
          specialty, appointment_date::text AS appointment_date,
          appointment_time::text AS appointment_time, reason, status,
          created_at::text AS created_at, updated_at::text AS updated_at
        FROM appointments

  patients_lookup:
    auto_subscribe: false
    queries:
      - SELECT patient_id::text AS id, patient_id, code_patient,
          first_name, last_name, contact_phone
        FROM patients
        WHERE is_deleted = false

  doctors_lookup:
    auto_subscribe: false
    queries:
      # Colonnes limitees a ce qui est affiche (nom du medecin sur un RDV) -
      # jamais password_hash/postgres_role/email, meme si "users" est
      # couverte par la publication FOR ALL TABLES cote Postgres.
      - SELECT user_id::text AS id, user_id, username, full_name
        FROM users
```

**Note pour l'exécutant :** `request.user_id()` résout le claim `sub` du JWT — qui est une chaîne (`str(user.user_id)`, voir `auth_endpoints.py`) — comparée à `doctor_id`, une colonne entière. Si le redémarrage à l'Étape 4 échoue avec une erreur de comparaison de type, ajouter un cast explicite côté requête (`WHERE doctor_id = request.user_id()::int` ou équivalent) — point que la spec elle-même signale comme à vérifier empiriquement, pas supposé résolu à l'avance.

- [ ] **Étape 4 : Redémarrer et vérifier**

```bash
docker restart powersync-powersync-1
```

Attendre ~10s, puis `docker logs powersync-powersync-1 --tail 30` — chercher `Loaded sync config` et l'absence de nouvelle erreur (pas de `Replication error`). `curl http://localhost:18080/probes/liveness` doit renvoyer `{"ready":true,"started":true,...}`.

---

## Tâche 3 : Outillage frontend — dépendances, build Vite, coquille PWA

**Fichiers :**
- Modifier : `ah2-admin-web/package.json`
- Modifier : `ah2-admin-web/vite.config.js`
- Modifier : `ah2-admin-web/index.html`
- Créer : `ah2-admin-web/public/pwa-192x192.png`, `ah2-admin-web/public/pwa-512x512.png`, `ah2-admin-web/public/pwa-maskable-512x512.png`

**Interfaces :**
- Produit : plugins Vite (`wasm`, `topLevelAwait`, `VitePWA`) nécessaires pour que `@powersync/web` (Tâche 4) compile et s'exécute dans le navigateur.

- [ ] **Étape 1 : Installer les dépendances**

Depuis `ah2-admin-web/` :

```bash
npm install @powersync/web
npm install -D vite-plugin-wasm vite-plugin-top-level-await vite-plugin-pwa
```

- [ ] **Étape 2 : Générer un jeu d'icônes provisoire**

Aucun asset de marque n'existe dans ce projet aujourd'hui (`ah2-admin-web/public/` ne contient que le SVG par défaut de Vite — vérifié dans la spec). Générer 3 PNG carrés unis (pas de design, juste ce qu'exige un manifeste PWA valide pour être installable) :
- `ah2-admin-web/public/pwa-192x192.png` (192×192)
- `ah2-admin-web/public/pwa-512x512.png` (512×512)
- `ah2-admin-web/public/pwa-maskable-512x512.png` (512×512, avec une marge de sécurité ~10% pour le rognage "maskable" — un simple aplat de couleur centré suffit pour ce pilote)

N'importe quel outil disponible dans l'environnement de l'implémenteur convient (script Python/Pillow, ImageMagick, ou un générateur en ligne suivi d'un téléchargement manuel) — le contenu visuel exact n'a aucune importance pour ce pilote (voir Hors périmètre de la spec : "design de marque réel" explicitement exclu). Utiliser une couleur simple cohérente avec la palette déjà utilisée ailleurs dans l'app (ex. `#0d9488`, le teal déjà utilisé dans les boutons des modales de ce projet).

- [ ] **Étape 3 : Configurer `vite.config.js`**

Remplacer le contenu actuel de `ah2-admin-web/vite.config.js` :

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import wasm from 'vite-plugin-wasm'
import topLevelAwait from 'vite-plugin-top-level-await'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    wasm(),
    topLevelAwait(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['pwa-192x192.png', 'pwa-512x512.png', 'pwa-maskable-512x512.png'],
      manifest: {
        name: 'AH2',
        short_name: 'AH2',
        description: 'AH2 - Gestion hospitaliere',
        theme_color: '#0d9488',
        background_color: '#ffffff',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Ne met en cache que le shell applicatif (JS/CSS/HTML/icones) -
        // PowerSync gere la synchronisation des donnees separement, le
        // service worker ne doit jamais intercepter les appels /appointments/*
        // ni les requetes vers le service PowerSync (port 18080).
        globPatterns: ['**/*.{js,css,html,png,svg,ico}'],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // @powersync/web embarque des web workers + fichiers WASM (wa-sqlite) -
  // doit etre exclu de l'optimisation de dependances Vite, sinon le build
  // echoue ou le worker ne charge pas correctement au runtime.
  optimizeDeps: {
    exclude: ['@journeyapps/wa-sqlite', '@powersync/web'],
  },
  worker: {
    format: 'es',
    plugins: () => [wasm(), topLevelAwait()],
  },
})
```

- [ ] **Étape 4 : Ajouter le lien de manifeste et le theme-color dans `index.html`**

Dans `ah2-admin-web/index.html`, ajouter dans le `<head>` (après la ligne `<link rel="icon" ...>` existante) :

```html
    <meta name="theme-color" content="#0d9488" />
```

(`vite-plugin-pwa` injecte lui-même le lien `<link rel="manifest">` et l'enregistrement du service worker au build — ne pas les ajouter manuellement, ce serait dupliqué.)

- [ ] **Étape 5 : Vérification**

`cd ah2-admin-web && npm run build` doit réussir sans erreur, avec un fichier `dist/manifest.webmanifest` et un `dist/sw.js` générés (`ls dist/` pour confirmer). `npm run dev` doit démarrer sans erreur liée aux nouveaux plugins (les erreurs `@powersync/web` elles-mêmes ne peuvent apparaître qu'à la Tâche 4, une fois le SDK réellement importé — cette tâche vérifie seulement que l'outillage de build ne casse rien).

---

## Tâche 4 : Client PowerSync — schéma local, bootstrap, connecteur

**Fichiers :**
- Créer : `ah2-admin-web/src/powersync-client/AppSchema.js`
- Créer : `ah2-admin-web/src/powersync-client/client.js`
- Créer : `ah2-admin-web/src/powersync-client/AppointmentConnector.js`
- Modifier : `ah2-admin-web/src/services/AppointmentGateway.js` (une seule méthode, `createAppointment` — voir Étape 3)

**Interfaces :**
- Produit : `db` (instance `PowerSyncDatabase` exportée par `client.js`), `connectPowerSync(role)`, `disconnectPowerSync()` — consommés par `auth.js`/`App.vue` (Tâche 5) et `appointmentStore.js` (Tâche 6).
- Consomme : `useAuthStore` (`@/stores/auth`, déjà existant — `token`, `userRole`), `AppointmentGateway` (`@/services/AppointmentGateway`, déjà existant, réutilisé tel quel dans le connecteur sauf la modification de l'Étape 3).

- [ ] **Étape 1 : Écrire `AppSchema.js`**

```js
import { column, Schema, Table } from '@powersync/web';

// La cle primaire "id" de chaque table est implicite (texte, geree par
// PowerSync) et DOIT contenir la valeur de la colonne "uuid" Postgres,
// jamais l'entier "id" de Postgres - voir sync-config.yaml (Tache 2) qui
// fait deja cet aliasing cote serveur (SELECT uuid::text AS id, ...).
// "server_id" ci-dessous est l'entier Postgres, disponible seulement une
// fois la ligne confirmee par le serveur (null pour une creation encore
// hors ligne, jamais uploadee).

const appointments = new Table(
  {
    server_id: column.integer,
    patient_id: column.integer,
    doctor_id: column.integer,
    specialty: column.text,
    appointment_date: column.text,
    appointment_time: column.text,
    reason: column.text,
    status: column.text,
    created_at: column.text,
    updated_at: column.text,
  },
  { indexes: { by_doctor: ['doctor_id'], by_date: ['appointment_date'] } }
);

const patients_lookup = new Table({
  patient_id: column.integer,
  code_patient: column.text,
  first_name: column.text,
  last_name: column.text,
  contact_phone: column.text,
});

const doctors_lookup = new Table({
  user_id: column.integer,
  username: column.text,
  full_name: column.text,
});

export const AppSchema = new Schema({
  appointments,
  patients_lookup,
  doctors_lookup,
});
```

- [ ] **Étape 2 : Écrire `AppointmentConnector.js`**

```js
import { UpdateType } from '@powersync/web';
import { useAuthStore } from '@/stores/auth';
import { AppointmentGateway } from '@/services/AppointmentGateway';
import { API_URL } from '@/services/api';

// URL du service PowerSync self-hoste (voir powersync/.env, PS_PORT) -
// distincte de l'API FastAPI (API_URL). A definir dans .env.local du
// frontend si elle differe de la valeur par defaut locale.
const POWERSYNC_URL = import.meta.env.VITE_POWERSYNC_URL || 'http://localhost:18080';

// Codes d'erreur qu'il ne faut JAMAIS re-essayer indefiniment - abandonner
// l'operation et la retirer de la file plutot que de bloquer toute la
// synchronisation dessus. Voir Tache 1, note sur la contrainte unique
// "uuid" : un 409/422 sur une creation deja reussie signifie un succes
// deja acquis, pas un echec a re-tenter.
function isFatalUploadError(error) {
  const status = error?.response?.status;
  return status === 400 || status === 404 || status === 409 || status === 422;
}

export class AppointmentConnector {
  async fetchCredentials() {
    const authStore = useAuthStore();
    if (!authStore.token) {
      throw new Error('Aucun token d\'authentification disponible pour PowerSync.');
    }
    return {
      endpoint: POWERSYNC_URL,
      token: authStore.token,
    };
  }

  async uploadData(database) {
    const transaction = await database.getNextCrudTransaction();
    if (!transaction) {
      return;
    }

    let lastOp = null;
    try {
      for (const op of transaction.crud) {
        lastOp = op;

        switch (op.op) {
          case UpdateType.PUT: {
            // Creation locale : op.id est le uuid client (cle primaire
            // locale), envoye au backend qui le persiste dans la colonne
            // uuid de Postgres (Tache 1).
            await AppointmentGateway.createAppointment({
              patientId: op.opData.patient_id,
              specialty: op.opData.specialty,
              appointmentDate: op.opData.appointment_date,
              appointmentTime: op.opData.appointment_time,
              reason: op.opData.reason,
              uuid: op.id,
            });
            break;
          }
          case UpdateType.PATCH: {
            // Modification : necessite l'id serveur (server_id), pas le
            // uuid local. Si server_id est encore absent (ligne creee
            // hors ligne, jamais confirmee), cette PATCH ne peut pas
            // encore etre appliquee individuellement - PowerSync a deja
            // coalesce les operations sur la meme ligne dans la plupart
            // des cas, mais si ce n'est pas le cas ici, abandonner cette
            // PATCH isolee plutot que d'appeler un endpoint avec un id
            // invalide (voir limite documentee dans la spec, section 3).
            const current = await database.get(
              'SELECT server_id FROM appointments WHERE id = ?',
              [op.id]
            );
            if (!current?.server_id) {
              console.warn(`RDV ${op.id} : modification hors ligne d'une creation pas encore confirmee, ignoree pour cet upload (sera reprise via le prochain PUT).`);
              break;
            }
            await AppointmentGateway.updateAppointment(current.server_id, {
              patientId: op.opData.patient_id,
              specialty: op.opData.specialty,
              appointmentDate: op.opData.appointment_date,
              appointmentTime: op.opData.appointment_time,
              reason: op.opData.reason,
            });
            break;
          }
          case UpdateType.DELETE: {
            // Hors perimetre de ce pilote (voir Contraintes globales) -
            // ne devrait jamais etre en file puisque rien cote UI ne
            // supprime materiellement un RDV. Log defensif seulement.
            console.warn(`Suppression RDV ${op.id} recue par le connecteur mais hors perimetre de ce pilote - ignoree.`);
            break;
          }
        }
      }

      await transaction.complete();
    } catch (error) {
      console.error('Erreur upload PowerSync:', lastOp, error);
      if (isFatalUploadError(error)) {
        console.error(`Operation ${lastOp?.op} sur ${lastOp?.id} abandonnee (erreur non recuperable) - retiree de la file.`);
        await transaction.complete();
      } else {
        // Erreur reseau/serveur transitoire - ne pas completer la
        // transaction, PowerSync retentera plus tard.
        throw error;
      }
    }
  }
}
```

- [ ] **Étape 3 : Ajouter `uuid` au payload de `AppointmentGateway.createAppointment()`**

Dans `ah2-admin-web/src/services/AppointmentGateway.js`, la méthode `createAppointment()` (actuellement lignes 33-42) ne transmet pas de `uuid` — c'est le seul changement nécessaire dans ce fichier pour ce plan, le reste (`fetchAppointments`, `updateAppointment`, `cancelAppointment`, `completeAppointment`, `getSpecialties`) reste inchangé et continue de servir le chemin en ligne direct pour tout code qui ne passe pas par le connecteur :

```js
    async createAppointment(data) {
        const payload = {
            patient_id: data.patientId,
            specialty: data.specialty || null,
            appointment_date: data.appointmentDate,
            appointment_time: data.appointmentTime,
            reason: data.reason || '',
            uuid: data.uuid || null,
        };
        return api.post('/appointments/', payload);
    },
```

- [ ] **Étape 4 : Écrire `client.js`**

```js
import { PowerSyncDatabase } from '@powersync/web';
import { AppSchema } from './AppSchema';
import { AppointmentConnector } from './AppointmentConnector';

export const db = new PowerSyncDatabase({
  schema: AppSchema,
  database: {
    dbFilename: 'ah2-powersync.db',
  },
});

let connected = false;

// role : 'medecin' | 'nurse' - determine quel stream RDV souscrire (voir
// sync-config.yaml, Tache 2). Ne jamais souscrire aux deux streams RDV
// pour un meme utilisateur - un medecin recevrait alors aussi la portee
// large de all_appointments, annulant la restriction voulue.
export async function connectPowerSync(role) {
  if (connected) {
    return;
  }
  const connector = new AppointmentConnector();
  await db.connect(connector);

  if (role === 'medecin') {
    await db.syncStream('my_appointments').subscribe();
  } else if (role === 'nurse') {
    await db.syncStream('all_appointments').subscribe();
  }
  await db.syncStream('patients_lookup').subscribe();
  await db.syncStream('doctors_lookup').subscribe();

  connected = true;
}

export async function disconnectPowerSync() {
  if (!connected) {
    return;
  }
  await db.disconnect();
  connected = false;
}
```

- [ ] **Étape 5 : Vérification**

`cd ah2-admin-web && npm run build` doit réussir sans erreur. Pas encore de vue branchée sur ce module (Tâches 5-6) — vérifier seulement l'absence d'erreur de compilation/import.

---

## Tâche 5 : Brancher le cycle de vie PowerSync sur l'authentification

**Fichiers :**
- Modifier : `ah2-admin-web/src/stores/auth.js`
- Modifier : `ah2-admin-web/src/App.vue`

**Interfaces :**
- Consomme : `connectPowerSync(role)`/`disconnectPowerSync()` (Tâche 4).

- [ ] **Étape 1 : Connecter/déconnecter sur login/logout**

Dans `ah2-admin-web/src/stores/auth.js`, ajouter l'import en tête de fichier :

```js
import { connectPowerSync, disconnectPowerSync } from '@/powersync-client/client';
```

Dans l'action `login()` (actuellement lignes 36-69), juste avant le `return true;` final :

```js
        localStorage.setItem('user', JSON.stringify(this.user));

        const role = this.user.application_role?.role_name;
        await connectPowerSync(role);

        return true;
```

Dans l'action `logout()` (actuellement lignes 71-90), juste après le commentaire `// 0. Revoquer le token cote serveur...` et son bloc try/catch, avant `// 1. Nettoyer l'état Pinia` :

```js
      // 0.5 Deconnecter PowerSync avant de nettoyer l'etat (best-effort,
      //     comme la revocation serveur - ne doit jamais bloquer le logout)
      try {
        await disconnectPowerSync();
      } catch (error) {
        console.warn("Echec de la deconnexion PowerSync :", error);
      }
```

- [ ] **Étape 2 : Reconnecter automatiquement au chargement si déjà authentifié**

Dans `ah2-admin-web/src/App.vue`, remplacer le contenu :

```vue
<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { connectPowerSync } from '@/powersync-client/client';

onMounted(async () => {
  const authStore = useAuthStore();
  if (authStore.isAuthenticated) {
    const role = authStore.userRole;
    if (role === 'medecin' || role === 'nurse') {
      await connectPowerSync(role);
    }
  }
});
</script>

<style scoped>
/* Laissez vide ou retirez cette section si elle est vide pour ne pas interférer avec Tailwind */
</style>
```

**Note pour l'exécutant :** ce hook couvre le cas "rechargement de page avec un token déjà en `localStorage`". Il ne connecte PowerSync que pour `medecin`/`nurse` (les seuls rôles couverts par ce pilote) — les autres rôles ne doivent pas tenter de se connecter à un service qui n'a pas de stream prévu pour eux.

- [ ] **Étape 3 : Vérification**

`cd ah2-admin-web && npm run build`. Test manuel : se connecter avec un compte `medecin` existant, ouvrir la console navigateur, confirmer l'absence d'erreur JS liée à PowerSync (des logs `[PowerSync]`/info sont normaux). Se déconnecter, confirmer l'absence d'erreur pendant la déconnexion.

---

## Tâche 6 : Rebrancher Rendez-vous (store + liste + modale) sur la base locale PowerSync

**Fichiers :**
- Modifier : `ah2-admin-web/src/stores/appointmentStore.js`
- Modifier : `ah2-admin-web/src/views/modules/appointments/AppointmentsList.vue`
- Modifier : `ah2-admin-web/src/components/appointments/AppointmentModal.vue`

**Interfaces :**
- Consomme : `db` (`@/powersync-client/client`), `AppointmentGateway.getSpecialties()`/`cancelAppointment()`/`completeAppointment()` (actions ponctuelles qui restent des appels REST directs, pas des écritures locales — voir note ci-dessous).
- Change de forme des objets `appointments.value` : avant, chaque RDV avait des sous-objets `.patient`/`.doctor` (réponse REST enrichie) ; après cette tâche, la ligne est un objet plat issu de la jointure SQL locale (`.code_patient`, `.first_name`, `.last_name`, `.contact_phone`, `.full_name` directement sur l'objet RDV, pas nichés). `AppointmentsList.vue`/`AppointmentModal.vue` doivent être adaptés à cette forme, pas seulement le store.

**Décision de portée pour cette tâche :** `fetchAppointments`/`createAppointment`/`updateAppointment` passent par la base locale PowerSync (lecture réactive + écriture locale mise en file). `fetchSpecialties`, `cancelAppointment`, `completeAppointment` **restent des appels REST directs inchangés** (via `AppointmentGateway`) — ce ne sont pas des tables synchronisées par PowerSync (les spécialités ne sont pas dans `sync-config.yaml`), et annulation/complétion sont des actions serveur ponctuelles hors périmètre de la file CRUD locale pour ce pilote (la spec ne les couvre pas comme "écriture hors ligne" à proprement parler — elles resteront simplement indisponibles hors ligne, ce qui est acceptable pour ce pilote et documenté ici plutôt que silencieusement laissé de côté).

- [ ] **Étape 1 : Remplacer `fetchAppointments` par une requête réactive locale**

Remplacer le contenu de `ah2-admin-web/src/stores/appointmentStore.js` :

```js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { AppointmentGateway } from '@/services/AppointmentGateway';
import { db } from '@/powersync-client/client';

// Les 3 seuls statuts reellement produits par le backend, verifie de
// facon exhaustive (grep sur toutes les affectations de status dans
// tout le code appointments) - voir registre C4. Ne pas ajouter
// "confirmed"/"accepted" ici tant que ce ticket n'est pas tranche.
export const APPOINTMENT_STATUSES = ['pending', 'cancelled', 'completed'];

export const useAppointmentStore = defineStore('appointment', () => {

    // --- ÉTAT ---
    const appointments = ref([]);
    const specialties = ref([]);
    const isLoading = ref(false);

    const filters = ref({
        searchQuery: '',
        status: 'ALL', // 'ALL' | 'pending' | 'cancelled' | 'completed'
        dateMode: 'ALL', // 'ALL' | 'TODAY' | 'CUSTOM'
        customDate: '',
    });

    let watchAbortController = null;

    // --- ACTIONS ---

    // Requete reactive sur la base locale PowerSync (pas un appel REST) -
    // se met a jour automatiquement quand une synchronisation arrive ou
    // qu'une ecriture locale est faite (createAppointment/updateAppointment
    // ci-dessous), sans jamais rappeler cette fonction manuellement.
    function startWatchingAppointments() {
        if (watchAbortController) {
            watchAbortController.abort();
        }
        watchAbortController = new AbortController();

        isLoading.value = true;
        (async () => {
            try {
                for await (const result of db.watch(
                    `SELECT a.*, p.first_name, p.last_name, p.code_patient, p.contact_phone,
                            d.full_name AS doctor_full_name, d.username AS doctor_username
                     FROM appointments a
                     LEFT JOIN patients_lookup p ON p.patient_id = a.patient_id
                     LEFT JOIN doctors_lookup d ON d.user_id = a.doctor_id
                     ORDER BY a.appointment_date DESC, a.appointment_time DESC`,
                    [],
                    { signal: watchAbortController.signal }
                )) {
                    let items = result.rows?._array ?? [];

                    // Filtres appliques cote client sur le jeu de donnees
                    // local complet (deja tout synchronise pour ce role,
                    // pas de pagination serveur ici contrairement au
                    // chemin REST direct des autres modules).
                    if (filters.value.status !== 'ALL') {
                        items = items.filter((a) => a.status === filters.value.status);
                    }
                    if (filters.value.dateMode === 'TODAY') {
                        const today = new Date().toISOString().split('T')[0];
                        items = items.filter((a) => a.appointment_date === today);
                    } else if (filters.value.dateMode === 'CUSTOM' && filters.value.customDate) {
                        items = items.filter((a) => a.appointment_date === filters.value.customDate);
                    }
                    if (filters.value.searchQuery) {
                        const q = filters.value.searchQuery.toLowerCase();
                        items = items.filter((a) =>
                            (a.first_name || '').toLowerCase().includes(q) ||
                            (a.last_name || '').toLowerCase().includes(q) ||
                            (a.code_patient || '').toLowerCase().includes(q)
                        );
                    }

                    appointments.value = items;
                    isLoading.value = false;
                }
            } catch (err) {
                if (err?.name !== 'AbortError') {
                    console.error('Erreur watch RDV PowerSync:', err);
                }
                isLoading.value = false;
            }
        })();
    }

    async function fetchSpecialties() {
        try {
            const res = await AppointmentGateway.getSpecialties();
            specialties.value = res.data || [];
        } catch (err) {
            console.error('Erreur chargement spécialités:', err);
            specialties.value = [];
        }
    }

    // Ecriture locale (pas d'appel REST direct) - PowerSync met l'INSERT
    // en file et appelle AppointmentConnector.uploadData() en arriere-plan,
    // en ligne comme hors ligne. crypto.randomUUID() genere le uuid client,
    // qui devient la cle primaire locale ET la colonne uuid Postgres une
    // fois synchronise (voir Contraintes globales du plan).
    async function createAppointment(data) {
        const uuid = crypto.randomUUID();
        await db.execute(
            `INSERT INTO appointments (id, patient_id, specialty, appointment_date, appointment_time, reason, status)
             VALUES (?, ?, ?, ?, ?, ?, 'pending')`,
            [uuid, data.patientId, data.specialty || null, data.appointmentDate, data.appointmentTime, data.reason || '']
        );
    }

    async function updateAppointment(localId, data) {
        await db.execute(
            `UPDATE appointments
             SET patient_id = ?, specialty = ?, appointment_date = ?, appointment_time = ?, reason = ?
             WHERE id = ?`,
            [data.patientId, data.specialty || null, data.appointmentDate, data.appointmentTime, data.reason || '', localId]
        );
    }

    async function cancelAppointment(appointmentId) {
        await AppointmentGateway.cancelAppointment(appointmentId);
    }

    async function completeAppointment(appointmentId) {
        await AppointmentGateway.completeAppointment(appointmentId);
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters };
    }

    return {
        appointments,
        specialties,
        isLoading,
        filters,
        startWatchingAppointments,
        fetchSpecialties,
        createAppointment,
        updateAppointment,
        cancelAppointment,
        completeAppointment,
        setFilters,
    };
});
```

**Notes pour l'exécutant :**
- `cancelAppointment`/`completeAppointment` ne rafraîchissent plus explicitement la liste après l'appel (contrairement à l'ancien `await fetchAppointments()` en fin de fonction) — ce n'est plus nécessaire : la modification du `status` en base par le backend sera répliquée par PowerSync et la boucle `for await` de `startWatchingAppointments()` la reflétera automatiquement dès la prochaine synchronisation descendante. Documenter dans le rapport de tâche si un délai perceptible est observé pendant les tests manuels (Tâche 7).
- `updateAppointment(localId, data)` prend l'`id` **local** (le uuid, colonne `id` de la table PowerSync), pas l'`id` serveur — cohérent avec les Étapes 2-3 ci-dessous, qui passent déjà `appt.id` (désormais le uuid local) sans changement à ce niveau-là.

- [ ] **Étape 2 : Adapter `AppointmentsList.vue`**

Remplacer le contenu de `ah2-admin-web/src/views/modules/appointments/AppointmentsList.vue` :

```vue
<template>
  <div class="space-y-6 w-full">

    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('appointments.title') }}
        </h1>
        <p class="text-sm text-gray-500">{{ t('appointments.subtitle') }}</p>
      </div>

      <button
        @click="openCreateModal"
        class="flex items-center px-6 py-2.5 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 shadow-md shadow-emerald-200 transition font-semibold"
      >
        <PlusCircleIcon class="h-5 w-5 mr-2" />
        {{ t('appointments.new_appointment') }}
      </button>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-wrap gap-4 items-end">

      <div class="flex-1 min-w-[220px]">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('appointments.search_label') }}</label>
        <div class="relative">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
          </div>
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('appointments.search_placeholder')"
            class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
          >
        </div>
      </div>

      <div class="w-full md:w-48">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('appointments.status_label') }}</label>
        <select v-model="statusFilter" class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm rounded-lg">
          <option value="ALL">{{ t('appointments.status_all') }}</option>
          <option v-for="s in appointmentStatuses" :key="s" :value="s">{{ t(`appointments.status_${s}`) }}</option>
        </select>
      </div>

      <div class="w-full md:w-44">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('appointments.date_label') }}</label>
        <select v-model="dateMode" class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm rounded-lg">
          <option value="ALL">{{ t('appointments.date_all') }}</option>
          <option value="TODAY">{{ t('appointments.date_today') }}</option>
          <option value="CUSTOM">{{ t('appointments.date_custom') }}</option>
        </select>
      </div>

      <div v-if="dateMode === 'CUSTOM'" class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('appointments.date_custom') }}</label>
        <input v-model="customDate" type="date" class="block w-full pl-3 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm" />
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

      <div class="p-4 border-b border-gray-100 flex items-center justify-between">
        <div class="text-sm text-gray-500">
          {{ appointmentStore.appointments.length }} {{ t('appointments.results_count') }}
        </div>
      </div>

      <div v-if="appointmentStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></span>
        <p class="mt-2 text-gray-500">{{ t('common.loading') }}</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.patient') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.phone') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.doctor') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.time') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.reason') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('appointments.table.status') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('appointments.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="appt in appointmentStore.appointments" :key="appt.id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4">
                <div class="text-sm font-medium text-gray-900">{{ patientName(appt) }}</div>
                <div class="text-xs text-gray-500">{{ appt.code_patient }}</div>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ appt.contact_phone || '—' }}</td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ appt.doctor_full_name || appt.doctor_username || '—' }}</td>
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ appt.appointment_date }}</td>
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ (appt.appointment_time || '').substring(0, 5) }}</td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ appt.reason || '—' }}</td>
              <td class="px-6 py-4">
                <StatusBadge :status="appt.status" />
              </td>
              <td class="px-6 py-4 text-right">
                <div class="flex justify-end gap-2">
                  <!--
                    Bouton "Accepter" volontairement omis (contrairement au
                    client desktop) - voir docs/superpowers/SUIVI-AVANCEMENT.md,
                    registre C4. Non touché par ce chantier.
                  -->
                  <button
                    v-if="appt.status === 'pending'"
                    @click="appointmentStore.completeAppointment(appt.server_id)"
                    :disabled="!appt.server_id"
                    :title="!appt.server_id ? t('appointments.pending_sync') : ''"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {{ t('appointments.actions.complete') }}
                  </button>
                  <button
                    v-if="appt.status === 'pending'"
                    @click="appointmentStore.cancelAppointment(appt.server_id)"
                    :disabled="!appt.server_id"
                    :title="!appt.server_id ? t('appointments.pending_sync') : ''"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {{ t('appointments.actions.cancel') }}
                  </button>
                  <button
                    @click="openEditModal(appt)"
                    class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition"
                  >
                    {{ t('appointments.actions.edit') }}
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="appointmentStore.appointments.length === 0">
              <td colspan="8" class="px-6 py-8 text-center text-gray-500 italic">
                {{ t('appointments.empty') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>

    <AppointmentModal
      v-if="showModal"
      :appointment="editingAppointment"
      @close="closeModal"
      @save="handleSave"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAppointmentStore, APPOINTMENT_STATUSES } from '@/stores/appointmentStore';
import { useI18n } from 'vue-i18n';
import StatusBadge from '@/components/appointments/StatusBadge.vue';
import AppointmentModal from '@/components/appointments/AppointmentModal.vue';
import {
  PlusCircleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const appointmentStore = useAppointmentStore();
const appointmentStatuses = APPOINTMENT_STATUSES;

onMounted(() => {
  appointmentStore.startWatchingAppointments();
  appointmentStore.fetchSpecialties();
});

const searchQuery = computed({
  get: () => appointmentStore.filters.searchQuery,
  set: (val) => appointmentStore.setFilters({ searchQuery: val }),
});

const statusFilter = computed({
  get: () => appointmentStore.filters.status,
  set: (val) => appointmentStore.setFilters({ status: val }),
});

const dateMode = computed({
  get: () => appointmentStore.filters.dateMode,
  set: (val) => appointmentStore.setFilters({ dateMode: val }),
});

const customDate = computed({
  get: () => appointmentStore.filters.customDate,
  set: (val) => appointmentStore.setFilters({ customDate: val }),
});

function patientName(appt) {
  return [appt.first_name, appt.last_name].filter(Boolean).join(' ') || '—';
}

const showModal = ref(false);
const editingAppointment = ref(null);

function openCreateModal() {
  editingAppointment.value = null;
  showModal.value = true;
}

function openEditModal(appt) {
  editingAppointment.value = appt;
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  editingAppointment.value = null;
}

async function handleSave(data) {
  try {
    if (editingAppointment.value) {
      await appointmentStore.updateAppointment(editingAppointment.value.id, data);
    } else {
      await appointmentStore.createAppointment(data);
    }
    closeModal();
  } catch (err) {
    console.error('Erreur enregistrement rendez-vous:', err);
    alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
  }
}
</script>
```

**Changements par rapport à l'existant, à bien noter :**
- La pagination serveur (`goToPage`, `ChevronLeftIcon`/`ChevronRightIcon`, le bloc `<div v-if="appointmentStore.pagination.total_pages > 1">`) est entièrement retirée — tout le jeu de données du rôle connecté est désormais local (pas de pagination réseau à paginer). Si le volume réel s'avère trop important pour un rendu sans pagination, ce sera une itération future, pas un oubli de cette tâche (déjà noté comme limite acceptée dans la spec, section 2, à propos de la volumétrie patients — le même raisonnement s'applique ici).
- `doctorName(appt)` (fonction) est retirée, remplacée par l'expression inline `appt.doctor_full_name || appt.doctor_username || '—'` — la jointure locale (Tâche 6, Étape 1) fournit déjà ces deux champs plats.
- `appt.patient?.code_patient` etc. deviennent `appt.code_patient` etc. (objet plat, plus de sous-objet `.patient`/`.doctor` — voir Interfaces en tête de cette tâche).
- Les boutons "Compléter"/"Refuser" appellent `appt.server_id` (pas `appt.id`, qui est maintenant le uuid local) et sont désactivés (`:disabled="!appt.server_id"`) tant qu'un RDV créé hors ligne n'a pas encore été confirmé par le serveur — appeler `POST /appointments/{id}/cancel` avec un uuid à la place d'un entier échouerait. Ajouter la clé i18n `appointments.pending_sync` (fr : "En attente de synchronisation", en : "Awaiting sync") dans `ah2-admin-web/src/i18n.js`, bloc `appointments.*` existant (fr et en).

- [ ] **Étape 3 : Adapter `AppointmentModal.vue`**

Remplacer le contenu de `ah2-admin-web/src/components/appointments/AppointmentModal.vue` :

```vue
<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
    <div class="relative mx-auto p-6 border w-full max-w-md shadow-xl rounded-2xl bg-white">

      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold text-gray-900">
          {{ isEdit ? t('appointments.modal.title_edit') : t('appointments.modal.title_new') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-5">

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.patient_code') }}</label>
          <input
            v-model="patientCode"
            @blur="lookupPatient"
            type="text"
            required
            :readonly="isEdit"
            placeholder="Ex: AH2-000818AQ"
            :class="[
              'block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm',
              isEdit ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : ''
            ]"
          />
          <p class="mt-1 text-xs" :class="patientId ? 'text-emerald-600' : 'text-gray-400'">
            {{ patientLookupMessage }}
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.specialty') }}</label>
          <select v-model="form.specialty" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm">
            <option value="">{{ t('appointments.modal.specialty_none') }}</option>
            <option v-for="spec in appointmentStore.specialties" :key="spec" :value="spec">{{ spec }}</option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.date') }}</label>
            <input
              v-model="form.appointmentDate"
              type="date"
              required
              class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.time') }}</label>
            <select v-model="form.appointmentTime" required class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm">
              <option value="" disabled>--:--</option>
              <option v-for="slot in timeSlots" :key="slot" :value="slot">{{ slot }}</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('appointments.modal.reason') }}</label>
          <textarea
            v-model="form.reason"
            rows="2"
            placeholder="Ex: Consultation de suivi..."
            class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
          ></textarea>
        </div>

        <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-100">
          <button type="button" @click="$emit('close')" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition shadow-sm">
            {{ t('appointments.modal.cancel') }}
          </button>
          <button type="submit" class="px-4 py-2 text-white rounded-lg shadow-md font-medium transition bg-emerald-600 hover:bg-emerald-700">
            {{ t('appointments.modal.save') }}
          </button>
        </div>
      </form>

    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAppointmentStore } from '@/stores/appointmentStore';
import { db } from '@/powersync-client/client';

const { t } = useI18n();
const appointmentStore = useAppointmentStore();
const emit = defineEmits(['close', 'save']);

const props = defineProps({
  appointment: {
    type: Object,
    default: null,
  },
});

const isEdit = computed(() => !!props.appointment);

const patientCode = ref('');
const patientId = ref(null);
const patientName = ref('');
const patientLookupMessage = ref('');

const form = reactive({
  specialty: '',
  appointmentDate: '',
  appointmentTime: '',
  reason: '',
});

// Creneaux de 30 min, 08:00-18:30 - port exact de book_appoint_view.py
// (f"{h:02d}:{m:02d}" for h in range(8, 19) for m in (0, 30))
const timeSlots = computed(() => {
  const slots = [];
  for (let h = 8; h <= 18; h++) {
    for (const m of [0, 30]) {
      slots.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
    }
  }
  return slots;
});

// Recherche patient sur la base locale PowerSync (patients_lookup) au lieu
// d'un appel REST direct - fonctionne desormais aussi hors ligne, ce qui
// est le but meme de ce pilote (creer un RDV sans reseau implique de
// pouvoir retrouver le patient sans reseau non plus).
async function lookupPatient() {
  const raw = patientCode.value.trim();
  if (!raw) {
    patientId.value = null;
    patientName.value = '';
    patientLookupMessage.value = '';
    return;
  }

  let code = raw.toUpperCase();
  if (!code.startsWith('AH2-')) {
    code = `AH2-${code}`;
  }
  patientCode.value = code;

  try {
    const match = await db.get(
      'SELECT patient_id, first_name, last_name FROM patients_lookup WHERE code_patient = ?',
      [code]
    );
    if (!match) {
      patientId.value = null;
      patientName.value = '';
      patientLookupMessage.value = t('appointments.modal.patient_not_found');
      return;
    }
    patientId.value = match.patient_id;
    patientName.value = [match.first_name, match.last_name].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
  } catch (err) {
    console.error('Erreur recherche patient (locale):', err);
    patientId.value = null;
    patientName.value = '';
    patientLookupMessage.value = t('appointments.modal.patient_not_found');
  }
}

onMounted(() => {
  if (props.appointment) {
    const appt = props.appointment;
    patientId.value = appt.patient_id || null;
    patientCode.value = appt.code_patient || '';
    patientName.value = [appt.first_name, appt.last_name].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
    form.specialty = appt.specialty || '';
    form.appointmentDate = (appt.appointment_date || '').substring(0, 10);
    form.appointmentTime = (appt.appointment_time || '').substring(0, 5);
    form.reason = appt.reason || '';
  }
});

async function handleSubmit() {
  if (!patientId.value && patientCode.value.trim()) {
    await lookupPatient();
  }

  if (!patientId.value) {
    alert(t('appointments.modal.patient_not_found'));
    return;
  }

  emit('save', {
    patientId: patientId.value,
    specialty: form.specialty,
    appointmentDate: form.appointmentDate,
    appointmentTime: form.appointmentTime,
    reason: form.reason,
  });
}
</script>
```

**Changements par rapport à l'existant, à bien noter :**
- `lookupPatient()` interroge désormais `db.get(...)` (base locale PowerSync, table `patients_lookup`) au lieu de `api.get('/patients/', ...)` — l'import `api` (`@/services/api`) n'est plus utilisé dans ce fichier, retiré des imports.
- Le champ "Code Patient" devient `:readonly="isEdit"` — même convention déjà établie dans `MedicalRecordModal.vue`/`ConsultationModal.vue` (chantier 3) pour ne pas permettre de changer le patient d'un RDV existant après création.
- En édition (`onMounted`), les champs viennent maintenant de l'objet plat (`appt.code_patient`, `appt.first_name`, `appt.last_name`, `appt.patient_id`) fourni par la jointure locale du store, pas de sous-objets `appt.patient.*`.
- La variable `pendingLookup` (promesse de recherche en cours, utilisée dans l'ancien `handleSubmit` pour attendre une recherche déjà lancée par le `@blur`) est retirée : `db.get()` étant une requête locale quasi instantanée (pas un appel réseau), il n'y a plus de scénario réaliste de "recherche encore en cours" à gérer à la soumission — simplification volontaire, pas un oubli.

- [ ] **Étape 4 : Vérification**

`cd ah2-admin-web && npm run build` doit réussir. La vérification fonctionnelle complète (avec la base locale réellement peuplée) arrive à la Tâche 7.

---

## Tâche 7 : Vérification manuelle de bout en bout

Pas de nouveau fichier — cette tâche exécute la section "Vérification" de la spec, avec un compte réel.

- [ ] **Étape 1 : Build et démarrage**

```bash
cd ah2-admin-web && npm run build && npm run preview
```

(`npm run preview` sert le build de production, nécessaire pour tester le service worker/PWA — `npm run dev` ne l'active pas de la même façon.)

- [ ] **Étape 2 : Scoping par rôle**

Se connecter avec un compte `medecin` A, créer un RDV, confirmer qu'il apparaît dans la liste. Se connecter avec un compte `medecin` B différent, confirmer que le RDV du médecin A **n'apparaît pas**. Se connecter avec un compte `nurse`, confirmer que les RDV des deux médecins **apparaissent tous les deux**.

- [ ] **Étape 3 : Cycle hors ligne complet**

Avec un compte `medecin` connecté et déjà synchronisé une première fois : couper le réseau (DevTools → Network → Offline, ou arrêter `docker stop powersync-powersync-1`). Créer un RDV, modifier son statut si l'UI le permet. Reconnecter le réseau (`docker start powersync-powersync-1` si arrêté). Confirmer dans les logs (`docker logs powersync-powersync-1 --tail 20`) qu'aucune erreur de upload n'apparaît, et vérifier côté Postgres (`psql` sur `AH2`, `SELECT * FROM appointments WHERE uuid = '<uuid genere>'`) que la ligne existe avec le bon `doctor_id`.

- [ ] **Étape 4 : Installabilité PWA**

Dans Chrome/Edge, ouvrir l'app servie par `npm run preview`, confirmer que l'icône d'installation apparaît dans la barre d'adresse, installer l'app, confirmer qu'elle s'ouvre dans sa propre fenêtre.

- [ ] **Étape 5 : Non-régression**

Se connecter avec un compte `admin`/`ToxicoManager`/autre rôle non couvert par ce pilote, confirmer que `MainLayout.vue` et ses modules fonctionnent à l'identique (aucune tentative de connexion PowerSync, aucune erreur console liée).

## Auto-revue (à faire par le contrôleur avant de lancer la Tâche 1)

- **Couverture de la spec :** les 5 sections de la spec (identité des lignes, règles de sync, écriture, auth, PWA) correspondent chacune à une ou plusieurs tâches (1-2 / 2 / 4 / 1+2 / 3). Vérification de bout en bout couverte par la Tâche 7.
- **Cohérence des identifiants :** `uuid` (Postgres) = `id` (local PowerSync) rappelé et appliqué de façon cohérente dans les Tâches 1, 2, 4 et 6 — jamais confondu avec `server_id`/l'entier Postgres.
- **Point d'incertitude assumé, pas un trou du plan :** le cast `request.user_id()`/type de `doctor_id` (Tâche 2) et la nécessité réelle du `kid` (déjà réglée en Tâche 1 de façon déterministe, sans attendre une vérification empirique) sont les deux seuls points où le plan reconnaît explicitement ne pas garantir le résultat à 100% avant exécution réelle — documentés avec une action de repli concrète, pas laissés vagues.
