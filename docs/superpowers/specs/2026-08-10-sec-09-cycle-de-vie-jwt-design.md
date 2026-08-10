# SEC-09 — Cycle de vie JWT et en-têtes de sécurité

**Date :** 2026-08-10
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** audit `SEC-09` ; suite des chantiers 0 et 1

## Contexte

L'audit initial regroupait sous `SEC-09` plusieurs manques sur le cycle de vie du JWT : absence de `jti`, absence de révocation, absence de validation `iss`/`aud`, absence d'en-têtes de sécurité HTTP, et `IS_PROD` défini dans `.env` mais jamais lu par le code. Ce chantier ferme `SEC-09`.

## Décisions validées avec l'utilisateur

1. **Stockage du token** : reste en `localStorage`, aucune migration vers un cookie `httpOnly`. Le chantier 4 (PowerSync) attend un token lisible côté JS pour l'injecter dans ses requêtes de synchronisation ; migrer vers un cookie compliquerait cette intégration future sans bénéfice proportionné pour un outil interne.
2. **Pas de refresh token** : un seul token, durée inchangée (`JWT_EXPIRE_MINUTES`, 120 min actuellement). Le vrai manque signalé par l'audit est l'absence de révocation, pas la durée de vie — c'est ce qui est corrigé, sans le coût d'un flux de renouvellement silencieux (nouvel endpoint, intercepteur axios, rotation).

## Découverte pendant le cadrage

`PUT /auth/password` (changement de mot de passe) — la route, `UserPasswordUpdate`, et `AuthController.change_user_password()` — **n'existe sur aucun des trois fichiers concernés sur `HEAD`**. C'est un travail en cours entier, non commité (`auth_endpoints.py`, `schemas.py`, `controller/auth_controller.py`). Conséquence : la révocation au changement de mot de passe ne peut pas être livrée dans ce chantier sans committer du code qui n'appartient pas à ce chantier. Voir section "Hors périmètre".

## Détail des correctifs

### 1. Révocation via `token_version`

Nouvelle colonne `token_version` (entier, `NOT NULL DEFAULT 0`) sur `users`. Ajoutée par SQL direct (pas d'Alembic pour l'instant — argument de plus pour le chantier 2 juste après) :

```sql
ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0;
```

`models/user.py` (fichier propre, aucun travail en cours dessus) reçoit le champ SQLAlchemy correspondant.

Le JWT embarque désormais `ver` = `token_version` de l'utilisateur au moment de l'émission (`login()`). `get_current_user()` compare cette valeur à `token_version` tel que lu en base à chaque requête ; en cas de désaccord → `401`, session invalidée.

**Nouvelle route `POST /auth/logout`** (authentifiée) : incrémente `token_version` de l'utilisateur courant en base. Conséquence : tous les jetons déjà émis pour ce compte deviennent invalides immédiatement, y compris ceux ouverts sur d'autres appareils/onglets. C'est une révocation globale par compte (pas par jeton individuel) — plus simple qu'une liste de révocation par `jti`, suffisant pour le besoin réel identifié par l'audit (« pouvoir forcer une déconnexion »).

### 2. Hygiène du jeton

Le payload du JWT gagne :
- `jti` : `uuid4().hex`, identifiant unique du jeton, pour la traçabilité (logs, audit) — pas utilisé pour la révocation elle-même, qui repose sur `token_version`
- `iss` : `"ah2-api"`
- `aud` : `"ah2-web"`

`get_current_user()` valide `iss`/`aud` nativement via les paramètres `issuer=` et `audience=` de `jose_jwt.decode()`, plutôt qu'une vérification manuelle après coup.

L'algorithme de signature était déjà correctement restreint (`algorithms=[JWT_ALGORITHM]` dans `jose_jwt.decode()`) — aucun changement nécessaire sur ce point, contrairement à ce que l'audit initial suggérait.

### 3. Front — déconnexion réelle

`ah2-admin-web/src/stores/auth.js`, action `logout()` (fichier propre, aucun travail en cours dessus) : appelle `POST /auth/logout` avant de nettoyer `localStorage`, en best-effort (si l'appel échoue — token déjà expiré, réseau coupé — le nettoyage local et la redirection ont quand même lieu, pour ne jamais bloquer un utilisateur qui veut se déconnecter).

### 4. En-têtes de sécurité

Middleware Starlette ajouté dans `main.py`, posant sur chaque réponse :
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=63072000; includeSubDomains` — **uniquement si `IS_PROD` est vrai** (l'en-tête n'a pas de sens et peut induire en erreur en HTTP local)

Le CSP (`Content-Security-Policy`) est **délibérément exclu** de ce chantier : un CSP mal calibré casse silencieusement une SPA (scripts/styles/images bloqués sans erreur visible côté utilisateur). Il mérite un audit dédié des origines de ressources chargées par la console Vue — noté comme découverte pour un chantier futur, pas traité ici.

### 5. Câblage de `IS_PROD`

`api_backend/backend_app/config.py` (fichier propre) expose `IS_PROD = os.getenv("IS_PROD", "false").lower() == "true"`, consommé uniquement par le middleware d'en-têtes du point 4 pour cette itération.

## Hors périmètre (découvertes, pas traitées ici)

- **Révocation au changement de mot de passe** : `PUT /auth/password` n'existe pas sur `HEAD` (travail en cours non commité). Recommandation pour l'utilisateur : quand cette fonctionnalité sera commitée, ajouter un incrément de `token_version` dans `change_user_password()`, suivant exactement le même mécanisme que `POST /auth/logout` de ce chantier.
- **Content-Security-Policy** : nécessite un audit des ressources chargées par `ah2-admin-web` avant calibration, pour ne pas casser l'application.
- **Révocation par jeton individuel** (liste de révocation par `jti`) : la révocation par `token_version` couvre le besoin réel (forcer une déconnexion globale) avec beaucoup moins de complexité (pas de table de révocation à interroger à chaque requête). Une granularité plus fine n'a pas été demandée et ajouterait une dépendance (Redis ou table dédiée) pour un bénéfice non requis à ce stade.

## Vérification

- Test unitaire : un jeton signé avec un `ver` différent du `token_version` courant en base est rejeté par `get_current_user()`
- Test unitaire : un jeton avec `iss`/`aud` incorrects est rejeté
- Vérification manuelle : connexion, appel `POST /auth/logout`, nouvel appel avec l'ancien jeton → `401`
- Vérification manuelle : `curl -I` sur une route quelconque confirme la présence des en-têtes `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, et l'absence de `Strict-Transport-Security` en local (`IS_PROD` non positionné à `true` en développement)
- `npm run build` sur la console web après la modification de `stores/auth.js`

## Risques et hypothèses

- La migration SQL directe (`ALTER TABLE`) doit être appliquée manuellement sur chaque environnement (dev local maintenant, tout autre environnement plus tard) tant qu'Alembic n'existe pas — risque de dérive de schéma entre environnements, atténué par le fait qu'il n'y a aujourd'hui qu'un seul environnement actif (dev local).
- La révocation globale par compte (et non par jeton) signifie qu'un `POST /auth/logout` déconnecte aussi les autres sessions actives du même utilisateur sur d'autres appareils. Comportement jugé acceptable et même souhaitable pour un outil de gestion hospitalière (pas de cas d'usage identifié nécessitant des sessions multiples indépendantes non révocables ensemble).
