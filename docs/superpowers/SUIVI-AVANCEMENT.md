# Suivi d'avancement — AH2 / Glostone-Kare

**Dernière mise à jour :** 2026-08-12 (chantier 2b)
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
| 2d-3 | Tests prescriptions | ✅ Terminé | `d998b51`..`4974068` |
| 2d-4 | Tests caisse | ✅ Terminé | `d030693`..`d663640` |
| 2b | CI (GitHub Actions) | ✅ Terminé | `032d554`..`6ffe5a8` |
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

**Couplage avec le travail en cours non commité (à traiter au prochain commit de `patient_controller.py`)** : dans le worktree isolé (code commité uniquement), les 10 tests passent. Dans le répertoire de travail principal, `test_update_patient_flag_protection_prevents_any_change` **échoue** — et c'est le comportement voulu. Le `controller/patient_controller.py` non commité de l'utilisateur remplace `getattr(self.user, 'role_name', '')` par `_get_user_roles_set()` (lignes 40-50, 83, 111) : le bug `B6` y est donc **déjà corrigé**, un admin peut à nouveau modifier `is_toxicology`, et le test qui affirme l'inverse tombe. Les contraintes globales du plan exigeaient précisément qu'un test documentant un bug « échoue si le bug venait à être corrigé sans mise à jour du test » — le garde-fou a fonctionné.

**Action requise au moment où `controller/patient_controller.py` sera commité** : mettre à jour les deux tests de documentation de `B6` dans `tests/test_patients.py` pour qu'ils affirment le comportement corrigé (l'admin peut changer les drapeaux ; l'injection par rôle se déclenche à la création), et fermer la ligne `B6` du registre. Ne pas les supprimer : les convertir.

**Point de vigilance pour la suite** : les briefs de dispatch aux subagents implémenteurs doivent continuer à limiter explicitement le périmètre (« ne touchez qu'aux fichiers listés, ne modifiez jamais l'infrastructure partagée, remontez un blocage plutôt que de contourner ») — ce cas montre qu'un subagent peut malgré tout dépasser ce cadre face à un blocage réel. Le classifieur de sécurité a correctement flaggé l'action, ce qui a permis l'arrêt et l'investigation avant toute suite.

**Précision sur l'investigation (revue finale de branche)** : le dump `ah2_v3_dashmedical.sql` du dépôt est une archive binaire au format personnalisé de `pg_dump` (`-Fc`), pas du texte brut — `grep` ne voit pas son contenu et le signale comme fichier binaire. L'outil correct pour l'inspecter est `pg_restore -l ah2_v3_dashmedical.sql` (liste le contenu de l'archive sans la restaurer), utilisé pendant la revue finale pour confirmer que `delete_patient` en est bien absent. Par ailleurs, on ignore si la procédure d'origine (avant correctif) propageait le soft delete aux enregistrements liés (rendez-vous, prescriptions, dossiers médicaux) — la procédure reconstruite ne touche que `patients` et `audit_user_actions`. Comme l'ancienne procédure échouait systématiquement avec une erreur SQL, aucune suppression n'a jamais réellement abouti historiquement, donc cet écart potentiel n'a jamais été observable en pratique — c'est une inconnue ouverte pour qui reprendra ce sujet plus tard.

### Chantier 2d-3 — Tests d'intégration prescriptions
Spec : `2026-08-11-chantier-2d3-tests-prescriptions-design.md` · Plan : `2026-08-11-chantier-2d3-tests-prescriptions.md`
Troisième sous-chantier métier, construit sur 2d-0/2d-1/2d-2. Exécuté via subagent-driven-development, worktree isolé (`.claude/worktrees/chantier-2d3-tests-prescriptions`). 25 tests neufs dans `tests/test_prescriptions.py`, tout le routeur `/prescriptions` : CRUD, `/renewals`, `/kpi/count`, `/patient/{id}`, RBAC propre à ce routeur (`medecin`, `nurse`, `admin`, `manager` — différent de `/users/`) :
- Création : succès (documente le bug `E5`, le corps de réponse réel est le repli générique) + 422 (champ requis manquant) + plantage `TypeError` du gestionnaire de validation global sur dates invalides (`E1`, transversal) + 403 secrétaire + 401 non-authentifié + 201 pour le rôle `nurse`.
- Lecture : succès + 404 + liste filtrée par `patient_id`/plage de dates/recherche (valeur hautement unique pour éviter toute collision avec des données réelles préexistantes).
- Mise à jour : succès avec payload complet + 409 sur payload partiel (`E4`, réécriture destructive de la procédure stockée) + 500 sur id inexistant (`E3`, corrige une hypothèse initiale erronée de la spec) + même plantage `TypeError` que la création.
- Suppression : suppression physique confirmée via `GET` 404 après coup + documentation du bug `E2` (204 au lieu de 404 sur un id inexistant).
- Renouvellements et KPI : fenêtre `within_days` (dans/hors fenêtre) et compteurs jour/semaine (comparaison avant/après pour ne pas dépendre du volume réel de la table).
- Historique patient : prescription créée retrouvée + filtre par `status`.
- RBAC transversal : confirme que `role_required` s'applique à tout le routeur, pas seulement à `POST /`.

**Périmètre élargi par rapport à 2d-1/2d-2** (demandé explicitement par l'utilisateur, malgré cinq fichiers du module en travail non commité) : couverture complète du routeur plutôt que le seul CRUD critique, RBAC re-testé (routeur avec ses propres rôles autorisés), et un cadrage du plan appuyé sur exécution réelle contre un worktree jetable basé sur `HEAD` (créé et supprimé pendant le cadrage) plutôt que sur la seule lecture de code — ce qui a permis d'infirmer deux hypothèses de la spec initiale et de découvrir deux bugs supplémentaires (`E5`, `E6`) non anticipés, remontés par les implémenteurs de Task 2 puis vérifiés indépendamment avant correction du plan.

**Nouvelle catégorie de registre E** (6 items, détaillée ci-dessous) : contrairement à la catégorie B, ces défauts sont dans du code déjà committé (`main.py`, procédures stockées, schémas Pydantic) et ne dépendent d'aucun fichier en travail en cours côté utilisateur — corrigeables dès qu'un chantier dédié leur est consacré. `E1` et `E5` sont les plus prioritaires : `E1` est transversal (touche potentiellement toute route utilisant un validateur Pydantic qui lève `ValueError`), et `E5` signifie que la route de création la plus utilisée du module ne renvoie jamais son contrat documenté à un vrai client.

**Couplage avec le travail en cours non commité (constaté à la fusion dans `AH2_V3-1`)** : sur les 25 tests, 4 passent dans le worktree isolé (code committé uniquement) mais échouent dans le répertoire de travail principal, à cause des cinq fichiers du module prescriptions en travail non commité côté utilisateur. Diagnostic précis de chaque échec (pas une simple attribution générique) :
- `test_create_prescription_success` échoue car `POST /prescriptions/` renvoie désormais le corps complet de la prescription (16 champs, dont un nouveau champ `is_lab_order` absent de `HEAD`) au lieu du repli générique — **`E5` semble déjà corrigé dans le travail en cours**.
- `test_delete_prescription_nonexistent_returns_204_not_404` échoue car `DELETE` sur un id inexistant renvoie désormais 404 au lieu de 204 — **`E2` semble déjà corrigé dans le travail en cours**.
- `test_update_prescription_partial_payload_returns_409` et `test_update_prescription_not_found_returns_500` échouent tous les deux avec le même plantage `TypeError: Object of type ValueError is not JSON serializable` que documente `E1` : le travail en cours a ajouté un nouveau validateur métier ("Le nom du médicament est requis pour une prescription standard.") sur le schéma, qui se déclenche avant même d'atteindre le code que ces deux tests visent (payloads sans `medication`) — **`E1` ne semble donc PAS corrigé dans le travail en cours**, c'est une règle métier ajoutée par-dessus qui intercepte plus tôt.

**Action requise au moment où les fichiers du module prescriptions seront commités** : convertir `test_create_prescription_success` et `test_delete_prescription_nonexistent_returns_204_not_404` pour affirmer le comportement corrigé (fermer `E2`/`E5`) ; revoir `test_update_prescription_partial_payload_returns_409`/`test_update_prescription_not_found_returns_500` à la lumière du nouveau validateur métier (le 409/500 attendu ne sera peut-être plus jamais atteignable si `E1` reste présent) ; garder `E1`, `E3`, `E4`, `E6` ouverts sauf preuve du contraire.

### Chantier 2d-4 — Tests d'intégration caisse et retrait
Spec : `2026-08-12-chantier-2d4-tests-caisse-design.md` · Plan : `2026-08-12-chantier-2d4-tests-caisse.md`
Quatrième sous-chantier métier, construit sur 2d-0/2d-1/2d-2/2d-3. Exécuté via subagent-driven-development, worktree isolé (`.claude/worktrees/chantier-2d4-tests-caisse`). 43 tests neufs : 32 dans `tests/test_caisse.py` (routeur `/caisse`, 17 endpoints), 11 dans `tests/test_retrait.py` (routeur `/retrait`, 6 endpoints). RBAC identique sur les deux routeurs (`secretaire`/`admin`, différent de prescriptions) :
- Caisse — création : succès + documentation du bug `F1` (calcul erroné de `amount_due`/`amount_paid` dans `mapping.py`) + validations métier (champ requis, incohérence montant/lignes, référence de consultation invalide) + RBAC.
- Caisse — lecture : succès + 404, liste/recherche filtrée (terme, statut, plage de dates), liste par patient.
- Caisse — mise à jour : succès, refus après annulation, 400 (pas 404) sur id inexistant.
- Caisse — suppression : succès + documentation du bug `F2` (204 au lieu de 404 sur un id inexistant, même motif que `E2` sur prescriptions).
- Caisse — paiement/solde/annulation : succès + documentation du corps de réponse vide sur le paiement échelonné + documentation de l'idempotence silencieuse sur double annulation.
- Caisse — KPIs : `daily_total`/`total`/`total_payments` (comparaison avant/après, données réelles préexistantes) + documentation de l'incohérence de filtre implicite sur `total_remaining_due` + KPIs de tableau de bord bornés par date (valeurs exactes fiables, calcul correct — contrairement au bug `F1`).
- Caisse — facture PDF : téléchargement réel (10+ Ko constatés), Content-Type correct, 404 sur id inexistant.
- Retrait — couverture complète : création (succès + 422 montant négatif), lecture, liste, recherche, total, annulation (refus explicite sur double annulation — contraste documenté avec l'idempotence de `/caisse/{id}/cancel`), RBAC.

**Correction empirique par rapport à la spec** : le "Bug 1" anticipé (notification Celery avec `tx.id` au lieu de `tx.transaction_id`) ne se manifeste pas sur `HEAD` — `tasks/finance_tasks.py` n'existe que dans le travail en cours non commité de l'utilisateur, l'import échoue silencieusement sur `HEAD` et tout le bloc de notification est court-circuité. Aucun test ne le documente ; il redeviendra pertinent si ce fichier est un jour commité.

**Fichiers en travail non commité** (jamais touchés par ce chantier) : `api_backend/backend_app/routes/caisse/mapping.py`, `controller/caisse_controller.py`, `repositories/caisse_repo.py`. Le module `retrait` n'est pas touché par le travail en cours.

**Couplage avec le travail en cours non commité (constaté à la fusion dans `AH2_V3-1`)** : sur les 43 tests, 1 échoue dans le répertoire de travail principal (mais passe dans le worktree isolé) : `test_create_transaction_amount_mismatch_returns_400` échoue avec `AssertionError: assert 'ne correspond pas' in 'Incohérence montant: Lignes(100.0) != Total(999.0).'` — le travail en cours sur `controller/caisse_controller.py` a changé le texte du message d'erreur de `create_transaction` sur une incohérence montant/lignes, qui ressemble désormais à celui d'`update_transaction` (`"Incohérence montant."`) plutôt qu'au message distinct de `HEAD` (`"Le montant total des lignes (...) ne correspond pas à data['amount'] (...)."`). Aucun autre test de ce chantier n'est affecté par le travail en cours — les 11 autres échecs du run fusionné (`test_patient_repo.py`, `test_patients.py`, `test_prescription_repo.py`, `test_prescriptions.py`) sont déjà attribués et documentés ailleurs dans ce fichier, aucun n'est nouveau.

**Action requise au moment où `controller/caisse_controller.py` sera commité** : mettre à jour l'assertion de `test_create_transaction_amount_mismatch_returns_400` pour refléter le nouveau texte du message (à constater précisément à ce moment-là, pas à deviner maintenant).

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
| D2 | ~~La migration baseline ne contenait aucune définition `FUNCTION`/`PROCEDURE`.~~ **Résolu au chantier 2b** : `create_patient`/`update_patient`/`create_prescription`/`update_prescription` + 4 fonctions de trigger + `current_user_id()` (dépendance cachée) désormais suivies (`alembic/versions/002_add_missing_procedures_triggers.py`, appliquée pour de vrai contre `AH2` locale, `CREATE OR REPLACE` partout donc idempotente). `delete_patient` restait déjà couvert depuis 2d-2. La baseline elle-même (`6ea9b46b7a65_baseline.py`, ~70 `DROP` générés par autogénération) reste inutilisable contre une base vide — voir `G1` : la CI la contourne, ne la corrige pas. | `alembic/versions/002_add_missing_procedures_triggers.py` | Résolu pour l'usage réel et pour la CI ; la baseline elle-même reste un `DROP`-miné non exécutable tel quel contre une base neuve |
| D3 | Aucune étape de déploiement n'exécute les migrations Alembic en attente — le `Procfile` ne lance que `uvicorn`, sans étape release/migrate. Le correctif `delete_patient` de ce chantier n'atteindra donc aucun environnement déployé automatiquement ; là où l'ancienne procédure cassée est installée, la suppression de patients reste cassée jusqu'à un `alembic upgrade head` manuel. | `Procfile` | Nécessite d'ajouter une étape de déploiement (release phase ou équivalent), pas encore décidée |

### E — Découvertes du chantier 2d-3 (prescriptions), non bloquées par le travail en cours

Contrairement aux catégories B, ces défauts sont dans du code purement
committé (`main.py`, procédures stockées) et ne dépendent d'aucun fichier
en travail en cours côté utilisateur — ils peuvent être corrigés dès
qu'un chantier dédié leur est consacré.

| # | Découverte | Fichier | Gravité |
|---|---|---|---|
| E1 | `main.py::validation_exception_handler` sérialise `exc.errors()` tel quel en JSON (`json.dumps` standard). Quand une erreur de validation vient d'un `model_validator` qui lève `ValueError` (ex. `PrescriptionBase.check_dates`), Pydantic inclut l'exception elle-même dans `error["ctx"]["error"]` — non sérialisable → `TypeError` non intercepté, propagé brut au client au lieu d'un 422 propre. **Transversal : touche potentiellement toute route dont un schéma Pydantic utilise `raise ValueError(...)` dans un validateur**, pas seulement les prescriptions. | `api_backend/backend_app/main.py` | Élevée — un client réel reçoit une erreur 500 non structurée là où un 422 propre est attendu |
| E2 | `repositories/prescription_repo.py::delete()` exécute un `DELETE FROM` brut sans vérifier le rowcount, retourne toujours `True`. Pas de suppression logique sur `Prescription` (à la différence de `Patient`) — suppression physique sans garde-fou : `DELETE /prescriptions/{id}` sur un id inexistant renvoie 204 au lieu de 404. | `repositories/prescription_repo.py` | Faible — comportement silencieux, pas de perte de données |
| E3 | `PUT /prescriptions/{id}` sur un id inexistant renvoie 500 (`"Erreur serveur lors de la mise à jour de la prescription"`), pas 404 : la procédure stockée `public.update_prescription` lève sa propre exception PL/pgSQL sur un id absent, remontée comme `SQLAlchemyError` générique. | `repositories/prescription_repo.py`, procédure stockée `public.update_prescription` (non tracée — item `D2`) | Moyenne |
| E4 | `public.update_prescription` réécrit toutes les colonnes inconditionnellement (pas de `COALESCE`). Un `PUT` avec un payload partiel remet à `NULL` les champs omis — plante en 409 si un champ `NOT NULL` est omis, sinon efface silencieusement les champs nullable (`notes`, `end_date`, `medical_record_id`). `PUT` n'est utilisable qu'avec un payload complet, jamais partiel. | procédure stockée `public.update_prescription` (non tracée — item `D2`) | Élevée — perte de données silencieuse possible sur les champs nullable |
| E5 | `POST /prescriptions/` ne renvoie **jamais** la prescription créée, même en cas de succès complet. `repo.create()` renvoie `True` ; comme `bool` est une sous-classe d'`int` en Python, `isinstance(True, int)` vaut `True` — la branche `if isinstance(created, int):` intercepte systématiquement avant la branche `elif created is True or created is None:` écrite pour ce cas précis. Le code tente alors `get_prescription(True)`, qui plante contre PostgreSQL (`operator does not exist: integer = boolean`), silencieusement avalé, et retombe sur le repli générique `{"detail": "Prescription créée (lecture non disponible)"}` — jamais le corps `PrescriptionResponse` déclaré par la route. Un vrai client (le frontend Vue) ne reçoit donc jamais la prescription qu'il vient de créer. **Même après correction de l'ordre isinstance, cette branche resterait cassée** : `list_prescriptions()` renvoie `{"data": [...], "total": N}` (dict), pas une liste — `recent[0]` lèverait `KeyError: 0`, avalé par le même `except Exception`, avec le même repli générique en résultat. Il faudrait `recent["data"][0]`. Les deux défauts doivent être corrigés ensemble pour que l'endpoint fonctionne réellement. | `api_backend/backend_app/routes/prescription/prescriptions_endpoints.py:183-207`, `controller/prescription_controller.py:37-63` | **La plus élevée du registre E** — la route de création la plus utilisée de ce module ne remplit jamais son contrat documenté |
| E6 | La colonne `prescriptions.duration` est `NOT NULL` en base (`models/prescription.py`), mais `PrescriptionBase.duration` est `Optional[str] = None` côté Pydantic et `PrescriptionCreate` ne le rend pas requis (contrairement à `medication`/`dosage`/`frequency`/`start_date`, explicitement surchargés en requis). Toute création qui omet `duration` échoue en 409 `IntegrityError`, quel que soit le rôle — découvert par l'implémenteur de Task 2 sur un payload de test, vérifié indépendamment (`nullable=False` confirmé sur le modèle). | `api_backend/backend_app/routes/prescription/prescriptions_schemas.py:12`, `models/prescription.py:16` | Moyenne — écart schéma/base cohérent avec E4 (mêmes colonnes `NOT NULL` que la procédure de mise à jour) |

**Note (pas un bug, une limite de couverture)** : seul `manager` n'est pas seedé dans `application_roles` (`api_backend/backend_app/security/role_map.py` le documente comme "réservé, en développement") ; `admin` l'est (comme `medecin`/`nurse`) mais n'est pas exercé par un test RBAC-positif dans ce chantier — une lacune de couverture, pas une limite de rôles seedés.

### F — Découvertes du chantier 2d-4 (caisse, retrait), non bloquées par le travail en cours

Comme la catégorie E, ces défauts sont dans du code déjà committé et ne
dépendent d'aucun fichier en travail en cours côté utilisateur —
corrigeables dès qu'un chantier dédié leur est consacré.

| # | Découverte | Fichier | Gravité |
|---|---|---|---|
| F1 | `normalize_caisse_data()` calcule `amount_due = amount + advance_amount` (devrait être `amount - advance_amount`) et `amount_paid = amount` (devrait être `advance_amount`). Confirmé avec `amount=100, advance_amount=30` : `amount_due=130` (attendu 70), `amount_paid=100` (attendu 30). Indépendant des KPIs de tableau de bord (`get_caisse_kpis`), qui calculent correctement. Tout client (frontend) affichant ces deux champs par transaction affiche des montants faux. | `api_backend/backend_app/routes/caisse/mapping.py` | Élevée — chiffres financiers visibles par transaction, faux dans les deux sens |
| F2 | `DELETE /caisse/{id}` sur un id inexistant renvoie 204 au lieu de 404 — l'endpoint ne vérifie jamais la valeur de retour de `delete_transaction()`, qui échoue silencieusement (`None`, pas d'exception) sur un id absent. Même motif que `E2` sur prescriptions. | `api_backend/backend_app/routes/caisse/caisse_endpoints.py` | Faible — comportement silencieux, pas de perte de données |
| F3 | `POST /caisse/{id}/payment` ne déclare pas de `response_model` — renvoie 201 avec un corps vide `{}` (l'objet ORM `PaiementEchelonne` retourné n'est pas sérialisable sans schéma). Le client doit refaire un `GET` pour voir l'état à jour. | `api_backend/backend_app/routes/caisse/caisse_endpoints.py` | Faible — pas de perte de données, juste un round-trip supplémentaire nécessaire côté client |
| F4 | `get_total_remaining_due()` filtre implicitement `status='active'` même sans paramètre `status` explicite, contrairement à `get_total_transactions()`/`get_total_payments()` qui ne filtrent par statut que si demandé. Incohérence d'API entre trois endpoints de la même famille (`/caisse/total`, `/caisse/total_payments`, `/caisse/total_remaining_due`). | `repositories/caisse_repo.py` | Moyenne — surprend un appelant qui s'attend à un comportement uniforme entre les trois endpoints |
| F5 | Annuler une transaction caisse déjà annulée réussit silencieusement (200, `cancel_transaction()` fait `if tx.status == 'cancelled': return tx` sans erreur), alors qu'annuler un retrait déjà annulé est explicitement refusé (400 `"Ce retrait est déjà annulé."`). Incohérence de comportement entre deux modules très proches du même domaine (caisse). | `repositories/caisse_repo.py` vs `repositories/caisse_retrait_repo.py` | Faible — incohérence de contrat API, pas de perte de données |
| F6 | `update_transaction()` supprime inconditionnellement toutes les `CaisseItem` existantes avant de vérifier si le payload contient `items`, puis ne réinsère que `data.get("items", [])`. Un `PUT` partiel qui omet `items` supprime donc définitivement toutes les lignes de facture (le total `amount` reste inchangé, sans plus aucune ligne pour le justifier), et pour les lignes `médicament`/`carnet`, restaure le stock sans jamais le redéduire — inflation de stock fantôme permanente. Le finding le plus grave de ce registre : perte de données de facturation et corruption de stock, silencieuses, en un seul appel `PUT`. | `repositories/caisse_repo.py` | **La plus élevée du registre F** — perte de données financières et corruption de stock, pas seulement un champ mal affiché |

**Note (pas un bug)** : `tasks/finance_tasks.py` — référencé par `controller/caisse_controller.py` mais absent de `HEAD` (uniquement dans le travail en cours de l'utilisateur) — n'a jamais été exercé par ce chantier. Si ce fichier est un jour commité, revérifier `create_transaction` : l'appel `task_process_payment_notification.delay(transaction_id=tx.id, ...)` utilise `tx.id`, qui n'existe pas sur le modèle `Caisse` (seul `transaction_id` existe) — probable `AttributeError` avalée silencieusement, à re-tester à ce moment-là.

### G — Découvertes du chantier 2b (CI GitHub Actions)

| # | Découverte | Fichier | Gravité / statut |
|---|---|---|---|
| G1 | La migration baseline (`6ea9b46b7a65_baseline.py`) contient environ 70 `op.drop_table`/`op.drop_index`/`op.drop_constraint`, générés par autogénération contre une base déjà peuplée. Contre une base Postgres neuve et vide, `alembic upgrade head` échoue immédiatement (`UndefinedTable: patient_contacts`). Corriger individuellement ces ~70 suppressions serait disproportionné par rapport à l'objectif de ce chantier. | `alembic/versions/6ea9b46b7a65_baseline.py` | Non corrigé — contourné en CI par restauration d'un dump schéma-seulement (`ci/schema_only.sql`) + `alembic stamp head`, jamais `upgrade head`, contre une base neuve |
| G2 | Le schéma contient une politique RLS (`CREATE POLICY medical_policy ON public.patients TO app_medical USING (true)`) référençant le rôle Postgres `app_medical`. Un dump `--no-owner --no-privileges` ne supprime pas cette dépendance (ce n'est pas une métadonnée de propriété, c'est une vraie référence d'objet) — restaurer `ci/schema_only.sql` échoue si le rôle n'existe pas déjà. | `ci/schema_only.sql`, `.github/workflows/ci.yml` | Résolu — le workflow crée le rôle avant de restaurer le schéma |
| G3 | Un dump schéma-seulement contient zéro ligne dans toutes les tables, y compris les tables de configuration statique. `tests/conftest.py::create_test_user()` dépend de 9 lignes dans `application_roles` pour résoudre `role_name` → `role_id` ; sans elles, toute création d'utilisateur de test échoue en cascade (`NoResultFound`), soit la quasi-totalité de la suite. | `tests/conftest.py`, `ci/seed_application_roles.sql` | Résolu — seed dédié restauré après le schéma, avant `alembic stamp head` |
| G4 | `ci/schema_only.sql` et `ci/seed_application_roles.sql` sont des instantanés figés de `AH2` locale au moment de ce chantier. Toute future migration Alembic modifiant réellement le schéma doit être accompagnée d'une régénération manuelle de ces deux fichiers (`pg_dump --schema-only`/`--data-only -t application_roles`), sinon la CI stampera silencieusement un historique qui ne correspond plus à ce qu'elle a réellement provisionné. | `ci/schema_only.sql`, `ci/seed_application_roles.sql` | Limitation connue, non automatisée — à surveiller à chaque nouvelle migration touchant le schéma |
| G5 | `api_backend/backend_app/config.py` exige aussi `AH2_API_BASE` (pas seulement `DATABASE_URL`/`JWT_SECRET`/`JWT_ALGORITHM`) dès que `IS_CLIENT` est faux (le cas par défaut) — sinon `RuntimeError` dès l'import du module, avant même que les tests ne démarrent. Absent de la spec et du plan initiaux, découvert par la revue finale de branche (la vérification empirique du contrôleur avait `.env` présent localement, qui définit cette variable, masquant le problème). | `api_backend/backend_app/config.py`, `.github/workflows/ci.yml` | Résolu — variable ajoutée au workflow |
| G6 | `requirements.txt` ne décrivait pas tout le graphe d'imports réellement exercé par la suite de tests : `Pillow` (import direct de l'app via `config_controller.py`, cassait potentiellement toute la suite) et `python-multipart` (dépendance transitive de FastAPI pour les champs `Form`, fonctionnait par accident avec la version pinée) manquaient. `PyQt6` (desktop uniquement) a été exclu du fichier et le test qui l'importe (`tests/test_auth_manager.py`) protégé par `pytest.importorskip`. | `requirements.txt`, `tests/test_auth_manager.py` | Résolu — packages ajoutés, test desktop-only protégé |

### Autres points ouverts, hors registre A/B/C

- **Console web inaccessible en local** (`EACCES` Vite) — non résolu, voir `CONTEXTE-PROJET.md`. N'affecte pas la CI (build fonctionne).
- **2 tests pré-existants obsolètes** (`test_patient_repo.py::test_update_patient_success`, `test_update_patient_not_found`), sans lien avec les chantiers de sécurité — marqués `xfail` au chantier 2b (`strict=False`) : visibles dans le rapport pytest sans faire échouer la CI.
- **Tailwind reste en v3** alors que la v4 existe (changement de format de config) — à examiner lors de l'audit Vue/Tailwind demandé par l'utilisateur, après 2b-2e.

## Prochaine étape

Chantier **2b — CI (GitHub Actions)** terminé (voir registre `G` pour les découvertes). Reconsidérer **2c** (toujours bloqué). Ensuite : audit des versions Vue/Tailwind/dépendances front.
