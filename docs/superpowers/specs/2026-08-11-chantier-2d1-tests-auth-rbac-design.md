# Chantier 2d-1 — Tests d'intégration auth + RBAC

**Date :** 2026-08-11
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** premier sous-chantier métier de 2d, construit sur l'infrastructure livrée en 2d-0

## Contexte

2d-0 a livré une fixture `db_session` (transaction externe + SAVEPOINT auto-relancée) et un helper `override_get_db()`, vérifiés mais non encore utilisés pour tester une vraie fonctionnalité. 2d-1 est le premier sous-chantier métier : il couvre le chemin d'authentification (`POST /auth/login`, `GET /auth/me`, `POST /auth/logout`) et le contrôle d'accès par rôle (`role_required()`), en s'appuyant sur de vraies requêtes HTTP (`TestClient`) et la base `AH2` réelle.

C'est aussi le chantier qui valide concrètement le cycle de vie JWT ajouté en SEC-09 (révocation via `token_version`, `iss`/`aud`, expiration) — jusqu'ici uniquement vérifié manuellement ou par des tests unitaires avec mocks.

## Décisions validées avec l'utilisateur

1. **Comptes de test éphémères**, créés par chaque test dans la transaction annulée par `db_session` — jamais de dépendance aux comptes seedés existants (`admin_test`, `nurse_test`, etc.) ni à leurs mots de passe, potentiellement rotés depuis le chantier 0 (`SEC-04`).
2. **Couverture complète** : login (succès/échecs), cycle de vie du token (expiration, signature invalide, révocation), RBAC positif/négatif sur une vraie route protégée.

## Découvertes pendant le cadrage

1. **Comptes seedés existants** (`admin_test`, `bonne`, `kouam2`, `labotest`, `Letto`, `Med2`, `Med3`, `nurse_test`, `secretaire0-3`, `thegoat`) confirment que les rôles `admin` et `secretaire` sont déjà seedés en base avec un `role_name` en minuscules, strictement aligné sur les canoniques de `role_map.py` — aucune ambiguïté de casse pour ces deux rôles précisément.
2. **Le trigger `create_metier_profile()`** (rendu idempotent en A2) se déclenche à l'insertion d'un `User` et route vers `admin`/`secretaire`/`medecin`/`nurse`/`laborantin` selon `role_id`. Créer un utilisateur éphémère avec `role_id` pointant vers le rôle `admin` ou `secretaire` déjà seedé fonctionne donc sans modification du trigger, et reste sans effet observable hors de la transaction du test (rollback).
3. **`GET /admin/users/` exige un double `override_get_db`** : `role_required()` dépend de `get_current_user()`, défini dans `auth_endpoints.py` (son propre `get_db`) ; `get_user_controller()` dans `users_endpoint.py` dépend d'un second `get_db`, défini dans ce même fichier. Sans surcharger les deux, une des deux dépendances utiliserait une session réelle (`SessionLocal()`) hors transaction de test. Confirme concrètement le besoin `ARC-05` déjà noté au registre (`SUIVI-AVANCEMENT.md`).
4. **`POST /auth/login` est limité à 5/minute** (`slowapi`, chantier 0 `SEC-05`). `TestClient` envoie toutes ses requêtes avec la même adresse cliente (`testclient`) — sans réinitialisation, la suite de tests finirait par se faire bloquer elle-même par sa propre limite de débit. `slowapi.Limiter` expose `.reset()` pour vider son stockage en mémoire.
5. **Le message d'échec de connexion est volontairement générique** (`authenticate()` retourne `None` aussi bien pour mot de passe erroné que pour compte inactif ou utilisateur inconnu — même réponse 401 "Identifiants invalides" dans les trois cas). Comportement existant, non modifié par ce chantier — les tests le documentent tel quel plutôt que d'exiger une différenciation.

## Détail de l'implémentation

### 1. Factory de compte de test (ajout à `tests/conftest.py`)

```python
def create_test_user(session, username, role_name, password="TestPass123!", is_active=True):
    role = session.query(ApplicationRole).filter_by(role_name=role_name).one()
    user = User(
        username=username,
        password_hash=pwd_context.hash(password),
        full_name=f"Test {username}",
        role_id=role.role_id,
        is_active=is_active,
    )
    session.add(user)
    session.flush()  # obtient user_id, déclenche le trigger create_metier_profile(), sans commit
    return user
```

`session.flush()` (pas `commit()`) suffit : la route `/auth/login` lit l'utilisateur via la même connexion transactionnelle (session surchargée via `override_get_db`), donc la ligne non commitée est visible. Réutilisable tel quel par 2d-2 à 2d-4.

### 2. Réinitialisation du rate limiter (fixture `autouse` dans `tests/conftest.py`)

```python
@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield
```

Placée dans `conftest.py` (portée globale) plutôt que localisée à `test_auth_login.py`, pour que les sous-chantiers suivants qui appelleraient `/auth/login` n'aient pas à s'en soucier.

### 3. `tests/test_auth_login.py`

- `test_login_success_returns_token_with_correct_role` — utilisateur `admin` actif, mot de passe correct → 200, `access_token` présent, décodage du JWT confirme `roles: ["admin"]`.
- `test_login_wrong_password_returns_401` — mot de passe incorrect → 401 "Identifiants invalides".
- `test_login_inactive_account_returns_401` — `is_active=False` → 401 "Identifiants invalides" (même message que ci-dessus, comportement existant).
- `test_login_unknown_username_returns_401` — nom d'utilisateur inexistant → 401 "Identifiants invalides".

### 4. `tests/test_auth_token_lifecycle.py`

- `test_valid_token_allows_access_to_me_endpoint` — login réel → `GET /auth/me` avec le token obtenu → 200, `role_name` cohérent.
- `test_expired_token_returns_401` — token forgé directement (`jose_jwt.encode` avec `exp` dans le passé, même `JWT_SECRET`/`JWT_ALGORITHM`/`iss`/`aud` que l'app) → `GET /auth/me` → 401 "Token expiré".
- `test_tampered_signature_returns_401` — token forgé avec un secret différent → 401 "Token invalide ou expiré".
- `test_logout_revokes_current_token` — login → `POST /auth/logout` avec le token (succède, incrémente `token_version`) → réutilisation du **même** token sur `GET /auth/me` → 401 "Session invalidée, veuillez vous reconnecter".

### 5. `tests/test_rbac.py`

Cible : `GET /admin/users/` (`role_required("admin", "manager")`, durci au chantier 0 pour restreindre la lecture des comptes — `SEC-07`).

- `test_admin_role_can_list_users` — utilisateur `admin` → 200.
- `test_secretaire_role_forbidden_from_admin_route` — utilisateur `secretaire` (rôle valide mais non autorisé sur cette route) → 403 "Accès refusé : rôle utilisateur insuffisant".
- `test_unauthenticated_request_returns_401` — aucun header `Authorization` → 401.

Chaque test de ce fichier surcharge **les deux** modules (`auth_endpoints`, `users_endpoint`) via `override_get_db()`.

## Vérification

- Les 11 tests neufs passent (`pytest tests/test_auth_login.py tests/test_auth_token_lifecycle.py tests/test_rbac.py -v`)
- Aucune régression sur la suite existante (`pytest tests/ -v`) — mêmes 4 échecs pré-existants, sans lien
- Aucune donnée résiduelle dans `AH2` après la suite (comptage sur `users` filtré par les noms d'utilisateurs de test, avant/après)

## Hors périmètre

- Les autres routes protégées par `role_required()` (caisse, labo, toxico, etc.) — RBAC est testé une fois, en profondeur, sur une route représentative ; les 2d-2 à 2d-4 ne re-testent pas le mécanisme lui-même, seulement la logique métier de leurs domaines respectifs (déjà noté dans la spec 2d-0, section 3)
- La consolidation des 14 `get_db()` (`ARC-05`) — resterait un chantier de refactoring séparé
- Le test de la limite de débit elle-même (5/minute) — hors périmètre RBAC/auth fonctionnel, et risquerait de rendre la suite fragile (dépendante du timing)
