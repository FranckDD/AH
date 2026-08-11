# Suivi d'avancement — AH2 / Glostone-Kare

**Dernière mise à jour :** 2026-08-11 (chantier 2d-0)
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
| 2d-1 | Tests auth + RBAC | ⬜ À faire (prochain) | — |
| 2d-2 | Tests patients | ⬜ À faire | — |
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

### C — Nécessitent une décision produit avant d'être un "problème" à corriger

| # | Découverte | Décision requise |
|---|---|---|
| C1 | `patient_controller.py` a son propre mécanisme de résolution de rôle (colonne `postgres_role`), indépendant de `get_current_user()` | Unifier avec `role_map.py`, ou volontairement distinct ? |
| C2 | Mode hors ligne (`repo_offline/user_repo_offline.py`) a sa propre logique de rôle | Sera remplacé par PowerSync (chantier 4) — vaut-il le coup d'y toucher avant ? |
| C3 | `UserModal.vue` / `GROUP_MAPPING` — 4ᵉ classification de rôles, UX uniquement | Pas un problème de sécurité — à laisser tel quel ? |

### Autres points ouverts, hors registre A/B/C

- **Console web inaccessible en local** (`EACCES` Vite) — non résolu, voir `CONTEXTE-PROJET.md`. N'affecte pas la CI (build fonctionne).
- **4 tests pré-existants en échec**, sans lien avec les chantiers de sécurité — candidats pour le chantier 2d.
- **Tailwind reste en v3** alors que la v4 existe (changement de format de config) — à examiner lors de l'audit Vue/Tailwind demandé par l'utilisateur, après 2b-2e.

## Prochaine étape

Chantier **2d — tests des chemins critiques** (auth, RBAC, patients, prescriptions, caisse), puis **2b — CI**, puis reconsidérer **2c** (toujours bloqué). Ensuite : audit des versions Vue/Tailwind/dépendances front.
