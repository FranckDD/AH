# Chantier 2d-0 — Infrastructure de test d'intégration

**Date :** 2026-08-11
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** audit (tests des chemins critiques) ; fondation des sous-chantiers 2d-1 à 2d-4

## Contexte

Le chantier 2d (« tests des chemins critiques : auth, RBAC, patients, prescriptions, caisse ») ne peut pas commencer sans une fixture de base de données fiable. Les tests actuels (chantiers 0, 1, SEC-09, 2e) utilisent tous des mocks (`MagicMock`) — utile pour vérifier une logique isolée, mais incapable de détecter des bugs réels de mapping SQLAlchemy, de contraintes de base, ou de comportement RBAC bout-en-bout via de vraies requêtes HTTP. C'est précisément ce que 2d vise à couvrir.

**Décision validée avec l'utilisateur** : les tests d'intégration utilisent la base `AH2` locale réelle (pas de base dédiée `AH2_test`), avec annulation de transaction après chaque test. Les données actuellement présentes en base sont des données de test, pas des données de production — le risque d'une fixture imparfaite est donc limité, mais elle doit tout de même être correcte et vérifiée avant d'être utilisée pour écrire de vrais tests métier.

## Découvertes pendant le cadrage

1. **14 fonctions `get_db()` distinctes**, une par module de routes (`ARC-05`, déjà connu). `app.dependency_overrides` de FastAPI indexe sur l'objet fonction exact — il n'existe pas de point d'interception unique. Chaque fichier de test devra surcharger précisément les `get_db` des modules qu'il exerce.
2. **La migration baseline d'Alembic (chantier 2a) ne peut pas amorcer une base vide** : son `upgrade()` contient des `op.drop_table(...)` pour 17 tables supposées déjà présentes — échouerait sur une base neuve. Sans objet ici puisqu'on utilise la base réelle existante, mais à retenir si une base de test dédiée est envisagée plus tard.
3. **Plusieurs contrôleurs appellent `self.session.commit()` en interne** (ex. `sync_simple_patient_creation`). Une transaction de test naïve (`session.begin()` + `rollback()` en fin de test) serait invalidée dès le premier `commit()` intermédiaire — le rollback final n'annulerait alors plus rien. Le pattern SQLAlchemy standard pour ce cas (« rejoindre une transaction externe », documenté officiellement) doit être utilisé : une transaction externe sur la connexion, une SAVEPOINT imbriquée relancée automatiquement à chaque fin de transaction interne, annulée uniquement au niveau externe en fin de test.

## Détail de l'implémentation

### 1. Fixture de session transactionnelle (`tests/conftest.py`)

Pattern SQLAlchemy 2.0 « rejoindre une transaction externe », **vérifié empiriquement contre la base locale réelle** pendant le cadrage (insertion + `commit()` interne simulé + rollback externe + vérification depuis une connexion séparée — confirmé qu'aucune donnée ne survit) :

```python
@pytest.fixture
def db_session():
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()
```

Point clé : la SAVEPOINT imbriquée (`nested`) est ouverte et relancée au niveau de la **connexion**, pas de la session — c'est ce qui permet au rollback externe d'annuler même les `commit()` internes des contrôleurs (`sync_simple_patient_creation` et consorts), déjà vérifié pendant le cadrage.

`engine` importé directement depuis `api_backend.backend_app.database` (même connexion que l'application réelle, pas de configuration dupliquée).

### 2. Helper de surcharge par module

```python
def override_get_db(app, module, session):
    app.dependency_overrides[module.get_db] = lambda: session
```

Usage dans un test : `override_get_db(app, patients_endpoints, db_session)`.

### 3. Fixture client HTTP

`TestClient(app)` standard, réutilisable. Pas de surcharge globale de `get_current_user` — chaque sous-chantier (2d-1 à 2d-4) décide s'il exerce le flux d'authentification réel (2d-1, par construction) ou surcharge l'identité pour se concentrer sur la logique métier (2d-2 à 2d-4, avec une note explicite justifiant pourquoi RBAC n'est pas re-testé à chaque fois — déjà couvert par 2d-1).

### 4. Méta-test de validation du rollback

Avant tout test métier construit sur cette fixture, un test dédié vérifie que la fixture elle-même fonctionne :
- Insère une ligne via `db_session` (par exemple dans une table sans contrainte gênante)
- Simule un `commit()` interne (comme le ferait un contrôleur) suivi d'une autre insertion
- Après la fin du test (fixture nettoyée), une connexion **complètement séparée** interroge la base et confirme qu'aucune des deux lignes n'est présente

## Vérification

- Le méta-test de rollback passe, y compris dans le cas d'un `commit()` intermédiaire simulé
- Un test simple utilisant `override_get_db` sur un module réel (par exemple `health_endpoint` ou un `GET` simple) confirme que la substitution fonctionne bout-en-bout via `TestClient`
- Aucune donnée résiduelle dans `AH2` après exécution de la suite de tests (vérifié par un comptage de lignes avant/après sur une table de test)

## Hors périmètre

- Les tests métier eux-mêmes (2d-1 à 2d-4) — cette fondation seule ne teste rien de fonctionnel
- Une base de données de test dédiée (`AH2_test`) — décision explicite de l'utilisateur de rester sur `AH2`
- La consolidation des 14 `get_db()` en un point unique (`ARC-05`) — resterait un chantier de refactoring séparé, pas nécessaire pour que les tests fonctionnent
