# Chantier 1 — Unification des rôles (chemin web)

**Date :** 2026-08-10
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** audit `ARC-01`, `SEC-06`, `WEB-04` ; suite du chantier 0

## Contexte

Le chantier 0 a fermé les vulnérabilités P0 d'exposition, à l'exception explicite de `SEC-06` : le repli permissif du système de rôles, qui dépend d'une refonte plus large — c'est l'objet de ce chantier.

En cadrant ce chantier, l'exploration a révélé que le problème dépasse les 4 systèmes de rôles identifiés par l'audit initial (`ARC-01`). Le dépôt contient en réalité **6 à 8 mécanismes de résolution de rôle distincts et partiellement incohérents** :

1. `api_backend/backend_app/security/role_map.py` — table de correspondance canonique, ne couvre que 5 des 9 rôles réels
2. La table `application_roles` en base — 9 rôles réels : `admin`, `medecin`, `nurse`, `secretaire`, `laborantin`, `Psychologist`, `SpiritualCounsellor`, `ToxicoManager`, `Assistant`
3. `get_current_user()` dans `auth_endpoints.py` — repli fail-open sur le rôle brut en minuscules quand la normalisation échoue (`SEC-06`)
4. `routes/core/permissions.py` — code mort, importe `from app.routes.auth...` (package inexistant), zéro import ailleurs dans le dépôt (vérifié)
5. `controller/patient_controller.py` — combine `application_role.role_name` **et** une colonne séparée `postgres_role` dans son propre ensemble de rôles, indépendamment de `get_current_user()`
6. `repositories/repo_offline/user_repo_offline.py` — logique de résolution de rôle distincte pour le mode hors ligne
7. Le front (`ah2-admin-web/src/router/index.js`) — compare des rôles bruts sans normalisation, avec deux fautes de casse réelles constatées : `'assistant'` en minuscule dans les métadonnées de route (la base stocke `'Assistant'`, donc un compte Assistant connecté se voit refuser l'accès à la réception labo) et `'biologiste'`, un rôle qui n'existe dans aucune des 9 lignes de la base
8. `ah2-admin-web/src/components/users/UserModal.vue` — un 4ᵉ regroupement (`GROUP_MAPPING` : `app_admin`/`app_medical`/`app_secretaire`/`app_laborantin`), lié à la colonne `postgres_role`, utilisé uniquement pour filtrer le formulaire de création d'utilisateur

Découverte additionnelle : plusieurs `role_required("admin", "manager")` (création/modification/suppression d'utilisateurs dans `users_endpoint.py`) référencent un rôle `"manager"` absent des 9 lignes de la base. **Confirmé avec l'utilisateur : ce n'est pas un vestige** — `manager` est un rôle réel, prévu avec un niveau d'accès inférieur à `admin`, dont le câblage côté Python a commencé mais dont le reste (ligne en base, écran d'assignation) arrive dans une phase de développement ultérieure.

Découverte additionnelle : le compte `secretaire1` a un `role_id` NULL en base (vérifié par requête directe) — un compte cassé en silence.

## Décision de périmètre (validée avec l'utilisateur)

Ce chantier couvre **exclusivement le chemin web** : `role_map.py`, `get_current_user()`/`role_required()`, et le garde de navigation front. Il ferme `SEC-06` et `WEB-04`, les deux failles prouvées de l'audit initial.

**Explicitement hors périmètre**, documenté comme découvertes séparées à traiter plus tard :
- Mécanisme 5 (`patient_controller.py` / colonne `postgres_role`)
- Mécanisme 6 (mode hors ligne, `repo_offline/user_repo_offline.py`) — chemin sensible non exploré en détail ; son remplacement est de toute façon déjà prévu au chantier 4 (PowerSync)
- Mécanisme 8 (`UserModal.vue` / `GROUP_MAPPING`) — n'est pas un problème de sécurité, juste un regroupement UX indépendant ; laissé tel quel

## Détail des correctifs

### 1. Source de vérité canonique (`role_map.py`)

Les codes canoniques deviennent le strict équivalent en minuscules des 9 rôles réels de la table `application_roles` : `admin`, `medecin`, `nurse`, `secretaire`, `laborantin`, `psychologist`, `spiritualcounsellor`, `toxicomanager`, `assistant`. La base reste autoritaire sur l'orthographe — aucune nouvelle nomenclature n'est inventée, aucune migration de données sur les rôles existants n'est nécessaire.

`ROLE_ALIASES` s'enrichit d'alias lisibles pour les 4 nouveaux rôles issus de la base, sur le modèle des 5 existants :
- `psychologist` : `{"psychologist", "psychologue"}`
- `spiritualcounsellor` : `{"spiritualcounsellor", "spiritual_counsellor", "conseiller_spirituel", "conseiller spirituel"}`
- `toxicomanager` : `{"toxicomanager", "toxico_manager", "responsable_toxico"}`
- `assistant` : `{"assistant", "assistante"}`

S'y ajoute un **10ᵉ canonique réservé, `manager`**, sans ligne correspondante dans `application_roles` : la table de correspondance le reconnaît comme un rôle valide (accès de niveau inférieur à `admin`, prévu par l'utilisateur), mais aucune ligne en base ne le rend assignable pour l'instant — décision explicite pour ne pas anticiper sur un développement en cours côté produit. `role_required("admin", "manager")` redeviendra fonctionnel dès qu'une ligne `manager` existera en base et qu'un compte s'y verra assigné ; d'ici là, ces routes restent admin-only dans les faits, sans que le code mente sur l'intention.

Purement additif pour les 5 rôles déjà gérés aujourd'hui (`admin`, `medecin`, `nurse`, `secretaire`, `laborantin`) : ni code canonique ni comportement ne changent.

### 2. `SEC-06` — déjà fermé sur la version committée, risque résiduel identifié

Découverte en préparant le plan d'implémentation : la version **committée** (`HEAD`) de `get_current_user()` dans `auth_endpoints.py` n'a **pas** le repli permissif décrit par l'audit initial. Elle est déjà fail-closed (repli DB → repli token via `normalize_roles_list()` → liste vide). Le repli permissif lu lors de l'audit initial provenait de la **copie de travail non commitée** de l'utilisateur — une tentative locale de débloquer les comptes `Psychologist`/`Assistant`, non sécurisée, jamais commitée.

**Conséquence pour ce chantier** : aucune modification de `get_current_user()` n'est nécessaire. Le problème réel sur la version committée n'est pas un excès de permissivité mais l'inverse — les comptes `Psychologist`, `ToxicoManager`, `SpiritualCounsellor`, `Assistant` obtiennent aujourd'hui `roles = []` (verrouillés) car `role_map.py` ne les couvre pas. Le point 1 (extension de `role_map.py`) suffit à corriger ce verrouillage, sans toucher à la logique de `get_current_user()`.

**Risque résiduel signalé à l'utilisateur** : sa copie de travail contient toujours la version avec repli permissif. Si ce fichier est commité plus tard sans revoir ce point précis, la vulnérabilité reviendrait. Ce chantier touche bien `auth_endpoints.py` pour le point 3 ci-dessous (`role_required()`), mais laisse `get_current_user()` intact et isolé du reste du travail en cours (cf. contrainte d'isolation habituelle) ; le repli permissif de la copie de travail reste un point de vigilance pour l'utilisateur, pas une action de ce chantier.

### 3. Nettoyage de `role_required()`

Le repli `c = normalize_role_name(r) or r.strip().lower()` sur la liste des rôles **autorisés** (fournie par le code, pas par l'utilisateur) est retiré. Un rôle non reconnu passé à `role_required(...)` est désormais silencieusement ignoré plutôt que conservé tel quel en minuscules.

Grâce au canonique réservé `manager` ajouté au point 1, `role_required("admin", "manager")` continue de résoudre `"manager"` correctement (ce n'est plus un rôle "non reconnu" pour la table de correspondance) — son ensemble autorisé ne change donc pas. Le comportement observable reste identique à aujourd'hui (admin-only dans les faits, faute de compte `manager` existant), mais pour la bonne raison : le rôle est reconnu et simplement pas encore assigné, plutôt que silencieusement accepté sans jamais matcher personne.

### 4. Suppression du code mort

`api_backend/backend_app/routes/core/permissions.py` est supprimé. Zéro import ailleurs dans le dépôt (vérifié par recherche exhaustive). Il implémente un 3ᵉ système de rôles incompatible avec les deux autres ; même inatteignable, sa présence contredit l'objectif de source unique de vérité et créera de la confusion pour quiconque le découvrira plus tard.

### 5. Front — comparaison normalisée (`WEB-04`)

Dans `ah2-admin-web/src/router/index.js`, le garde de navigation (`router.beforeEach`) compare aujourd'hui `authStore.userRole` (casse exacte renvoyée par l'API, donc celle de la base) à des tableaux littéraux. Deux défauts corrigés :

- La comparaison `requiredRoles.includes(userRole)` devient insensible à la casse (les deux côtés normalisés en minuscules avant comparaison), pour que la classe entière de bug (nouvelle faute de frappe de casse à l'avenir) ne puisse plus se reproduire silencieusement.
- `'assistant'` (minuscule, ligne des routes labo réception) est corrigé en `'Assistant'` — ou devient sans objet une fois la comparaison insensible à la casse, mais corrigé quand même pour la lisibilité du code.
- `'biologiste'` est retiré des tableaux de rôles (labo dashboard, labo validation) : ce rôle n'existe dans aucune des 9 lignes de la base, sa présence est un vestige inerte et trompeur.

### 6. Correction du compte `secretaire1`

`UPDATE users SET role_id = (SELECT role_id FROM application_roles WHERE role_name = 'secretaire') WHERE username = 'secretaire1';` — décision confirmée avec l'utilisateur, cohérente avec le nom du compte.

Avec le fail-closed du point 2, ce compte serait sinon passé d'un comportement indéfini à un compte totalement bloqué (`roles = []`) sans message explicite — corriger la donnée avant que le fail-closed n'entre en vigueur évite de casser un compte réel au passage.

## Vérification

- Tests unitaires sur `normalize_role_name()` / `normalize_roles_list()` pour les 10 rôles canoniques (9 issus de la base + `manager` réservé) et leurs alias, y compris les 4 nouveaux issus de la base
- Vérification (sans modification de code) que `get_current_user()`, tel que committé, reste fail-closed après l'extension de `role_map.py` : un rôle DB toujours non couvert continuerait de produire `roles = []`, jamais un repli permissif
- Test que `role_required("admin", "manager")` reconnaît toujours `"manager"` comme rôle autorisé valide (pas de régression sur ce point précis, malgré le retrait du repli permissif)
- Vérification manuelle par connexion réelle : `kouam2` (Psychologist) et `thegoat` (Assistant), les deux comptes actifs déjà concernés par `SEC-06` dans l'audit, doivent conserver un accès fonctionnel identique après le durcissement
- Vérification manuelle que `secretaire1` peut se connecter et obtient les permissions du rôle secrétaire après la correction de données
- `npm run build` sur la console web après la correction du garde de navigation

## Risques et hypothèses

- Vérifié pendant la rédaction de cette spec (requête directe sur les 13 comptes actuels) : `secretaire1` est le seul compte dont le rôle ne résout vers aucun canonique. Les 12 autres résolvent tous correctement vers l'un des 9 rôles couverts. Le passage en fail-closed ne réserve donc aucune surprise au-delà du cas déjà traité au point 6.
- Les mécanismes 5, 6 et 8 (hors périmètre) continueront de fonctionner selon leur logique actuelle, potentiellement divergente de la nouvelle source de vérité du chemin web. Ce n'est pas une régression introduite par ce chantier — c'est l'état actuel, simplement non corrigé ici.
