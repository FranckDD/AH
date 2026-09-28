# Chantier 5 — Fiabiliser les données affichées : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire en sorte que tout chiffre, compteur et liste affichés par AH2 corresponde à la réalité de la base — ou signale explicitement son indisponibilité.

**Architecture:** Aucune fonctionnalité nouvelle, sauf un endpoint de journal financier unifié qui remplace une fusion client incorrecte. Partout ailleurs, on applique la convention déjà correcte présente à côté du code fautif (enveloppe paginée `_list_by_flag`, `Promise.allSettled` de `secretariatHomeStore`). Chaque défaut est d'abord reproduit par un test qui échoue.

**Tech Stack:** FastAPI + SQLAlchemy 2.x + PostgreSQL 17 · Vue 3 (Composition API) + Pinia + Vite · pytest avec fixtures transactionnelles contre la base `AH2` réelle.

**Spec:** `docs/superpowers/specs/2026-09-15-chantier-5-fiabilite-donnees-design.md`

## Global Constraints

- **Aucun commit git.** Règle permanente de ce projet : ne jamais commiter sans accord explicite et frais de l'utilisateur. Les étapes « Commit » du gabarit habituel sont remplacées par une consignation dans le ledger d'exécution. Ne jamais utiliser `git add -A`.
- **Aucune migration de base, aucun DDL.** Ce chantier ne modifie pas le schéma. Si une tâche semble en exiger une, s'arrêter et remonter la question.
- **Caractérisation avant modification** : pour chaque défaut, écrire d'abord un test qui échoue en décrivant le comportement erroné, puis corriger, puis vérifier qu'il passe.
- **Suivre la convention correcte déjà présente** dans le fichier ou le module concerné plutôt que d'inventer. Elle est nommée explicitement dans chaque tâche.
- **Un chiffre indisponible ne s'affiche jamais comme `0`** — il s'affiche comme indisponible.
- **Ne pas casser les appelants existants** : si un type déclaré est malhonnête mais qu'un appelant en dépend, corriger le sens sans changer le contrat, et le noter.
- **Le filtre par rôle de la liste patients reste inerte.** Il est conservé tel quel, non activé — c'est un livrable du chantier 6. Ne pas le « réparer » en passant (registre `B6`).
- **Redémarrage backend** : `uvicorn --reload` ne surveille que `api_backend/`. Toute modification dans `repositories/` ou `controller/` exige un redémarrage manuel du processus pour être prise en compte. En tenir compte avant de conclure qu'un correctif ne marche pas.
- **Limite de connexions** : `/auth/login` est limité à 5 requêtes/minute (`auth_endpoints.py:33`). En test, la fixture autouse `reset_rate_limiter` s'en charge ; en vérification manuelle par `curl`, espacer les connexions.
- **Tests** : `pytest` depuis la racine du dépôt. Les fixtures et fabriques sont dans `tests/conftest.py` — `db_session`, `api_client(*modules)`, `auth_headers(client, user, pwd)`, `create_test_user`, `create_test_patient`, `create_test_transaction`, `create_test_retrait`. Ne pas en créer de nouvelles sans nécessité.
- **Aucun passage hors ligne dans ce chantier.** Synchroniser des compteurs faux n'aurait aucun sens ; le hors-ligne est intégré en fin des chantiers 6 et 7, module par module. Si une tâche semble en appeler, c'est une erreur de lecture du périmètre.
- **9 échecs de tests pré-existants** sont documentés et sans rapport avec ce chantier (couplage caisse/patients/prescriptions). Ne pas chercher à les corriger ; vérifier seulement qu'aucun échec nouveau n'apparaît.

---

## Structure des fichiers

**Créés**
- `repositories/finance_ledger_repo.py` — accès au journal financier unifié (union recettes + dépenses). Responsabilité unique : construire, filtrer, trier et paginer le flux de mouvements. Placé dans un fichier propre plutôt qu'ajouté à `caisse_repo.py`, déjà long et centré sur une seule table.
- `api_backend/backend_app/routes/finance/__init__.py` et `finance_endpoints.py` — routeur `/finance`, exposant le journal unifié. Distinct de `/caisse` et `/retrait`, qui restent des vues par table.
- `tests/test_finance_ledger.py`, `tests/test_patients_pagination.py`, `tests/test_users_pagination.py`, `tests/test_cs_pagination.py` — tests de caractérisation par défaut traité.

**Modifiés (backend)**
- `repositories/patient_repo.py` — `list_patients` renvoie l'enveloppe paginée
- `api_backend/backend_app/routes/patients/patients_endpoints.py` — `response_model`
- `controller/user_controller.py` + `api_backend/backend_app/routes/admin/users_endpoint.py` — enveloppe paginée et recherche paginée
- `api_backend/backend_app/routes/cs/cs_endpoint.py` — enveloppe paginée (le total exact est déjà disponible)
- `repositories/caisse_repo.py` — périmètre de la recherche
- `api_backend/backend_app/routes/toxico/toxico_schema.py` + `controller/toxico_controller.py` — date d'admission dans la liste
- `api_backend/backend_app/main.py` — enregistrement du routeur `/finance`

**Modifiés (frontend)**
- `ah2-admin-web/src/services/FinanceGateway.js` — appel du journal unifié
- `ah2-admin-web/src/stores/financialStore.js` — suppression de la fusion client
- `ah2-admin-web/src/stores/dashboardStore.js` — tolérance aux pannes
- `ah2-admin-web/src/stores/secretariatHomeStore.js` — compteur consultations
- `ah2-admin-web/src/stores/configStore.js` — distinction des états d'échec
- `ah2-admin-web/src/stores/labStore.js` — suppression du code mort
- `ah2-admin-web/src/views/dashboards/DashboardOverview.vue` — affichage « indisponible »

---

## Task 1 : Liste patients paginée (registre L1d)

**Files:**
- Modify: `repositories/patient_repo.py:236-263` (`list_patients`)
- Modify: `api_backend/backend_app/routes/patients/patients_endpoints.py:66-74` (`list_patients`)
- Test: `tests/test_patients_pagination.py` (créer)

**Interfaces:**
- Consomme : `PatientListResponse` (`patients_schemas.py:168`) — `{data, total, page, per_page, total_pages}`, déjà défini, ne pas le modifier.
- Produit : `PatientRepository.list_patients(page, per_page, search, filters) -> Dict[str, Any]` avec les clés `data`, `total`, `page`, `per_page`, `total_pages`. La tâche 5 n'en dépend pas ; aucune autre tâche ne consomme cette signature.

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `tests/test_patients_pagination.py` :

```python
from api_backend.backend_app.routes.patients import patients_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_patient


def test_liste_patients_renvoie_enveloppe_paginee(db_session, api_client):
    """GET /patients/ doit renvoyer {data,total,page,per_page,total_pages},
    comme le font deja /patients/clinical, /toxicology et /spiritual/list.
    Avant correction : renvoie une liste nue, donc le client ne connait
    jamais le nombre total et bloque la pagination sur une seule page."""
    admin = create_test_user(db_session, "pagin_admin", "admin")
    for i in range(3):
        create_test_patient(db_session, admin, first_name=f"Pagin{i}")
    db_session.flush()

    client = api_client(patients_endpoints)
    headers = auth_headers(client, "pagin_admin", "TestPass123!")

    reponse = client.get("/patients/?page=1&per_page=2", headers=headers)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert isinstance(corps, dict), "une liste nue ne permet pas de paginer"
    assert set(corps) >= {"data", "total", "page", "per_page", "total_pages"}
    assert len(corps["data"]) == 2
    assert corps["total"] >= 3
    assert corps["total_pages"] >= 2
    assert corps["page"] == 1
    assert corps["per_page"] == 2
```

- [ ] **Step 2 : Lancer le test pour le voir échouer**

Run : `pytest tests/test_patients_pagination.py -v`
Attendu : ÉCHEC sur `assert isinstance(corps, dict)` — la réponse est une liste.

- [ ] **Step 3 : Faire renvoyer l'enveloppe par le dépôt**

Dans `repositories/patient_repo.py`, remplacer la dernière ligne de `list_patients` (`return query.offset(...).limit(per_page).all()`) par le même calcul que `_list_by_flag` (`patient_repo.py:299-312`) :

```python
        # Total calcule AVANT pagination - meme convention que _list_by_flag,
        # dont depend deja la pagination des trois onglets typees.
        total_count = query.count()

        query = query.order_by(Patient.last_updated_at.desc())
        items = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "data": items,
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page if per_page > 0 else 1
        }
```

Supprimer la ligne `query = query.order_by(Patient.last_updated_at.desc())` qui précédait l'ancien `return`, pour ne pas l'appliquer deux fois.

- [ ] **Step 4 : Adapter l'endpoint**

Dans `patients_endpoints.py`, remplacer la déclaration et le corps de `list_patients` :

```python
@router.get("/", response_model=PatientListResponse)
def list_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str = Query(None),
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    resultat = patient_ctrl.list_patients(page=page, per_page=per_page, search=search)
    return {
        **resultat,
        "data": [_safe_validate_patient(p) for p in resultat["data"]],
    }
```

Vérifier que `PatientListResponse` figure bien dans les imports du fichier ; l'ajouter à l'import existant depuis `.patients_schemas` si absent.

- [ ] **Step 5 : Vérifier que le test passe**

Run : `pytest tests/test_patients_pagination.py -v`
Attendu : SUCCÈS.

- [ ] **Step 6 : Vérifier qu'aucun appelant n'est cassé**

Run : `pytest tests/test_patients.py tests/test_patient_repo.py -v`
Attendu : aucun échec nouveau par rapport à la référence.

Côté client, aucune modification n'est nécessaire : `patientStore.js:90-99` sait déjà lire cette enveloppe — c'est la branche qu'il emprunte pour les trois autres onglets. Le vérifier en lisant le code, sans le modifier.

- [ ] **Step 7 : Consigner**

Ajouter au ledger d'exécution : tâche 1 terminée, `L1d` résolu, avec le résultat du test. **Ne pas commiter.**

---

## Task 2 : Liste utilisateurs paginée et recherche paginée (registre L1f + L1h)

**Files:**
- Modify: `controller/user_controller.py` (`list_users`, `search_users`)
- Modify: `api_backend/backend_app/routes/admin/users_endpoint.py:71-85` (`list_users`)
- Modify: `api_backend/backend_app/routes/admin/users_schemas.py` (ajout du schéma d'enveloppe)
- Test: `tests/test_users_pagination.py` (créer)

**Interfaces:**
- Produit : `GET /users/` renvoie `UserListResponse` — `{data: List[UserOut], total: int, page: int, per_page: int, total_pages: int}`. La tâche 5 consomme `total` depuis cette réponse.

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `tests/test_users_pagination.py` :

```python
from api_backend.backend_app.routes.admin import users_endpoint
from api_backend.backend_app.routes.auth import auth_endpoints
from tests.conftest import auth_headers, create_test_user


def test_liste_utilisateurs_renvoie_le_total(db_session, api_client):
    """GET /users/ doit exposer le nombre total de comptes : le tableau de
    bord admin lit ce champ. Avant correction, la reponse est une liste nue,
    donc 'Utilisateurs inscrits' affiche toujours 0."""
    create_test_user(db_session, "pagin_users_admin", "admin")
    db_session.flush()

    client = api_client(users_endpoint, auth_endpoints)
    headers = auth_headers(client, "pagin_users_admin", "TestPass123!")

    reponse = client.get("/users/?page=1&per_page=1", headers=headers)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert isinstance(corps, dict), "une liste nue ne porte aucun total"
    assert corps["total"] >= 1
    assert len(corps["data"]) == 1


def test_recherche_utilisateurs_respecte_la_pagination(db_session, api_client):
    """Avec un terme de recherche, page et per_page etaient ignores cote
    serveur : la recherche renvoyait tous les resultats d'un coup."""
    create_test_user(db_session, "chercheadmin", "admin")
    for i in range(3):
        create_test_user(db_session, f"cherchecible{i}", "secretaire")
    db_session.flush()

    client = api_client(users_endpoint, auth_endpoints)
    headers = auth_headers(client, "chercheadmin", "TestPass123!")

    reponse = client.get("/users/?search=cherchecible&page=1&per_page=2", headers=headers)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert len(corps["data"]) == 2, "la recherche doit honorer per_page"
    assert corps["total"] >= 3, "le total doit compter tous les resultats, pas la page"
```

- [ ] **Step 2 : Lancer les tests pour les voir échouer**

Run : `pytest tests/test_users_pagination.py -v`
Attendu : ÉCHEC des deux tests — la réponse est une liste.

- [ ] **Step 3 : Ajouter le schéma d'enveloppe**

Dans `api_backend/backend_app/routes/admin/users_schemas.py`, à la suite de la définition de `UserOut` :

```python
class UserListResponse(BaseModel):
    data: List[UserOut]
    total: int
    page: int
    per_page: int
    total_pages: int
```

Vérifier que `List` est importé depuis `typing` en tête de fichier ; l'ajouter si absent.

- [ ] **Step 4 : Faire renvoyer le total par le contrôleur**

Dans `controller/user_controller.py`, modifier `list_users` et `search_users` pour qu'ils renvoient un tuple `(items, total)`, le total étant calculé avant pagination. Les deux doivent accepter `page` et `per_page` :

```python
    def list_users(self, page: int = 1, per_page: int = 50):
        return self.repo.list_users_paginated(page=page, per_page=per_page)

    def search_users(self, term: str, page: int = 1, per_page: int = 50):
        return self.repo.search_users_paginated(term=term, page=page, per_page=per_page)
```

Dans `repositories/user_repo.py`, ajouter les deux méthodes paginées à côté des existantes. `list_users` et `search_users` actuelles sont **conservées intactes** : d'autres appelants en dépendent (`get_doctors`, écrans de sélection). Les nouvelles réutilisent la même construction de requête, en ajoutant le comptage avant pagination :

```python
    def list_users_paginated(self, page: int = 1, per_page: int = 50) -> tuple[list[User], int]:
        """Comme list_users(), mais renvoie aussi le nombre total de comptes.
        Le total est calcule AVANT offset/limit - sinon il vaudrait la taille
        de la page, ce qui bloquait la pagination sur un seul ecran."""
        requete = (
            self.session.query(User)
            .options(
                joinedload(User.application_role),
                joinedload(User.specialty),
            )
        )
        total = requete.order_by(None).count()
        items = requete.offset((page - 1) * per_page).limit(per_page).all()
        return items, total

    def search_users_paginated(self, term: str, page: int = 1, per_page: int = 50) -> tuple[list[User], int]:
        """Recherche paginee. L'ancienne search_users() renvoyait tous les
        resultats d'un coup : page et per_page etaient ignores."""
        q = term.strip()
        filters = []
        if q.isdigit():
            filters.append(User.user_id == int(q))
        pattern = f"%{q}%"
        filters.extend([
            User.username.ilike(pattern),
            User.full_name.ilike(pattern),
            User.email.ilike(pattern),
            User.contact.ilike(pattern),
        ])
        filters.append(ApplicationRole.role_name.ilike(pattern))
        filters.append(MedicalSpecialty.name.ilike(pattern))

        requete = (
            self.session.query(User)
            .join(ApplicationRole, User.role_id == ApplicationRole.role_id, isouter=True)
            .join(MedicalSpecialty, User.specialty_id == MedicalSpecialty.specialty_id, isouter=True)
            .options(
                joinedload(User.application_role),
                joinedload(User.specialty),
            )
            .filter(or_(*filters))
        )
        total = requete.order_by(None).count()
        items = requete.offset((page - 1) * per_page).limit(per_page).all()
        return items, total
```

Les imports nécessaires (`joinedload`, `or_`, `ApplicationRole`, `MedicalSpecialty`) sont déjà présents en tête de `user_repo.py` — le vérifier sans rien ajouter d'inutile.

- [ ] **Step 5 : Adapter l'endpoint**

Dans `users_endpoint.py` :

```python
@router.get("/", response_model=UserListResponse, dependencies=[Depends(role_required("admin", "manager"))])
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    user_ctrl: UserController = Depends(get_user_controller),
):
    """Liste tous les utilisateurs ou recherche par terme, toujours paginee."""
    if search:
        raws, total = user_ctrl.search_users(search, page=page, per_page=per_page)
    else:
        raws, total = user_ctrl.list_users(page=page, per_page=per_page)
    return {
        "data": [_safe_validate_user(u) for u in raws],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 1,
    }
```

Ajouter `UserListResponse` à l'import des schémas.

- [ ] **Step 6 : Vérifier que les tests passent**

Run : `pytest tests/test_users_pagination.py -v`
Attendu : SUCCÈS des deux tests.

- [ ] **Step 7 : Adapter le client de la liste utilisateurs**

Dans `ah2-admin-web/src/stores/userStore.js`, la lecture de la réponse doit désormais prendre `response.data.data` pour les éléments et `response.data.total` / `total_pages` pour la pagination. Lire le fichier, repérer l'affectation actuelle et l'adapter. Ne pas modifier autre chose.

- [ ] **Step 8 : Vérifier qu'aucun autre appelant n'est cassé**

Run : `grep -rn "'/users/'" ah2-admin-web/src/` puis vérifier chaque appelant trouvé.
Le tableau de bord admin (`dashboardStore.js`) est traité en tâche 5 — ne pas le modifier ici.

Run : `pytest tests/test_rbac.py -v`
Attendu : aucun échec nouveau.

- [ ] **Step 9 : Consigner**

Ledger : tâche 2 terminée, `L1f` et la partie « utilisateurs » de `L1h` résolus. **Ne pas commiter.**

---

## Task 3 : Journal financier unifié — backend (registre L1e)

**Files:**
- Create: `repositories/finance_ledger_repo.py`
- Create: `api_backend/backend_app/routes/finance/__init__.py` (fichier vide)
- Create: `api_backend/backend_app/routes/finance/finance_endpoints.py`
- Modify: `api_backend/backend_app/main.py` (enregistrement du routeur)
- Test: `tests/test_finance_ledger.py` (créer)

**Interfaces:**
- Produit : `GET /finance/mouvements` → `{data: [...], total, page, per_page, total_pages}`. Chaque élément porte `id`, `sens` (`"INCOME"` ou `"EXPENSE"`), `amount`, `amount_total`, `date`, `category`, `payment_method`, `description`, `created_by_name`, `status`. La tâche 4 consomme exactement ce contrat.
- `amount` est le montant réellement mouvementé : `advance_amount` pour une recette (ce qui a été encaissé), `amount` pour une dépense. `amount_total` porte le montant dû total d'une recette, et vaut le même montant pour une dépense.

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `tests/test_finance_ledger.py` :

```python
from datetime import datetime

from api_backend.backend_app.routes.finance import finance_endpoints
from api_backend.backend_app.routes.auth import auth_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_transaction, create_test_retrait


def test_journal_melange_recettes_et_depenses_triees(db_session, api_client):
    """Le journal doit renvoyer un flux unique trie par date decroissante,
    tous sens confondus. Avant : le client paginait les deux sources
    separement puis triait la page courante, donc l'ordre etait faux d'une
    page a l'autre et le total valait la somme de deux totaux."""
    admin = create_test_user(db_session, "journal_admin", "admin")
    db_session.flush()

    create_test_transaction(db_session, admin, amount=300.0, advance_amount=300.0,
                            paid_at=datetime(2025, 3, 10, 9, 0))
    create_test_retrait(db_session, admin, amount=50.0,
                        retrait_at=datetime(2025, 3, 11, 9, 0))
    create_test_transaction(db_session, admin, amount=200.0, advance_amount=200.0,
                            paid_at=datetime(2025, 3, 12, 9, 0))
    db_session.flush()

    client = api_client(finance_endpoints, auth_endpoints)
    headers = auth_headers(client, "journal_admin", "TestPass123!")

    reponse = client.get(
        "/finance/mouvements?date_from=2025-03-10&date_to=2025-03-12&page=1&per_page=10",
        headers=headers,
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["total"] == 3
    sens = [m["sens"] for m in corps["data"]]
    assert sens == ["INCOME", "EXPENSE", "INCOME"], "tri par date decroissante, sens melanges"
    assert corps["data"][0]["amount"] == 200.0


def test_journal_pagine_sur_le_flux_fusionne(db_session, api_client):
    """La pagination doit porter sur le flux fusionne, pas sur chaque source
    separement : la page 2 doit contenir le 3e mouvement, pas un doublon."""
    admin = create_test_user(db_session, "journal_admin2", "admin")
    db_session.flush()

    create_test_transaction(db_session, admin, amount=300.0, advance_amount=300.0,
                            paid_at=datetime(2025, 4, 10, 9, 0))
    create_test_retrait(db_session, admin, amount=50.0,
                        retrait_at=datetime(2025, 4, 11, 9, 0))
    create_test_transaction(db_session, admin, amount=200.0, advance_amount=200.0,
                            paid_at=datetime(2025, 4, 12, 9, 0))
    db_session.flush()

    client = api_client(finance_endpoints, auth_endpoints)
    headers = auth_headers(client, "journal_admin2", "TestPass123!")
    base = "/finance/mouvements?date_from=2025-04-10&date_to=2025-04-12&per_page=2"

    page1 = client.get(f"{base}&page=1", headers=headers).json()
    page2 = client.get(f"{base}&page=2", headers=headers).json()

    assert len(page1["data"]) == 2
    assert len(page2["data"]) == 1
    assert page1["total"] == 3 and page2["total"] == 3
    ids_page1 = {(m["sens"], m["id"]) for m in page1["data"]}
    ids_page2 = {(m["sens"], m["id"]) for m in page2["data"]}
    assert ids_page1.isdisjoint(ids_page2), "aucun mouvement ne doit apparaitre deux fois"


def test_journal_filtre_par_categorie_sur_tout_le_flux(db_session, api_client):
    """Le filtre categorie doit s'appliquer en base, pas sur la page deja
    chargee : sinon il ne voit qu'une quarantaine de lignes."""
    admin = create_test_user(db_session, "journal_admin3", "admin")
    db_session.flush()

    create_test_transaction(db_session, admin, amount=100.0, advance_amount=100.0,
                            transaction_type="Consultation",
                            paid_at=datetime(2025, 5, 10, 9, 0))
    create_test_transaction(db_session, admin, amount=100.0, advance_amount=100.0,
                            transaction_type="Pharmacie",
                            paid_at=datetime(2025, 5, 11, 9, 0))
    db_session.flush()

    client = api_client(finance_endpoints, auth_endpoints)
    headers = auth_headers(client, "journal_admin3", "TestPass123!")

    corps = client.get(
        "/finance/mouvements?date_from=2025-05-10&date_to=2025-05-11&category=Consultation",
        headers=headers,
    ).json()

    assert corps["total"] == 1
    assert corps["data"][0]["category"] == "Consultation"
```

- [ ] **Step 2 : Lancer les tests pour les voir échouer**

Run : `pytest tests/test_finance_ledger.py -v`
Attendu : ÉCHEC à l'import — `api_backend.backend_app.routes.finance` n'existe pas.

- [ ] **Step 3 : Écrire le dépôt du journal**

Créer `repositories/finance_ledger_repo.py` :

```python
# repositories/finance_ledger_repo.py
"""
Journal financier unifie : recettes (caisse) et depenses (caisse_retrait)
vues comme un seul flux de mouvements, trie et pagine EN BASE.

Raison d'etre : ces deux tables etaient paginees separement puis fusionnees
cote client, ce qui rendait le tri faux d'une page a l'autre, les dernieres
pages vides et le filtre categorie inoperant (registre L1e). Deux sources
paginees independamment ne peuvent pas etre fusionnees correctement apres
coup, quelle que soit l'astuce : la fusion doit avoir lieu avant la
pagination, donc en base.
"""

from typing import Any, Dict, Optional

from sqlalchemy import func, literal, or_, select, union_all
from sqlalchemy.orm import Session

from models.caisse import Caisse
from models.retrait import CaisseRetrait
from models.user import User


class FinanceLedgerRepository:
    def __init__(self, session: Session):
        self.session = session

    def _flux_unifie(self):
        """Construit l'union des deux tables sous une projection commune."""
        recettes = select(
            Caisse.transaction_id.label("id"),
            literal("INCOME").label("sens"),
            # Montant reellement encaisse, pas le total du : meme convention
            # que le tableau de bord (dashboardStore).
            Caisse.advance_amount.label("amount"),
            Caisse.amount.label("amount_total"),
            Caisse.paid_at.label("date"),
            Caisse.transaction_type.label("category"),
            Caisse.payment_method.label("payment_method"),
            Caisse.note.label("description"),
            Caisse.created_by_name.label("created_by_name"),
            Caisse.status.label("status"),
        )

        depenses = select(
            CaisseRetrait.retrait_id.label("id"),
            literal("EXPENSE").label("sens"),
            CaisseRetrait.amount.label("amount"),
            CaisseRetrait.amount.label("amount_total"),
            CaisseRetrait.retrait_at.label("date"),
            CaisseRetrait.category.label("category"),
            CaisseRetrait.payment_method.label("payment_method"),
            CaisseRetrait.justification.label("description"),
            # caisse_retrait ne stocke pas le nom de l'auteur, seulement la
            # cle etrangere - on le resout ici pour homogeneiser la projection.
            User.full_name.label("created_by_name"),
            CaisseRetrait.status.label("status"),
        ).join(User, User.user_id == CaisseRetrait.handled_by, isouter=True)

        return union_all(recettes, depenses).subquery("mouvements")

    def _appliquer_filtres(self, requete, flux, date_from, date_to, category, search, sens, status):
        if sens in ("INCOME", "EXPENSE"):
            requete = requete.where(flux.c.sens == sens)
        if status:
            requete = requete.where(flux.c.status == status)
        # func.date() sur la colonne : inclut la journee entiere quel que soit
        # le format envoye par l'appelant (meme regle que caisse_repo:127).
        if date_from is not None:
            requete = requete.where(func.date(flux.c.date) >= date_from)
        if date_to is not None:
            requete = requete.where(func.date(flux.c.date) <= date_to)
        if category:
            requete = requete.where(flux.c.category == category)
        if search:
            motif = f"%{search.lower()}%"
            requete = requete.where(
                or_(
                    func.lower(flux.c.description).like(motif),
                    func.lower(flux.c.category).like(motif),
                    func.lower(flux.c.created_by_name).like(motif),
                )
            )
        return requete

    def list_mouvements(
        self,
        page: int = 1,
        per_page: int = 20,
        date_from=None,
        date_to=None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sens: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        flux = self._flux_unifie()

        # Total calcule sur le flux filtre AVANT pagination.
        requete_total = self._appliquer_filtres(
            select(func.count()).select_from(flux), flux,
            date_from, date_to, category, search, sens, status,
        )
        total = self.session.execute(requete_total).scalar() or 0

        requete = self._appliquer_filtres(
            select(flux), flux,
            date_from, date_to, category, search, sens, status,
        )
        lignes = self.session.execute(
            requete.order_by(flux.c.date.desc(), flux.c.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).mappings().all()

        return {
            "data": [
                {
                    "id": l["id"],
                    "sens": l["sens"],
                    "amount": float(l["amount"] or 0),
                    "amount_total": float(l["amount_total"] or 0),
                    "date": l["date"],
                    "category": l["category"],
                    "payment_method": l["payment_method"],
                    "description": l["description"],
                    "created_by_name": l["created_by_name"],
                    "status": l["status"],
                }
                for l in lignes
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 1,
        }
```

- [ ] **Step 4 : Écrire le routeur**

Créer `api_backend/backend_app/routes/finance/__init__.py` (fichier vide), puis `finance_endpoints.py` :

```python
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api_backend.backend_app.database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import role_required
from repositories.finance_ledger_repo import FinanceLedgerRepository

router = APIRouter(prefix="/finance", tags=["Finance"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_ledger_repo(db: Session = Depends(get_db)) -> FinanceLedgerRepository:
    return FinanceLedgerRepository(db)


@router.get(
    "/mouvements",
    response_model=Any,
    dependencies=[Depends(role_required("admin", "secretaire", "manager"))],
)
def list_mouvements(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sens: Optional[str] = Query(None, pattern="^(INCOME|EXPENSE)$"),
    status: Optional[str] = Query(None),
    repo: FinanceLedgerRepository = Depends(get_ledger_repo),
):
    """Journal financier unifie : recettes et depenses en un seul flux,
    trie et pagine en base."""
    return repo.list_mouvements(
        page=page, per_page=per_page, date_from=date_from, date_to=date_to,
        category=category, search=search, sens=sens, status=status,
    )
```

- [ ] **Step 4b : Exposer les catégories réellement présentes**

Le filtre catégorie de l'interface est aujourd'hui alimenté par une liste **codée en dur** de libellés français (`FinancialList.vue:204-207` : `'Consultation'`, `'Pharmacie'`…), alors que la saisie enregistre des codes anglais (`FinanceModal.vue:156-175` : `'CONSULTATION'`, `'PHARMACY'`…). Les deux vocabulaires ne correspondent pas, et la base contient un mélange des deux selon l'ancienneté des lignes. Filtrer ne peut donc pas fonctionner, même une fois la pagination corrigée.

Plutôt que de trancher un vocabulaire — ce qui serait une décision produit et une normalisation de données hors périmètre de ce chantier — on alimente la liste depuis **les valeurs réellement présentes en base**. Le filtre devient ainsi juste par construction, quel que soit le mélange.

Ajouter dans `repositories/finance_ledger_repo.py` :

```python
    def list_categories(self) -> list[str]:
        """Categories reellement presentes dans le journal. Evite de coder en
        dur un vocabulaire : la base contient un melange de libelles francais
        et de codes anglais selon l'anciennete des lignes."""
        flux = self._flux_unifie()
        lignes = self.session.execute(
            select(flux.c.category).where(flux.c.category.isnot(None)).distinct().order_by(flux.c.category)
        ).scalars().all()
        return [c for c in lignes if c]
```

et dans `finance_endpoints.py` :

```python
@router.get(
    "/categories",
    response_model=Any,
    dependencies=[Depends(role_required("admin", "secretaire", "manager"))],
)
def list_categories(repo: FinanceLedgerRepository = Depends(get_ledger_repo)):
    """Categories reellement presentes dans le journal financier."""
    return repo.list_categories()
```

- [ ] **Step 5 : Enregistrer le routeur**

Dans `api_backend/backend_app/main.py`, ajouter l'import auprès des autres imports de routes :

```python
from .routes.finance import finance_endpoints
```

puis, auprès des autres `include_router` :

```python
app.include_router(finance_endpoints.router)
```

- [ ] **Step 6 : Vérifier que les tests passent**

Run : `pytest tests/test_finance_ledger.py -v`
Attendu : SUCCÈS des trois tests.

Si un test échoue sur le tri, vérifier que `order_by` porte bien sur `flux.c.date` (la colonne du flux unifié) et non sur une colonne d'une des tables sources.

- [ ] **Step 7 : Vérifier contre la base réelle**

Redémarrer le backend (modification dans `repositories/` — non couverte par `--reload`), puis :

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8200/finance/mouvements?date_from=2025-12-02&date_to=2025-12-02&per_page=5'
```

Comparer le `total` renvoyé au comptage SQL direct :

```sql
SELECT (SELECT count(*) FROM caisse WHERE date(paid_at) = '2025-12-02')
     + (SELECT count(*) FROM caisse_retrait WHERE date(retrait_at) = '2025-12-02');
```

Attendu : les deux nombres sont égaux.

- [ ] **Step 8 : Consigner**

Ledger : tâche 3 terminée, backend du journal unifié en place, avec le total vérifié contre SQL. **Ne pas commiter.**

---

## Task 4 : Journal financier unifié — câblage frontend (registre L1e)

**Files:**
- Modify: `ah2-admin-web/src/services/FinanceGateway.js`
- Modify: `ah2-admin-web/src/stores/financialStore.js:36-114` (`fetchTransactions`)
- Modify: `ah2-admin-web/src/views/modules/finance/FinancialList.vue:102` (filtre catégorie)

**Interfaces:**
- Consomme : `GET /finance/mouvements` tel que défini en tâche 3.
- Produit : `financialStore.transactions` conserve exactement la forme d'objet déjà attendue par `FinancialList.vue` — `{id, date, description, category, amount, type, status, paymentMethod}` — afin de ne pas modifier le gabarit d'affichage.

- [ ] **Step 1 : Ajouter l'appel au journal dans la passerelle**

Dans `ah2-admin-web/src/services/FinanceGateway.js`, ajouter :

```js
    /**
     * Journal financier unifie : recettes et depenses en un seul flux,
     * trie et pagine cote serveur. Remplace la fusion client de
     * fetchIncomes + fetchExpenses, qui produisait un tri faux.
     */
    async fetchMouvements(query) {
        return api.get('/finance/mouvements', { params: cleanParams(query) });
    },
```

Conserver `fetchIncomes` et `fetchExpenses` : le tableau de bord (`dashboardStore`) les utilise encore.

- [ ] **Step 2 : Écrire le nouveau chargement du store**

Dans `ah2-admin-web/src/stores/financialStore.js`, remplacer intégralement le corps de `fetchTransactions` par :

```js
    async function fetchTransactions() {
        isLoading.value = true;
        transactions.value = [];

        try {
            const reponse = await FinanceGateway.fetchMouvements({
                page: filters.value.page,
                per_page: filters.value.per_page,
                date_from: filters.value.startDate,
                date_to: filters.value.endDate,
                search: filters.value.searchQuery,
                category: filters.value.category || undefined,
                sens: filters.value.type === 'ALL' ? undefined : filters.value.type,
            });

            const corps = reponse.data;

            transactions.value = (corps.data || []).map((m) => ({
                id: `${m.sens === 'INCOME' ? 'inc' : 'exp'}-${m.id}`,
                date: m.date ? String(m.date).split('T')[0] : '',
                description: m.description,
                category: m.category || (m.sens === 'INCOME' ? 'Recette' : 'Dépense'),
                amount: Number(m.amount) || 0,
                type: m.sens,
                status: m.status === 'active' ? 'Validé' : m.status,
                paymentMethod: m.payment_method || 'Espèces',
            }));

            // Tri, filtrage et total viennent desormais du serveur : ne plus
            // rien trier ni filtrer ici, c'est precisement ce qui faussait
            // l'ordre d'une page a l'autre.
            totalItems.value = corps.total || 0;

            await updateKPIs();
        } catch (error) {
            console.error('Erreur chargement des mouvements financiers:', error);
            transactions.value = [];
            totalItems.value = 0;
            throw error;
        } finally {
            isLoading.value = false;
        }
    }
```

- [ ] **Step 3 : Alimenter le filtre catégorie depuis les vraies valeurs**

Dans `ah2-admin-web/src/services/FinanceGateway.js`, ajouter :

```js
    async fetchCategories() {
        return api.get('/finance/categories');
    },
```

Dans `ah2-admin-web/src/views/modules/finance/FinancialList.vue`, remplacer la liste codée en dur (`FinancialList.vue:204-207`) :

```js
const availableCategories = [
    'Consultation', 'Pharmacie', 'Hospitalisation','Examens' ,'Laboratoire', 
    'Salaires', 'Matériel', 'Factures','Detox', 'Autre'
];
```

par une liste chargée depuis le serveur :

```js
// Alimentee par les valeurs reellement presentes en base : la saisie
// enregistre des codes anglais ('CONSULTATION') tandis que cette liste
// contenait des libelles francais ('Consultation'), donc le filtre ne
// pouvait jamais correspondre.
const availableCategories = ref([]);
```

et, dans le `onMounted` existant, ajouter le chargement à côté de l'appel déjà présent :

```js
onMounted(async () => {
    financialStore.fetchTransactions();
    try {
        const reponse = await FinanceGateway.fetchCategories();
        availableCategories.value = reponse.data || [];
    } catch (err) {
        console.error('Categories financieres indisponibles:', err);
        availableCategories.value = [];
    }
});
```

Ajouter l'import de `FinanceGateway` et de `ref` en tête du bloc `<script setup>` s'ils n'y figurent pas déjà. Vérifier que le `v-for` du sélecteur de catégorie consomme bien `availableCategories` — s'il itérait sur la constante, il itère désormais sur la ref, sans autre changement.

Vérifier enfin que le changement de catégorie appelle `financialStore.setFilters({ category })` suivi d'un rechargement, et non un filtrage en mémoire : le filtrage est désormais entièrement côté serveur.

- [ ] **Step 4 : Reconstruire et vérifier**

Run : `cd ah2-admin-web && npm run build`
Attendu : build réussi, aucune erreur.

- [ ] **Step 5 : Vérifier en conditions réelles**

Ouvrir le module Finance connecté en admin, sur une plage couvrant plusieurs jours avec des recettes **et** des dépenses. Vérifier :
- les dates se suivent en ordre décroissant **d'une page à l'autre** (contrôler la dernière ligne d'une page et la première de la suivante) ;
- la dernière page n'est pas vide ;
- le nombre annoncé « N transactions trouvées » correspond au nombre réel obtenu en parcourant toutes les pages ;
- le filtre catégorie change le total affiché, et pas seulement les lignes visibles.

- [ ] **Step 6 : Consigner**

Ledger : tâche 4 terminée, `L1e` résolu de bout en bout, avec le résultat des vérifications ci-dessus. **Ne pas commiter.**

---

## Task 5 : Tableau de bord admin tolérant aux pannes (registre L1g et L1f côté client)

**Files:**
- Modify: `ah2-admin-web/src/stores/dashboardStore.js:56-134` (`fetchDashboardData`)
- Modify: `ah2-admin-web/src/views/dashboards/DashboardOverview.vue` (affichage de l'indisponibilité)

**Interfaces:**
- Consomme : `GET /users/` renvoyant `{data, total, ...}` — produit par la tâche 2. Cette tâche doit être exécutée **après** la tâche 2.
- Produit : `dashboardStore.stats` inchangé dans sa forme, plus un nouvel état `dashboardStore.indisponibles` — un tableau de chaînes nommant les blocs en échec (`'income'`, `'expense'`, `'debt'`, `'toxico'`, `'users'`, `'activites'`).

- [ ] **Step 1 : Remplacer le chargement bloc par bloc**

Dans `ah2-admin-web/src/stores/dashboardStore.js`, remplacer le `Promise.all` et la lecture des résultats par une version tolérante. Déclarer d'abord l'état, auprès des autres `ref` du store :

```js
    // Blocs dont le chargement a echoue : l'interface doit afficher
    // "indisponible" et surtout PAS 0, qui serait un chiffre faux.
    const indisponibles = ref([]);
```

Puis, dans `fetchDashboardData` :

```js
            const resultats = await Promise.allSettled([
                FinanceGateway.getIncomeTotal(dateParams),
                FinanceGateway.getExpenseTotal(dateParams),
                FinanceGateway.getDebtTotal(dateParams),
                FinanceGateway.fetchIncomes(listParams),
                FinanceGateway.fetchExpenses(listParams),
                ToxicoGateway.getDashboardStats(),
                api.get('/users/', { params: { page: 1, per_page: 1 } }),
            ]);

            const [incomeRes, expenseRes, debtRes, recentIncomes, recentExpenses, toxicoRes, usersRes] = resultats;
            const echecs = [];

            const valeurOuEchec = (resultat, nomBloc, lecture, defaut = 0) => {
                if (resultat.status === 'fulfilled') {
                    return lecture(resultat.value);
                }
                echecs.push(nomBloc);
                console.error(`Bloc "${nomBloc}" indisponible :`, resultat.reason);
                return defaut;
            };

            stats.value.income = valeurOuEchec(incomeRes, 'income', (r) => Number(r.data) || 0);
            stats.value.withdrawals = valeurOuEchec(expenseRes, 'expense', (r) => Number(r.data) || 0);
            stats.value.debt = valeurOuEchec(debtRes, 'debt', (r) => Number(r.data) || 0);
            stats.value.activePatients = valeurOuEchec(
                toxicoRes, 'toxico', (r) => r.data?.currentMonthAdmissions || 0
            );
            // /users/ renvoie desormais une enveloppe paginee (tache 2) :
            // total est le nombre reel de comptes, pas la taille de la page.
            stats.value.onlineUsers = valeurOuEchec(usersRes, 'users', (r) => r.data?.total ?? 0);
```

Pour les activités récentes, conserver exactement les deux blocs de transformation existants (`formattedIncomes` et `formattedExpenses`, inchangés dans leur contenu), mais les alimenter depuis les résultats tolérants :

```js
            const listeIncomes = recentIncomes.status === 'fulfilled' ? (recentIncomes.value.data.data || []) : [];
            const listeExpenses = recentExpenses.status === 'fulfilled' ? (recentExpenses.value.data.data || []) : [];
            if (recentIncomes.status === 'rejected' || recentExpenses.status === 'rejected') {
                echecs.push('activites');
            }
```

puis remplacer `(recentIncomes.data.data || [])` par `listeIncomes` et `(recentExpenses.data.data || [])` par `listeExpenses` dans les deux `map` existants, sans rien changer d'autre à leur contenu.

Enfin, avant la fin du bloc :

```js
            indisponibles.value = echecs;
```

Exposer `indisponibles` dans l'objet retourné par le store, auprès de `stats` et `recentActivities`.

- [ ] **Step 2 : Afficher l'indisponibilité au lieu d'un zéro**

`StatCard` déclare déjà `value: { type: [String, Number], required: true }` (`StatCard.vue:35`) : il accepte une chaîne, **aucune modification du composant n'est nécessaire**.

Dans `ah2-admin-web/src/views/dashboards/DashboardOverview.vue`, ajouter le helper auprès des autres fonctions du `<script setup>` :

```js
// Un bloc en echec doit afficher son indisponibilite, jamais 0 : un zero
// est un chiffre, et un chiffre faux est pire qu'une absence de chiffre.
const valeurAffichee = (nomBloc, valeur) =>
    dashboardStore.indisponibles.includes(nomBloc) ? 'Indisponible' : valeur;
```

puis, pour chaque `StatCard` du gabarit, remplacer la valeur passée : `:value="stats.income"` devient `:value="valeurAffichee('income', stats.income)"`, et de même pour `'expense'` / `stats.withdrawals`, `'debt'` / `stats.debt`, `'toxico'` / `stats.activePatients`, `'users'` / `stats.onlineUsers`.

- [ ] **Step 3 : Reconstruire**

Run : `cd ah2-admin-web && npm run build`
Attendu : build réussi.

- [ ] **Step 4 : Vérifier le comportement dégradé pour de vrai**

Arrêter le backend, recharger le tableau de bord admin.
Attendu : les cartes affichent « Indisponible », **aucune n'affiche 0**, et la page ne reste pas vide sans explication.

Redémarrer le backend, recharger.
Attendu : toutes les cartes affichent des valeurs, et « Utilisateurs inscrits » affiche le nombre réel de comptes — le comparer à `SELECT count(*) FROM users;`.

- [ ] **Step 5 : Consigner**

Ledger : tâche 5 terminée, `L1g` résolu et `L1f` vérifié côté client. **Ne pas commiter.**

---

## Task 6 : Compteurs et recherches non tronqués (registre L1h)

**Files:**
- Modify: `api_backend/backend_app/routes/cs/cs_endpoint.py:96-110` (`list_consultations`)
- Modify: `ah2-admin-web/src/stores/secretariatHomeStore.js:41,51`
- Modify: `repositories/caisse_repo.py:105-114` (périmètre de recherche)
- Modify: `api_backend/backend_app/routes/toxico/toxico_schema.py:36-45` (`ToxicoPatientListItem`)
- Modify: `controller/toxico_controller.py:73-85` (alimentation du champ)
- Test: `tests/test_cs_pagination.py` (créer)

**Interfaces:**
- Produit : `GET /cs/` renvoie `{data, total, page, per_page, total_pages}`. `secretariatHomeStore` consomme `total`.
- Produit : `ToxicoPatientListItem` porte un champ supplémentaire `admissionDate: Optional[date]`.

- [ ] **Step 1 : Écrire le test qui échoue pour le compteur de consultations**

Créer `tests/test_cs_pagination.py` :

```python
from api_backend.backend_app.routes.cs import cs_endpoint
from api_backend.backend_app.routes.auth import auth_endpoints
from tests.conftest import auth_headers, create_test_user


def test_liste_consultations_expose_le_total_reel(db_session, api_client):
    """L'accueil secretariat comptait les consultations en lisant la
    longueur d'une page bornee a 200 : au-dela, le compteur plafonnait en
    silence. Le total doit venir du serveur."""
    create_test_user(db_session, "cs_admin", "admin")
    db_session.flush()

    client = api_client(cs_endpoint, auth_endpoints)
    headers = auth_headers(client, "cs_admin", "TestPass123!")

    reponse = client.get("/cs/?page=1&per_page=5", headers=headers)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert isinstance(corps, dict), "une liste nue ne porte aucun total"
    assert "total" in corps
    assert len(corps["data"]) <= 5
    assert corps["total"] >= len(corps["data"])
```

- [ ] **Step 2 : Lancer le test pour le voir échouer**

Run : `pytest tests/test_cs_pagination.py -v`
Attendu : ÉCHEC — la réponse est une liste.

- [ ] **Step 3 : Renvoyer l'enveloppe pour les consultations**

Dans `cs_endpoint.py`, le contrôleur charge déjà la liste complète avant de la découper : le total exact est donc disponible sans coût supplémentaire. Remplacer la déclaration et le corps :

```python
@router.get("/", response_model=ConsultationListResponse)
def list_consultations(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=200),
    search: Optional[str] = Query(None),
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    """Retourne la liste paginee des consultations, avec le total reel."""
    all_raw = cs_ctrl.list_consultations()
    total = len(all_raw)
    start = (page - 1) * per_page
    page_items = all_raw[start:start + per_page]
    return {
        "data": page_items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 1,
    }
```

Définir `ConsultationListResponse` dans le module de schémas des consultations, sur le même modèle que `PatientListResponse` :

```python
class ConsultationListResponse(BaseModel):
    data: List[ConsultationResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
```

Conserver la pagination en mémoire telle quelle : la déplacer en base est hors périmètre de ce chantier (le noter au ledger comme dette).

- [ ] **Step 4 : Vérifier que le test passe**

Run : `pytest tests/test_cs_pagination.py -v`
Attendu : SUCCÈS.

- [ ] **Step 5 : Corriger le compteur de l'accueil secrétariat**

Dans `ah2-admin-web/src/stores/secretariatHomeStore.js`, remplacer la lecture de la longueur par celle du total :

```js
            stats.value.consultationsCount = consultationsRes.status === 'fulfilled'
                ? (consultationsRes.value.data?.total ?? 0)
                : 0;
```

et réduire `perPage` à `1` dans l'appel `ConsultationGateway.fetchConsultations({ page: 1, perPage: 1 })`, puisque seul le total est utilisé — inutile de rapatrier 200 lignes pour afficher un nombre.

Vérifier que `ConsultationGateway.fetchConsultations` et les autres consommateurs de `/cs/` (notamment `ConsultationsList.vue`) lisent bien `data.data` désormais ; les adapter si besoin.

- [ ] **Step 6 : Étendre le périmètre de la recherche en caisse**

Dans `repositories/caisse_repo.py`, le filtre par terme ne porte que sur `transaction_type` et `created_by_name`, alors que la colonne « Description » affichée vient de `note`. Étendre :

```python
        if term:
            term_like = f"%{term.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Caisse.transaction_type).like(term_like),
                    func.lower(Caisse.created_by_name).like(term_like),
                    func.lower(Caisse.note).like(term_like),
                    func.lower(Caisse.patient_label).like(term_like),
                )
            )
```

`note` et `patient_label` étant nullables, `lower(NULL)` vaut `NULL` et la condition est simplement fausse pour ces lignes — aucun filtrage parasite.

- [ ] **Step 7 : Exposer la date d'admission dans la liste toxico**

Dans `api_backend/backend_app/routes/toxico/toxico_schema.py`, ajouter le champ à `ToxicoPatientListItem` :

```python
class ToxicoPatientListItem(BaseModel):
    """Pour le tableau de bord (Liste)"""
    patient_id: int
    dossier_id: int
    patientName: str
    code: str
    substance: str
    currentPhase: int
    relapseCount: int
    psychologist: str # Nom complet
    admissionDate: Optional[date] = None
```

Vérifier que `Optional` et `date` sont importés en tête de fichier ; les ajouter si absents.

Dans `controller/toxico_controller.py`, la construction de chaque élément se fait dans `map_dossier_to_list_item` (lignes 73-85). Le dossier porte la colonne `admission_date` (`models/toxico.py:24`, `Date`, non nulle). Ajouter la dernière entrée du dictionnaire :

```python
    def map_dossier_to_list_item(self, d):
        """Helper pour mapper l'objet ORM vers le format liste attendu par le Front"""
        return {
            "patient_id": d.patient_id,
            "dossier_id": d.id,
            "patientName": f"{d.patient.first_name} {d.patient.last_name}",
            "code": d.patient.code_patient,
            "substance": d.substance,
            "currentPhase": d.current_phase,
            "relapseCount": d.relapse_count,
            "psychologist": d.psychologist.full_name if d.psychologist else "Non assigné",
            # Sans cette date, le badge "+X cette semaine" et l'alerte
            # "evaluation en retard" de ToxicoList.vue ne se declenchent jamais.
            "admissionDate": d.admission_date,
        }
```

- [ ] **Step 8 : Vérifier l'ensemble**

Run : `pytest tests/test_cs_pagination.py tests/test_caisse.py -v`
Attendu : SUCCÈS du nouveau test, aucun échec nouveau sur la caisse.

Run : `cd ah2-admin-web && npm run build`
Attendu : build réussi.

Redémarrer le backend (modifications dans `repositories/` et `controller/`), puis vérifier dans le navigateur que le badge toxico « + X cette semaine » se calcule, et que la recherche en caisse trouve une transaction par sa description.

- [ ] **Step 9 : Consigner**

Ledger : tâche 6 terminée, `L1h` résolu, avec la dette notée sur la pagination en mémoire des consultations. **Ne pas commiter.**

---

## Task 7 : Erreurs avalées (registre L1i)

**Files:**
- Modify: `ah2-admin-web/src/stores/configStore.js:41-51` (`fetchStructureInfo`)
- Modify: `ah2-admin-web/src/stores/labStore.js:159-181` (suppression de `fetchHistory`)

**Interfaces:**
- Produit : `configStore.structureError` — `null` quand tout va bien, sinon une chaîne décrivant l'échec. Aucune autre tâche ne le consomme ; il sert à distinguer « non configuré » de « endpoint cassé ».

- [ ] **Step 1 : Supprimer le code mort du module labo**

Vérifier d'abord, pour ne pas supprimer du code vivant :

```bash
cd ah2-admin-web && grep -rn "fetchHistory\|getAllResults" src/
```

Attendu : `fetchHistory` n'apparaît qu'à sa définition (`labStore.js:159`), et `getAllResults` uniquement à son appel (`labStore.js:168`) — sans définition nulle part. Si ce n'est pas le cas, s'arrêter et remonter la question plutôt que de supprimer.

Supprimer alors la fonction `fetchHistory` de `labStore.js`, ainsi que son entrée dans l'objet retourné par le store si elle y figure.

- [ ] **Step 2 : Distinguer les deux états de la configuration**

Dans `ah2-admin-web/src/stores/configStore.js`, déclarer l'état auprès des autres `ref` :

```js
    // null = tout va bien. Une chaine = l'appel a echoue, ce qui n'est PAS
    // la meme chose qu'un etablissement non configure : sans cette
    // distinction, un endpoint casse et une base vide sont indiscernables.
    const structureError = ref(null);
```

puis remplacer `fetchStructureInfo` :

```js
    async function fetchStructureInfo() {
        try {
            const response = await api.get('/config/structure');
            structureError.value = null;
            if (response.data) {
                structureInfo.value = { ...structureInfo.value, ...response.data };
            }
        } catch (err) {
            structureError.value = "Impossible de charger les informations de l'établissement.";
            console.error('Echec du chargement des infos structure:', err);
        }
    }
```

Exposer `structureError` dans l'objet retourné par le store.

- [ ] **Step 3 : Reconstruire**

Run : `cd ah2-admin-web && npm run build`
Attendu : build réussi, aucune référence manquante à `fetchHistory`.

- [ ] **Step 4 : Vérifier**

Backend arrêté, recharger l'application : la console doit afficher une erreur explicite pour la structure, et non un simple avertissement silencieux.

Backend démarré : `structureError` reste `null` et le nom de l'établissement s'affiche.

- [ ] **Step 5 : Consigner**

Ledger : tâche 7 terminée, `L1i` résolu. **Ne pas commiter.**

---

## Task 8 : Clôture du chantier

**Files:**
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md`

- [ ] **Step 1 : Lancer la suite complète**

Run : `pytest -q`
Attendu : les 9 échecs pré-existants documentés, et aucun échec nouveau. Si un échec nouveau apparaît, le corriger avant de poursuivre.

- [ ] **Step 2 : Vérifier les chiffres contre la base**

Pour chaque compteur corrigé, comparer la valeur affichée à une requête SQL directe, comme cela a été fait pour `L1a-c` (48 500 F attendus, 48 500 F affichés) :
- nombre total de patients vs `SELECT count(*) FROM patients WHERE is_deleted = false;`
- nombre d'utilisateurs vs `SELECT count(*) FROM users;`
- total du journal financier sur une journée vs la somme des comptages des deux tables

- [ ] **Step 3 : Mettre à jour le registre**

Dans `docs/superpowers/SUIVI-AVANCEMENT.md`, marquer `L1d` à `L1i` comme résolus, avec la preuve chiffrée pour chacun, sur le modèle de la note déjà rédigée pour `L1a-c`. Mettre à jour la section « Étape en cours » pour marquer le chantier 5 terminé et désigner le chantier 6 comme suivant.

- [ ] **Step 4 : Consigner la clôture**

Ledger : chantier 5 terminé, liste des registres résolus, état de la suite de tests. **Ne pas commiter** — proposer à l'utilisateur de relire l'ensemble avant toute décision de commit.
