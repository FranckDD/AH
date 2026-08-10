# Chantier 0 — Remise en service + P0 sécurité

**Date :** 2026-08-10
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** audit `docs/superpowers/specs/../audit-ah2` (rapport artifact du 2026-08-10)

## Contexte

Reprise du projet AH2/Glostone-Kare après 8 mois d'inactivité. Un audit complet a identifié 25 constats répartis en priorités P0/P1/P2. Ce chantier couvre exclusivement les correctifs P0 bloquants pour toute reprise saine — sécurité d'exposition et deux bugs front bloquants — sans toucher à l'architecture des rôles ni au portage web, qui font l'objet de chantiers séparés.

Contrainte déterminante : le dépôt `github.com/FranckDD/AH` est **public**. `JWT_SECRET` et le mot de passe PostgreSQL actuels doivent être traités comme compromis dès aujourd'hui, indépendamment de la purge d'historique.

## Périmètre

Ajustement par rapport au découpage initial de l'audit : `SEC-06` (repli permissif du système de rôles) **sort** de ce chantier. Il ne peut pas être corrigé isolément sans l'unification des rôles (chantier 1) — le traiter ici ne ferait que déplacer le bug plutôt que le résoudre.

Inclus : `SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-07, SEC-08, SEC-10, WEB-01, WEB-02, WEB-03`.

Explicitement hors périmètre (avec justification) :
- `SEC-06` / `ARC-01` — dépend du chantier 1 (unification des rôles)
- `SEC-09` (cycle de vie JWT complet : refresh token, révocation, migration hors `localStorage`) — refactor plus large, chantier séparé à définir
- Verrouillage de compte persistant après échecs de connexion — nécessite une migration de schéma ; reporté au chantier 2 qui introduit Alembic, pour éviter une migration à la main qu'Alembic devrait ensuite absorber
- Installation d'un Redis natif pour Celery — prérequis d'infrastructure (installation d'un serveur), pas un correctif de code. Les tâches Celery restent des simulations tant qu'`OPS-04` (sort du worker) n'est pas tranché

## Décisions validées avec l'utilisateur

1. **Historique Git** : purge complète de `.env` de tout l'historique via `git filter-repo`, puis `git push --force` sur `origin`. Autorisé explicitement — dépôt à auteur unique, sauvegarde locale prise avant réécriture.
2. **`/config/structure`** : **GET et POST** protégés par `role_required("admin")` — décision explicite de l'utilisateur, revenant sur ma proposition initiale de laisser le GET public. **Conséquence assumée** : l'écran de connexion ne pourra plus récupérer le nom/logo de l'établissement avant authentification. Non traité dans ce chantier ; si un affichage de marque pré-connexion est souhaité plus tard, il faudra soit une route dédiée à données non sensibles, soit un contenu statique côté front.

## Détail des correctifs

### 1. Secrets et hygiène Git (SEC-01, SEC-10)

- Sauvegarde locale complète du dépôt avant toute réécriture d'historique (`git clone --mirror` vers un répertoire hors du repo de travail)
- Installer `git-filter-repo` (paquet pip)
- Purger `.env` (et toute autre occurrence de secret trouvée) de tout l'historique, toutes branches
- `git push --force` vers `origin` pour les 4 branches distantes : `AH2_V2`, `AH2_V3-1`, `dash_Ah2`, `master`
- `git rm -r --cached` (sans réécriture d'historique) pour : `offline.db`, `onehandhumanity.sqlite`, `auth.log`, les fichiers `.pyc` suivis, `view/`, `view_pyqt6/`, `build/`, `dist/`, `htmlcov/` — déjà couverts par `.gitignore` mais suivis depuis avant son ajout
- Rotation effective des secrets encore actifs :
  - Nouveau mot de passe PostgreSQL local via `ALTER USER postgres ...`. Un rôle applicatif dédié à moindre privilège serait préférable à terme, mais c'est un changement d'architecture d'accès (permissions à cartographier par table) hors périmètre de ce chantier — noté comme amélioration future, pas traité ici
  - Nouveau `JWT_SECRET`, généré via `secrets.token_urlsafe(48)`
  - Nouveau mot de passe pour le compte `admin_test` (rendu public par le `README.md`)
  - Mise à jour du `.env` local avec les nouvelles valeurs (fichier déjà correctement ignoré)

### 2. `/config` non authentifié (SEC-02)

- `router = APIRouter(prefix="/config", tags=[...], dependencies=[Depends(role_required("admin"))])` — protection au niveau du router, cohérente avec le pattern déjà utilisé sur `appointments`, `toxico`, etc.
- S'applique à `GET /config/structure` **et** `POST /config/structure`

### 3. Upload de logo (SEC-03)

- Nom de fichier régénéré côté serveur : `f"{uuid4().hex}.{ext}"` — le nom fourni par le client n'est plus jamais utilisé pour construire un chemin
- Liste blanche d'extensions : `.png`, `.jpg`, `.jpeg`, `.webp` (SVG explicitement exclu — vecteur de script embarqué)
- Revalidation du contenu comme image réelle via Pillow : `Image.open(buffer).verify()`, pas seulement l'extension ou le `Content-Type` déclaré
- Taille plafonnée à 5 Mo, vérifiée avant écriture sur disque

### 4. Identifiants en dur (SEC-04)

Suppression des replis `postgresql://postgres:Admin_2025@localhost/AH2` dans :
- `controller/auth_controller.py:41`
- `main.py:14`
- `controller/controller_offline/auth_controller_factory.py:29`
- `import_medical_specialities.py:15`
- `migrations/import_users_pg_to_sqlite.py:15`

Comportement aligné sur `api_backend/backend_app/config.py` : erreur explicite si `DATABASE_URL` est absent de l'environnement, plus aucune valeur par défaut silencieuse.

Ligne d'identifiants (`Admin123! admin_test`) retirée du `README.md`.

### 5. Force brute sur l'authentification (SEC-05)

- Ajout de `slowapi` aux dépendances (`requirements.txt`)
- Limitation appliquée à `POST /auth/login` : 5 tentatives / 5 minutes, par IP + nom d'utilisateur combinés
- Backend du limiteur : Redis natif (disponible sur la machine de dev — service `postgresql-x64-17` confirmé actif, Redis natif à confirmer/installer séparément lors de l'implémentation ; si absent au moment du plan, repli sur un limiteur en mémoire du process, moins robuste mais non bloquant)

### 6. Lecture de l'annuaire des comptes (SEC-07)

- `role_required("admin", "manager")` ajouté sur `GET /users/`, `GET /users/{id}`, `GET /users/search`
- `GET /users/doctors` reste ouvert au personnel soignant authentifié — besoin métier légitime, et `UserOut` ne fuit pas de donnée sensible (vérifié : pas de `password_hash` dans le schéma)

### 7. Fuite de payload dans les logs (SEC-08)

Dans le handler `RequestValidationError` de `main.py` : suppression de l'impression de `error['input']`. Conserve l'emplacement du champ (`loc`) et le message d'erreur (`msg`), retire la valeur reçue.

### 8. Front web (WEB-01, WEB-02, WEB-03)

- Renommage `forbidden.vue` → `Forbidden.vue`, cohérent avec la convention PascalCase déjà en usage (`LoginView.vue`, `MainLayout.vue`, etc.)
- `API_URL` centralisé : une seule définition dans `services/api.js`, lue depuis `import.meta.env.VITE_API_URL` (avec repli sur `http://localhost:8000` en développement). Ajout d'un `.env.example` dans `ah2-admin-web/`
- `stores/auth.js` : remplacement des appels `axios` bruts par l'instance `api` partagée exportée depuis `services/api.js` — corrige au passage `WEB-03` (contournement des intercepteurs de gestion des 401), cause racine commune avec `WEB-02`

## Vérification

Pas de suite de tests d'intégration existante à étendre pour ce chantier (le socle de test est l'objet du chantier 2). Vérification par constat manuel :

- Upload avec un nom de fichier contenant `../` → rejeté
- Upload d'un fichier renommé en `.png` mais n'étant pas une image → rejeté par Pillow
- `POST /config/structure` sans jeton → 401
- `GET /config/structure` sans jeton → 401
- `GET /users/` avec un compte non-admin → 403
- 6e tentative de connexion en échec sur la même combinaison IP/utilisateur en moins de 5 minutes → bloquée
- Le gestionnaire 422 n'imprime plus de valeurs de champs dans la console serveur
- `npm run build` réussit sans avertissement de résolution de module sur `Forbidden.vue`

Deux unités neuves et isolées reçoivent un test ciblé plutôt qu'une vérification manuelle uniquement :
- Le générateur de nom de fichier d'upload (extensions valides/invalides, absence de traversée de chemin)
- La configuration du limiteur de débit (seuil déclenché au bon nombre de tentatives)

## Risques et hypothèses

- La réécriture d'historique change les hachages de commit sur toutes les branches distantes. Si un clone existe ailleurs (autre poste, fork), il devra être resynchronisé manuellement — acceptable ici, auteur unique confirmé.
- La disponibilité d'un Redis natif pour `slowapi` sera confirmée au moment de l'implémentation ; un repli en mémoire est prévu si nécessaire, sans bloquer le chantier.
- Le blocage du GET `/config/structure` retire une fonctionnalité de marque pré-connexion qui pourrait exister côté front (à vérifier au moment de l'implémentation si l'écran de connexion tente déjà de l'afficher).
