# Chantier 2d-4 — Tests d'intégration caisse et retrait

**Date :** 2026-08-12
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** quatrième sous-chantier métier de 2d, construit sur l'infrastructure de 2d-0/2d-1/2d-2/2d-3

## Contexte

2d-1 à 2d-3 ont couvert auth/RBAC, patients et prescriptions. 2d-4 couvre les deux routeurs financiers : `/caisse` (`api_backend/backend_app/routes/caisse/caisse_endpoints.py`, 17 endpoints) et `/retrait` (`api_backend/backend_app/routes/retrait/retrait_endpoints.py`, 6 endpoints). Périmètre élargi (comme 2d-3, décision utilisateur explicite) : couverture complète des deux routeurs, pas seulement le CRUD critique.

**Fichiers en travail non commité côté utilisateur** (à ne jamais toucher pendant ce chantier) : `api_backend/backend_app/routes/caisse/mapping.py` (1 ligne), `controller/caisse_controller.py` (réécriture substantielle, 395 lignes changées), `repositories/caisse_repo.py` (2 lignes). Ni `caisse_endpoints.py`/`caisse_schemas.py` ni tout le module `retrait` (`retrait_endpoints.py`, `caisse_retrait_controller.py`, `caisse_retrait_repo.py`) ne sont touchés par le travail en cours — périmètre plus restreint que prescriptions (qui avait 5 fichiers en WIP).

## Modèle de données

- **`Caisse`** (`models/caisse.py`) : `transaction_id` (PK), `patient_id` (nullable), `amount`, `advance_amount` (défaut 0), `payment_method`, `transaction_type`, `status` (défaut `active`), `paid_at`, relation `items`.
- **`CaisseItem`** (`models/caisse_item.py`) : lignes de transaction — `item_type`, `item_ref_id`, `unit_price`, `quantity`, `line_total`.
- **`CaisseRetrait`** (`models/retrait.py`) : `retrait_id` (PK), `amount`, `justification`, `status` (défaut `active`), `category`/`payment_method` optionnels, traçabilité d'annulation (`cancelled_by`, `cancelled_at`, `cancel_justification`).

**RBAC** : `role_required("secretaire", "admin")` sur les deux routeurs — différent de prescriptions (`medecin`/`nurse`/`admin`/`manager`), plus proche de `/users/` (2d-1) mais avec `secretaire` autorisée cette fois (elle en était exclue sur prescriptions).

**Différence structurelle majeure avec prescriptions** : `create_transaction`/`update_transaction` (`caisse_endpoints.py`) prennent un `dict` brut (`Body(...)`), pas un schéma Pydantic — toute la validation est manuelle dans `CaisseController`/`CaisseRepository`. `create_retrait` (`retrait_endpoints.py`) utilise des paramètres `Body(...)` individuels (`amount: float = Body(..., gt=0)`, etc.), pas un dict non plus.

## Découvertes pendant le cadrage (à vérifier empiriquement pendant la rédaction du plan, pas supposées)

### Bug 1 — notification Celery avec un mauvais nom d'attribut

`controller/caisse_controller.py::create_transaction` appelle `task_process_payment_notification.delay(transaction_id=tx.id, ...)` — mais le modèle `Caisse` n'a pas d'attribut `id`, seulement `transaction_id`. Ceci devrait lever `AttributeError` à chaque création, avalé silencieusement par `except Exception as e: print(...)`. Même risque de blocage prolongé que sur prescriptions (chantier 2d-3, où `.delay()` sur un broker Celery injoignable a bloqué ~109 secondes) — à confirmer par exécution réelle.

### Bug 2 — suppression potentiellement idempotente silencieuse

`api_backend/backend_app/routes/caisse/caisse_endpoints.py::delete_transaction` : `caisse_ctrl.delete_transaction(transaction_id); return None` — le code ne vérifie jamais la valeur de retour de `delete_transaction()`. Or `repositories/caisse_repo.py::delete_transaction()` retourne silencieusement `None` (sans lever d'exception) si l'id n'existe pas : `tx = self.get_by_id(transaction_id); if tx: ...; return tx`. Comme l'endpoint ne teste jamais ce retour, `DELETE /caisse/{id}` sur un id inexistant devrait renvoyer 204 comme un succès — motif identique au bug `E2` de prescriptions (2d-3).

### Item à confirmer — item_type neutre pour les tests

`create_transaction` (contrôleur) valide les lignes dont `item_type.lower() == "consultation"` contre une vraie ligne `ConsultationSpirituel` ; `create_transaction`/`update_transaction` (repository) déduisent du stock `Pharmacy` réel pour les types contenant "médicament"/"medication"/"carnet"/"booklet". Un `item_type` ne correspondant à aucun de ces mots-clés (ex. `"Service"`) évite ces deux validations et permet de créer des lignes de test sans dépendre de vraies données `Pharmacy`/`ConsultationSpirituel` — à confirmer que ce chemin fonctionne réellement pendant le cadrage du plan.

## Portée

### `/caisse` (17 endpoints testés, KPI/PDF/recherche inclus)
- CRUD : `POST /caisse/` (création), `GET /caisse/{id}`, `PUT /caisse/{id}`, `DELETE /caisse/{id}`, `GET /caisse/` (liste/recherche paginée).
- Paiement échelonné : `POST /caisse/{id}/payment`.
- Cycle de vie : `POST /caisse/{id}/settle`, `POST /caisse/{id}/cancel`.
- Rattachement patient : `GET /caisse/patient/{patient_id}`.
- KPIs : `GET /caisse/daily_total`, `GET /caisse/total`, `GET /caisse/total_payments`, `GET /caisse/total_remaining_due`.
- Facture : `GET /caisse/{id}/invoice/download` (vérifie uniquement que des octets PDF reviennent avec le bon `Content-Type`, pas le contenu texte de la facture).

Hors périmètre explicite dans `/caisse` : les 3 routes `GET /caisse/dashboard/caisse/*` (KPIs de tableau de bord agrégés — `kpis`, `unpaid`, `payment_distribution`) sont **incluses** dans la couverture complète demandée, mais avec des tests légers (structure de réponse + cohérence arithmétique de base), pas une couverture exhaustive de tous les cas limites de chaque agrégation.

### `/retrait` (6 endpoints)
- CRUD partiel : `POST /retrait/` (création), `GET /retrait/{id}`, `GET /retrait/` (liste paginée), `GET /retrait/search` (recherche paginée) — pas de `PUT`/`DELETE`, ce routeur n'en expose pas.
- Cycle de vie : `POST /retrait/{id}/cancel`.
- KPI : `GET /retrait/total`.

## Détail de l'implémentation

### Factories (ajout à `tests/conftest.py`)

1. `create_test_transaction(session, current_user, **overrides)` — appelle `CaisseRepository.create_transaction(data, current_user)` directement, avec un item par défaut utilisant un `item_type` neutre (voir "Item à confirmer" ci-dessus). Retourne l'objet `Caisse` créé (id réel disponible directement, contrairement à `create_test_prescription` qui devait le retrouver via une requête HTTP séparée — le repo caisse retourne déjà l'objet complet).
2. `create_test_retrait(session, current_user, **overrides)` — appelle `CaisseRetraitRepository.create(...)` directement. Retourne l'objet `CaisseRetrait` créé.

Les deux réutilisent `create_test_user` (2d-1) ; `create_test_transaction` accepte un `patient_id` optionnel (le champ est nullable sur `Caisse`), donc ne nécessite pas systématiquement `create_test_patient`.

### Tests (deux fichiers séparés, un par routeur)

`tests/test_caisse.py` et `tests/test_retrait.py` — séparés plutôt qu'un seul fichier, pour rester dans l'esprit "chaque fichier une responsabilité claire" et parce que ce sont deux routeurs distincts avec des contrôleurs/dépôts distincts (aucun code partagé entre eux hormis les factories communes de `conftest.py`).

Catégories de tests par routeur (le détail exact — noms, payloads, assertions précises — sera écrit dans le plan d'implémentation, après vérification empirique de chaque comportement contre `HEAD` réel, comme pour 2d-3) :
- Création : succès (structure de réponse, montant, avance initiale si applicable), validations métier (champ requis manquant → 400, incohérence montant total/lignes → 400, référence de ligne invalide → 400).
- Lecture : succès + 404, liste/recherche avec filtres (terme, méthode de paiement, statut, plage de dates), pagination.
- Mise à jour : succès, refus sur transaction annulée, 404 sur id inexistant.
- Suppression : succès + comportement sur id inexistant (documente le Bug 2 si confirmé).
- Paiement échelonné, solde, annulation : chemins nominaux + refus sur transaction déjà annulée.
- KPIs : structure de réponse pour chaque endpoint, cohérence arithmétique de base (ex. `total_remaining_due == total - total_payments` sur un jeu de données contrôlé).
- Téléchargement facture PDF : `Content-Type: application/pdf`, corps non vide, 404/erreur sur id inexistant.
- RBAC : rôle autorisé (`secretaire` ou `admin`) vs rôle refusé, non authentifié — sur au moins une route de chaque routeur (pas toutes, RBAC déjà bien couvert par 2d-1 dans son mécanisme générique).

## Vérification

- Tous les tests neufs passent contre `HEAD` (worktree isolé)
- Aucune régression sur la suite existante
- Aucune donnée résiduelle dans `AH2` après la suite
- Mise à jour de `docs/superpowers/SUIVI-AVANCEMENT.md` : détail du chantier + éventuelle nouvelle catégorie de registre pour les bugs confirmés

## Hors périmètre

- Le module `finance_tasks.py`/Celery/Redis lui-même (comme pour prescriptions, si un bug de blocage est confirmé il est documenté, pas corrigé dans ce chantier).
- Toute correction de bug découvert — ce chantier documente, ne corrige pas (sauf décision explicite contraire de l'utilisateur, comme cela a été fait après coup pour prescriptions).
- Le contenu réel généré du PDF de facture (mise en page, texte) — seule la présence d'octets PDF valides est vérifiée.
- Les vues desktop PyQt6 (`view_pyqt6/`) qui consomment potentiellement ces mêmes contrôleurs en mode hors-ligne — hors périmètre de l'API testée ici.
