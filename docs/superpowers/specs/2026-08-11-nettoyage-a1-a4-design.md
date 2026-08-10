# Nettoyage A1-A4 — corrections issues du registre de découvertes

**Date :** 2026-08-11
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** registre de découvertes compilé depuis les chantiers 0, 1, SEC-09, 2a

## Contexte

Plusieurs découvertes faites pendant les chantiers précédents ont été documentées comme « hors périmètre » sans être corrigées, faute de lien direct avec le chantier en cours à ce moment-là. Ce mini-chantier traite les 4 découvertes qui ne dépendent d'aucun travail en cours de l'utilisateur ni d'une décision produit préalable (catégorie A du registre) :

- **A1** — `datetime.utcnow().timestamp()` dans `login()` raccourcit la durée de vie réelle du token (découvert au chantier 1)
- **A2** — trigger `create_metier_profile()` non idempotent, plante sur tout compte ayant déjà un profil métier (découvert au chantier 1, contourné à l'époque sans corriger la cause)
- **A3** — 17 tables réelles sans modèle SQLAlchemy, candidates à la suppression dans toute future autogénération Alembic (découvert au chantier 2a)
- **A4** — CSP absent (identifié dès SEC-09, différé faute d'audit des ressources)

## Détail des correctifs

### A1 — Fuseau horaire du JWT

`datetime.datetime.utcnow()` retourne un datetime **naïf** (sans fuseau) représentant l'heure UTC, mais `.timestamp()` appelé sur un datetime naïf l'interprète comme heure **locale**. Sur cette machine (UTC+1), l'expiration calculée est donc ~1h plus tôt que prévu par rapport à l'heure UTC réelle.

Remplacer, dans `login()` (`api_backend/backend_app/routes/auth/auth_endpoints.py`) :
```python
expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)
```
par :
```python
expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES)
```
`datetime.now(timezone.utc)` est conscient du fuseau ; `.timestamp()` produit alors le bon epoch quel que soit le fuseau du serveur.

### A2 — Trigger `create_metier_profile()` idempotent

Ajout de `ON CONFLICT (user_id) DO NOTHING` aux 5 `INSERT` de la fonction (doctor/nurse/secretaire/admin/laborantin), pour qu'un changement de rôle vers une valeur déjà pourvue d'un profil ne fasse plus échouer la requête entière.

Appliqué via une **migration Alembic** (`op.execute(CREATE OR REPLACE FUNCTION ...)`) plutôt qu'un SQL direct — première utilisation réelle du tooling mis en place au chantier 2a, cohérent avec son objectif.

### A3 — Exclure les 17 tables non modélisées de l'autogénération

Ajout d'un hook `include_object` dans `alembic/env.py`, listant explicitement les 17 tables sans modèle (`admin`, `doctor`, `nurse`, `secretaire`, `laborantin`, `audit_logs`, `audit_user_actions_old`, `audit_access_old`, `permissions`, `role_permissions`, `motif_translations`, `spiritual_sessions`, `spiritual_attendance`, `admissions`, `psych_evaluations`, `patient_contacts`, `lab_results_audit`) et les excluant de la comparaison modèles/base. Elles ne seront plus jamais proposées à la suppression tant qu'elles n'auront pas de modèle SQLAlchemy — sans qu'il soit nécessaire d'en écrire un pour chacune dans ce chantier.

### A4 — Content-Security-Policy

Ajout au middleware d'en-têtes de sécurité existant (`main.py`, chantier SEC-09) :
```
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
img-src 'self' data: https://*.supabase.co;
connect-src 'self' http://localhost:8000 http://127.0.0.1:8000;
```

Justifié par l'inventaire réel des ressources chargées (vérifié pendant le cadrage) : aucun CDN externe, aucune police externe, un seul domaine d'API. `style-src 'unsafe-inline'` est nécessaire — Vue utilise massivement les liaisons `:style` (attributs inline), bloquées par défaut sans cette directive. `img-src` inclut Supabase par anticipation (stockage non encore configuré, mais l'intention existe dans le code — `ToxicoPatientDetailsModal.vue` gère déjà le cas d'URLs Supabase complètes).

## Vérification

- A1 : décoder un token émis après le correctif, vérifier que `exp - iat` correspond exactement à `JWT_EXPIRE_MINUTES` (à la seconde près), quel que soit le fuseau du serveur
- A2 : changer le rôle d'un compte déjà pourvu d'un profil métier (via l'API, pas en contournant le trigger comme au chantier 1) ne lève plus d'erreur
- A3 : `alembic revision --autogenerate` à blanc ne propose plus la suppression des 17 tables listées
- A4 : build de la console web, puis **usage réel dans un navigateur** (pas seulement `curl -I`) — se connecter, naviguer dans plusieurs modules, confirmer l'absence d'erreurs CSP dans la console développeur. **Non réalisable dans cet environnement** (voir Notes post-implémentation) — remplacé par une analyse statique du bundle buildé.

## Hors périmètre

- Écrire des modèles SQLAlchemy pour les 17 tables (A3 ne fait qu'empêcher leur suppression accidentelle, pas les rendre gérables par l'ORM)
- Durcissement CSP plus strict (nonces, `strict-dynamic`) — la politique actuelle est un point de départ pragmatique, pas une fin en soi

## Notes post-implémentation

- **A4 — aucun outil de navigateur disponible dans cet environnement d'exécution** : ni navigateur automatisé (Playwright/Puppeteer), ni accès à `localhost` depuis l'outil de récupération web disponible (`WebFetch` échoue en `ECONNREFUSED` sur une IP locale — c'est un service distant, pas un navigateur local). La vérification prévue dans la spec (usage réel en navigateur, plusieurs modules, console développeur) **n'a pas pu être réalisée**. Remplacée par une analyse statique du bundle de production (`dist/assets/*.js`, `dist/index.html`), qui a effectivement trouvé deux violations réelles qu'un `curl -I` n'aurait jamais révélées :
  - `vue-i18n` compile les messages traduits via `new Function()` à l'exécution (pas de précompilation au build) → `script-src` sans `'unsafe-eval'` aurait cassé toute traduction. Ajouté.
  - `SystemConfig.vue` prévisualise le logo avant envoi via `URL.createObjectURL(file)` affiché en `<img>` → `img-src` sans `blob:` aurait cassé cette prévisualisation. Ajouté.
  - Vérifiés sans trouver de problème : pas d'`<iframe>`, pas de WebSocket, pas d'appel direct à Supabase depuis le front, pas de police embarquée, pas de domaine externe référencé dans les bundles.
  - **Ce que l'analyse statique ne peut pas garantir** : le comportement à l'exécution dans un vrai navigateur (erreurs de timing, ressources chargées conditionnellement selon les données, extensions navigateur, etc.). Un utilisateur avec accès à un navigateur devrait faire un tour rapide de l'application (connexion, 2-3 modules) et vérifier l'onglet Console (F12) pour des messages `Refused to ... because it violates the following Content Security Policy directive` avant de considérer A4 définitivement clos.
