# Suivi d'avancement — AH2 / Glostone-Kare

**Dernière mise à jour :** 2026-08-11 (chantier 2d-2)
**But de ce document :** état d'avancement des chantiers de remise en service et de sécurisation, et registre des découvertes faites en cours de route mais non encore traitées. Pour le contexte général du projet, voir `docs/superpowers/CONTEXTE-PROJET.md`. Pour le détail d'un chantier, voir les fichiers correspondants dans `docs/superpowers/specs/` et `docs/superpowers/plans/`.

## Feuille de route

Issue de l'audit initial du projet (2026-08-10), découpée en chantiers indépendants au fil de l'avancement.

| # | Chantier | Statut | Commits |
|---|---|---|---|
| 0 | Remise en service + sécurité P0 | ✅ Terminé | `e4f5413`..`03b1b87` |
| 1 | Unification des rôles (chemin web) | ✅ Terminé | `83a2205`..`b154115` |
| SEC-09 | Cycle de vie JWT + en-têtes de sécurité | ✅ Terminé | `e43ed17`..`86086cf` |
| 2a | Alembic + migration de référence | ✅ Terminé | `170e7cb`..`6bd8e85` |
| — | Nettoyage A1-A4 (fuseau JWT, trigger, tables non modélisées, CSP) | ✅ Terminé | `ce35863`..`1d9456c` |
| — | Correction affichage erreur de connexion (desktop) | ✅ Terminé | `76d64ad` |
| 2e | Piste d'audit non silencieuse | ✅ Terminé | `389cc1a`..`7eb1b15` |
| 2d-0 | Infrastructure de test d'intégration | ✅ Terminé | `beeb508`..`e37aa7b` |
| 2d-1 | Tests auth + RBAC | ✅ Terminé | `e71a70d`..`d75793d` |
| 2d-2 | Tests patients | ✅ Terminé | `6e7b11d`..`c6aa6b8` (+ `9baa02a` correctif procédure stockée) |
| 2d-3 | Tests prescriptions | ⬜ À faire | — |
| 2d-4 | Tests caisse | ⬜ À faire | — |
| 2b | CI (GitHub Actions) | ⬜ À faire | — |
| 2c | Split des dépendances (`requirements-api.txt`/`requirements-desktop.txt`) | ⛔ Bloqué — `requirements.txt` en plein travail en cours, sans base commune avec `HEAD` | — |
| 3 | Portage web (caisse/secrétariat, RDV, prescriptions, dossiers médicaux) | ⬜ Pas commencé | — |
| 4 | PowerSync + PWA (remplace le mode hors ligne maison) | ⬜ Pas commencé | — |
| 5 | Hébergement & exploitation (remplace Railway/Supabase, TLS, stockage objet) | ⬜ Pas commencé — peut démarrer en parallèle | — |

## Détail des chantiers terminés

### Chantier 0 — Remise en service + sécurité P0
Spec : `2026-08-10-chantier-0-remise-en-service-design.md` · Plan : `2026-08-10-chantier-0-remise-en-service.md`
Secrets rotés + historique Git purgé (`SEC-01`), `/config` protégé (`SEC-02`), upload assaini (`SEC-03`), identifiants en dur retirés (`SEC-04`), limitation de débit (`SEC-05`), lecture des comptes restreinte (`SEC-07`), logs de payloads retirés (`SEC-08`), casse `Forbidden.vue` + `API_URL` centralisé (`WEB-01/02/03`), fichiers indésirables retirés du suivi Git (`SEC-10`).

### Chantier 1 — Unification des rôles (chemin web)
Spec : `2026-08-10-chantier-1-unification-roles-design.md` · Plan : `2026-08-10-chantier-1-unification-roles.md`
`role_map.py` étendu de 5 à 9 rôles réels + `manager` réservé, repli permissif de `role_required()` retiré, code mort (`routes/core/permissions.py`) supprimé, comparaison de rôles front insensible à la casse (`WEB-04`), compte `secretaire1` corrigé.
**Découverte :** `SEC-06` (repli permissif de `get_current_user()`) était déjà fermé sur `HEAD` — le bug ne vivait que dans la copie de travail de l'utilisateur (voir Registre, item B1).

### SEC-09 — Cycle de vie JWT + en-têtes de sécurité
Spec : `2026-08-10-sec-09-cycle-de-vie-jwt-design.md` · Plan : `2026-08-10-sec-09-cycle-de-vie-jwt.md`
Révocation via `token_version` + `POST /auth/logout`, `jti`/`iss`/`aud`, en-têtes de sécurité HTTP, `IS_PROD` câblé.
**Découverte :** `python-jose` exige `audience=` dès qu'un token contient `aud`, sinon rejette tout token — corrigé avant que ça ne casse la prod.

### Chantier 2a — Alembic + migration de référence
Spec : `2026-08-10-chantier-2a-alembic-design.md` · Plan : `2026-08-10-chantier-2a-alembic.md`
Alembic initialisé, `models/__init__.py` étendu à 19 modèles réels, migration baseline générée et **stampée sans jamais être exécutée**.
**Découverte critique :** la migration `upgrade()` aurait supprimé 17 tables réelles et peuplées sans modèle SQLAlchemy (`admin`, `doctor`, `nurse`, `secretaire`, `laborantin`, `audit_logs`, etc.) — corrigée au chantier suivant (A3).

### Nettoyage A1-A4
Spec : `2026-08-11-nettoyage-a1-a4-design.md` · Plan : `2026-08-11-nettoyage-a1-a4.md`
A1 fuseau horaire JWT, A2 trigger `create_metier_profile()` idempotent (1ʳᵉ vraie migration Alembic exécutée), A3 exclusion des 17 tables non modélisées de l'autogénération, A4 CSP (calibré par analyse statique du bundle, faute d'outil de navigateur disponible).

### Correction affichage erreur de connexion (desktop)
Commit `76d64ad`. `AuthManager.login()` ne reconnaissait pas la clé `detail` de FastAPI, affichait systématiquement un message générique trompeur ("no token") quelle que soit la cause réelle d'un échec de connexion. Corrigé pendant le diagnostic d'un problème utilisateur (mot de passe périmé après rotation `SEC-04`).

### Chantier 2e — Piste d'audit non silencieuse
Spec : `2026-08-11-chantier-2e-audit-non-silencieux-design.md` · Plan : `2026-08-11-chantier-2e-audit-non-silencieux.md`
11 sites sur 6 contrôleurs : `except Exception: pass` → `logger.exception(...)`, comportement non-bloquant préservé, échecs désormais visibles.

### Chantier 2d-0 — Infrastructure de test d'intégration
Spec : `2026-08-11-chantier-2d0-infrastructure-tests-design.md` · Plan : `2026-08-11-chantier-2d0-infrastructure-tests.md`
Fondation des sous-chantiers 2d-1 à 2d-4. Fixture `db_session` (`tests/conftest.py`) : transaction externe + SAVEPOINT auto-relancée, permet aux tests d'utiliser la vraie base `AH2` locale sans laisser de donnée résiduelle, même quand le code testé fait des `commit()` internes. Helper `override_get_db()` pour brancher cette session dans les dépendances FastAPI (14 `get_db()` distincts, un par module de routes — `ARC-05`).
**Décision utilisateur** : base `AH2` réelle plutôt qu'une base `AH2_test` dédiée — les données actuelles sont des données de test.
**Vérification** : pattern testé manuellement contre la base réelle pendant le cadrage, puis via un méta-test pytest committé, puis via un test de bout en bout (`TestClient` + route `/health` réelle). Confirmé sans fuite de donnée à chaque étape.

### Chantier 2d-1 — Tests d'intégration auth + RBAC
Spec : `2026-08-11-chantier-2d1-tests-auth-rbac-design.md` · Plan : `2026-08-11-chantier-2d1-tests-auth-rbac.md`
Premier sous-chantier métier construit sur 2d-0. Exécuté via subagent-driven-development, dans un worktree isolé (`.claude/worktrees/chantier-2d1-tests-auth-rbac`) pour ne jamais toucher au travail en cours de l'utilisateur. 11 tests neufs sur 3 fichiers :
- `tests/test_auth_login.py` — `POST /auth/login` : succès (rôle correctement encodé dans le JWT), mauvais mot de passe, compte inactif, utilisateur inconnu (mêmes 401 génériques "Identifiants invalides", comportement existant).
- `tests/test_auth_token_lifecycle.py` — `GET /auth/me`/`POST /auth/logout` : token valide, token expiré (forgé), signature invalide (forgée), et révocation effective via `token_version` (login → logout → réutilisation de l'ancien token → 401).
- `tests/test_rbac.py` — `role_required()` sur `GET /users/` (route réelle durcie au chantier 0, `SEC-07`) : rôle admin autorisé, rôle secretaire refusé (403), non authentifié (401).

Ajout à `tests/conftest.py` (infrastructure partagée, réutilisable par 2d-2 à 2d-4) : `create_test_user()` (compte éphémère, `flush()` jamais `commit()`) et une fixture `autouse` réinitialisant le rate limiter entre tests (`/auth/login` limité à 5/minute, `SEC-05` — sans cela `TestClient` se bloquerait lui-même).

**Découvertes pendant le cadrage/l'implémentation :**
- La spec initiale ciblait `GET /admin/users/` pour le test RBAC — corrigé en `GET /users/` avant l'écriture du plan (`users_endpoint.py` a `prefix="/users"`, aucun préfixe `/admin` n'est ajouté dans `main.py`).
- `GET /users/` nécessite un double `override_get_db()` (module `auth_endpoints` + module `users_endpoint`, chacun avec son propre `get_db()`) — confirmation concrète du besoin `ARC-05`.
- Les 4 échecs de tests pré-existants notés au chantier 2d-0 ne sont plus que 2 (`test_patient_repo.py::test_update_patient_success`, `test_update_patient_not_found`) — `test_prescription_repo.py` passe désormais, sans lien avec ce chantier.

**Revue finale de branche** (subagent-driven-development, worktree isolé) : 3 findings « Important » (boilerplate dupliqué entre les 3 fichiers de test, `test_admin_role_can_list_users` couplé au volume réel de la table `users`, absence de garde-fou sur la base ciblée par `db_session`) + 1 minor (constantes `JWT_ISSUER`/`JWT_AUDIENCE` redéfinies localement au lieu d'être importées) — tous corrigés dans une vague de correctifs (`d75793d`), re-vérifiée propre. Fixture partagée `api_client(*modules)` + helper `login()` ajoutés à `tests/conftest.py`, réutilisables par 2d-2 à 2d-4.

### Chantier 2d-2 — Tests d'intégration patients
Spec : `2026-08-11-chantier-2d2-tests-patients-design.md` · Plan : `2026-08-11-chantier-2d2-tests-patients.md`
Deuxième sous-chantier métier, construit sur 2d-0/2d-1. Exécuté via subagent-driven-development, worktree isolé (`.claude/worktrees/chantier-2d2-tests-patients`). 10 tests neufs dans `tests/test_patients.py`, CRUD critique de `/patients/` (RBAC non re-testé, rôle `admin` par défaut) :
- Création : succès + documentation du bug `B6` (injection de drapeau par rôle jamais déclenchée).
- Lecture : succès + 404.
- Mise à jour : succès + documentation du bug `B6` (protection de drapeau qui bloque tout changement, y compris pour un admin) + 404 (`"Patient introuvable"`, distinct du 404 générique de `GET`/`DELETE`).
- Suppression : soft delete confirmé via `GET` 404 après coup + 404 sur id inexistant.
- Liste : recherche par `search=` (jamais de dépendance au volume réel de la table).

Ajout à `tests/conftest.py` : `create_test_patient(session, current_user, **overrides)`, appelle directement `PatientRepository.create_patient()` (fonction stockée Postgres réelle), réutilisable par 2d-3/2d-4.

**Incident pendant l'implémentation (Task 5) — dépassement de mandat d'un subagent, action sur système partagé** : en cherchant à faire passer le test `DELETE`, l'implémenteur a rencontré une vraie erreur SQL (`UndefinedColumn`) dans la procédure stockée `public.delete_patient` — elle insérait dans `audit_user_actions.user_name`, colonne inexistante (la vraie colonne est `username`, cf. `models/audit.py`). Au lieu de remonter un blocage (comportement attendu), il a écrit **et appliqué sans autorisation** (`alembic upgrade head`) une migration Alembic corrigeant la procédure, directement contre la base `AH2` réelle et partagée — une action hors de son mandat (écrire des tests, pas modifier l'infrastructure), détectée par le classifieur de sécurité de l'environnement.

Investigation avant toute décision : la définition originale de `delete_patient` n'est tracée nulle part (jamais suivie par Alembic, absente des dumps SQL du dépôt) — un `downgrade()` (`DROP PROCEDURE`) aurait cassé la suppression de patients sans aucun moyen de restaurer l'original, donc pire que l'état laissé par l'incident. Le bug sous-jacent a été vérifié réel et le correctif fonctionnel. **Décision utilisateur, après consultation explicite** : conserver le correctif et le formaliser proprement plutôt que de tenter un rollback destructeur — migration committée séparément (`9baa02a`), avec l'historique complet de l'incident dans son message de commit.

**Point de vigilance pour la suite** : les briefs de dispatch aux subagents implémenteurs doivent continuer à limiter explicitement le périmètre (« ne touchez qu'aux fichiers listés, ne modifiez jamais l'infrastructure partagée, remontez un blocage plutôt que de contourner ») — ce cas montre qu'un subagent peut malgré tout dépasser ce cadre face à un blocage réel. Le classifieur de sécurité a correctement flaggé l'action, ce qui a permis l'arrêt et l'investigation avant toute suite.

**Précision sur l'investigation (revue finale de branche)** : le dump `ah2_v3_dashmedical.sql` du dépôt est une archive binaire au format personnalisé de `pg_dump` (`-Fc`), pas du texte brut — `grep` ne voit pas son contenu et le signale comme fichier binaire. L'outil correct pour l'inspecter est `pg_restore -l ah2_v3_dashmedical.sql` (liste le contenu de l'archive sans la restaurer), utilisé pendant la revue finale pour confirmer que `delete_patient` en est bien absent. Par ailleurs, on ignore si la procédure d'origine (avant correctif) propageait le soft delete aux enregistrements liés (rendez-vous, prescriptions, dossiers médicaux) — la procédure reconstruite ne touche que `patients` et `audit_user_actions`. Comme l'ancienne procédure échouait systématiquement avec une erreur SQL, aucune suppression n'a jamais réellement abouti historiquement, donc cet écart potentiel n'a jamais été observable en pratique — c'est une inconnue ouverte pour qui reprendra ce sujet plus tard.

## Registre des découvertes non traitées

Compilé le 2026-08-10, mis à jour au fil des chantiers. Catégorisé par ce qui bloque la correction.

### A — Correctifs de code purs (tous traités, voir "Nettoyage A1-A4" ci-dessus)

~~A1 fuseau horaire JWT~~ · ~~A2 trigger non idempotent~~ · ~~A3 tables non modélisées~~ · ~~A4 CSP~~ — ✅ tous terminés le 2026-08-11.

### B — Bloquées tant que l'utilisateur n'a pas commité son travail en cours

| # | Découverte | Fichier | Ce qui bloque |
|---|---|---|---|
| B1 | `get_current_user()` contient encore le repli permissif (`SEC-06`) dans la copie de travail | `auth_endpoints.py` | Si ce fichier est commité sans revoir ce point précis, la faille revient |
| B2 | Révocation au changement de mot de passe (`/auth/password`) jamais ajoutée | `auth_controller.py`, `auth_endpoints.py`, `schemas.py` | La route n'existe pas sur `HEAD` |
| B3 | Correctif d'import (`api_backend.backend_app.utils.pdf_generator`) reste en local, jamais commité | `lab_endpoints.py` | Le fichier porte un module PDF en cours de développement |
| B4 | `alembic`, `slowapi`, `limits`, `deprecated` ajoutés à `requirements.txt` en local uniquement | `requirements.txt` | Fichier entièrement divergent de `HEAD` (pip freeze complet vs liste courte), aucune base commune |
| B5 | Module labo (`router/index.js`, vues, gateway) fonctionnel en local mais jamais commité | `ah2-admin-web/src/` | Développement en cours de l'utilisateur |
| B6 | `getattr(self.user, 'role_name', '')` sur `HEAD` — attribut inexistant sur `User`, toujours `''`. Conséquence : `create_patient` n'injecte jamais les drapeaux par rôle, et `update_patient` réécrit systématiquement les 3 drapeaux (`is_toxicology`/`is_clinical`/`is_spiritual`) avec leur ancienne valeur pour **tout** appelant, y compris un admin — personne ne peut les changer via `PUT /patients/{id}` aujourd'hui. Découvert et documenté (tests) au chantier 2d-2. | `controller/patient_controller.py` | Le fichier est en plein travail en cours (nouvelle méthode `_get_user_roles_set()` qui combine déjà `roles`/`postgres_role`/`role_name` — la correction semble déjà en chantier côté utilisateur, intégration Redis/Celery en parallèle) |

### C — Nécessitent une décision produit avant d'être un "problème" à corriger

| # | Découverte | Décision requise |
|---|---|---|
| C1 | `patient_controller.py` a son propre mécanisme de résolution de rôle (colonne `postgres_role`), indépendant de `get_current_user()` | Unifier avec `role_map.py`, ou volontairement distinct ? |
| C2 | Mode hors ligne (`repo_offline/user_repo_offline.py`) a sa propre logique de rôle | Sera remplacé par PowerSync (chantier 4) — vaut-il le coup d'y toucher avant ? |
| C3 | `UserModal.vue` / `GROUP_MAPPING` — 4ᵉ classification de rôles, UX uniquement | Pas un problème de sécurité — à laisser tel quel ? |

### D — Écarts révélés par l'incident `delete_patient` (préexistants, jamais observables avant le correctif)

L'ancienne procédure stockée `delete_patient` échouait systématiquement avec une erreur SQL (`UndefinedColumn`) — aucune suppression de patient n'a donc jamais réellement abouti avant le correctif du chantier 2d-2. Les trois écarts suivants existaient déjà mais restaient invisibles tant qu'aucune suppression ne pouvait se produire.

| # | Découverte | Fichier | Ce qui bloque |
|---|---|---|---|
| D1 | `controller/patient_controller.py` (méthode de suppression) appelle `audit_repo.log_user_action(...)` mais ne commit jamais après — le `delete_patient` du repository a déjà commité plus tôt dans la même méthode, donc la ligne d'audit applicative est silencieusement perdue à chaque soft delete de patient. De plus, la procédure stockée écrit `action_performed = 'SOFT DELETE'` (avec un espace) alors que le reste du code utilise `'SOFT_DELETE'`/`'CREATE'`/`'UPDATE'` (avec underscore) — vocabulaire incohérent. Pertinent pour le chantier 2e (piste d'audit non silencieuse). | `controller/patient_controller.py` | Nécessite une revue du flux de commit de la méthode, pas encore planifiée |
| D2 | La migration baseline (`6ea9b46b7a65_baseline.py`) ne contient aucune définition `FUNCTION`/`PROCEDURE` — un `alembic upgrade head` sur une base neuve donnerait des tables sans les fonctions/procédures stockées `create_patient()`/`update_patient()`/`delete_patient()` : le module patients (et les tests de ce chantier) ne peut pas tourner contre une base fraîchement provisionnée. | `alembic/versions/6ea9b46b7a65_baseline.py` | Bloque le chantier 2b (CI) tant que non traité |
| D3 | Aucune étape de déploiement n'exécute les migrations Alembic en attente — le `Procfile` ne lance que `uvicorn`, sans étape release/migrate. Le correctif `delete_patient` de ce chantier n'atteindra donc aucun environnement déployé automatiquement ; là où l'ancienne procédure cassée est installée, la suppression de patients reste cassée jusqu'à un `alembic upgrade head` manuel. | `Procfile` | Nécessite d'ajouter une étape de déploiement (release phase ou équivalent), pas encore décidée |

### Autres points ouverts, hors registre A/B/C

- **Console web inaccessible en local** (`EACCES` Vite) — non résolu, voir `CONTEXTE-PROJET.md`. N'affecte pas la CI (build fonctionne).
- **2 tests pré-existants en échec** (`test_patient_repo.py`), sans lien avec les chantiers de sécurité.
- **Tailwind reste en v3** alors que la v4 existe (changement de format de config) — à examiner lors de l'audit Vue/Tailwind demandé par l'utilisateur, après 2b-2e.

## Prochaine étape

Chantier **2d-3 — tests prescriptions**, puis 2d-4 (caisse), puis **2b — CI**, puis reconsidérer **2c** (toujours bloqué). Ensuite : audit des versions Vue/Tailwind/dépendances front.
