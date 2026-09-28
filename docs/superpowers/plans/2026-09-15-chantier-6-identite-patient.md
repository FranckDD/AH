# Chantier 6 — Réparer l'identité patient et construire le dossier consolidé — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un même patient n'a plus qu'un seul enregistrement quel que soit le domaine d'entrée (clinique/toxico/spirituel), les drapeaux de domaine reflètent la réalité des dossiers au lieu d'une colonne jamais mise à jour, et un nouvel endpoint consolidé donne aux soignants + admin + promoteur une vue unique du dossier patient, journalisée.

**Architecture:** Aucune migration de schéma. Trois axes indépendants qui convergent sur le même patient : (1) un calcul de drapeaux à la lecture (`EXISTS` corrélé) qui remplace des colonnes stockées jamais synchronisées ; (2) un rattachement optionnel à un patient existant dans le flux d'admission toxico, au lieu d'une création systématique ; (3) un contrôleur de composition (`PatientDossierController`) qui appelle les contrôleurs de domaine existants et assemble leurs réponses, exposé par un routeur FastAPI **séparé** de `patients_endpoints.py` (celui-ci porte une dépendance de rôle au niveau du routeur, qui s'ET-erait avec toute route ajoutée dans le même fichier — voir Contraintes globales).

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (ORM) + PostgreSQL, Vue 3 + Pinia côté frontend, pytest avec fixtures `db_session`/`api_client` (transaction réelle contre la base `AH2` locale, rollback en fin de test — voir `tests/conftest.py`).

**Spec:** `docs/superpowers/specs/2026-09-15-chantier-6-identite-patient-design.md`

## Global Constraints

- Aucune migration de schéma (`ci/schema_only.sql` reste inchangé) — toutes les tables/colonnes nécessaires existent déjà.
- **Aucun commit git** à aucune étape — toutes les règles de ce projet s'appliquent : jamais de commit sans accord explicite et frais de l'utilisateur à ce moment précis, jamais `git add -A`. Le suivi d'exécution se fait uniquement via le ledger SDD (`.superpowers/sdd/2026-09-15-chantier-6-identite-patient/progress.md`).
- FastAPI compose une dépendance de **routeur** (`APIRouter(dependencies=[...])`) et une dépendance de **route** (`@router.get(..., dependencies=[...])`) par **ET**, jamais par remplacement. `api_backend/backend_app/routes/patients/patients_endpoints.py` porte une dépendance de routeur (`role_required("medecin","nurse","secretaire","admin","manager")`) : **aucune nouvelle route n'est ajoutée dans ce fichier** dans ce chantier, sauf le seul élargissement explicitement prévu (Tâche 4). Le nouvel endpoint de dossier consolidé vit dans un fichier séparé, sans dépendance de routeur, chaque route portant sa propre liste de rôles.
- Toute écriture réelle en base contre `AH2` locale (hors transaction de test) exige une confirmation explicite de l'utilisateur juste avant l'exécution — jamais automatique, même si le plan la décrit.
- Les gardes de rôle des 4 modules existants (dossiers médicaux, prescriptions, consultations spirituelles, toxicologie — registre `L4b-e`) restent intactes. Ne pas les toucher dans ce chantier.
- `tests/conftest.py::db_session` refuse de s'exécuter contre une base qui n'est pas `AH2` sur `localhost`/`127.0.0.1` — les tests de ce plan sont donc des tests d'intégration réels, pas des mocks.

---

### Task 1: Drapeaux de domaine calculés + filtre par rôle de la liste patients (B6)

**Files:**
- Modify: `repositories/patient_repo.py` (ajout `compute_domain_flags`, imports, filtres `EXISTS` dans `list_patients`)
- Modify: `controller/medical_controller.py:107-111` (`get_patient_dme_summary` lit les drapeaux calculés, plus les colonnes stockées)
- Modify: `controller/patient_controller.py:316-323` (`list_patients` utilise `_get_user_roles_set()` au lieu du `role_name` inexistant)
- Test: `tests/test_patient_repo.py` (nouveau test pour `compute_domain_flags`)
- Test: `tests/test_patients_pagination.py` (nouveaux tests pour le filtre par rôle)

**Interfaces:**
- Consumes: `PatientRepository.session` (déjà existant), `MedicalRecord`/`ToxicoDossier`/`ConsultationSpirituel` (modèles ORM existants), `PatientController._get_user_roles_set()` (déjà existant, `controller/patient_controller.py:40-51`).
- Produces: `PatientRepository.compute_domain_flags(patient_id: int) -> dict` avec les clés `is_clinical`/`is_toxicology`/`is_spiritual` (booléens) — **consommé par la Tâche 5** (`PatientDossierController`). `PatientRepository.list_patients(..., filters=...)` continue de recevoir un dict `{'is_clinical': True}` etc. (signature inchangée), mais l'implémentation interne change de colonne stockée à `EXISTS` corrélé.

- [ ] **Step 1: Écrire le test qui échoue pour `compute_domain_flags`**

Ajouter à la fin de `tests/test_patient_repo.py` :

```python
def test_compute_domain_flags_reflete_les_dossiers_reels(db_session):
    """Bug corrige par le chantier 6 : patients.is_clinical/is_toxicology/
    is_spiritual sont poses une seule fois a la creation et jamais remis a
    jour. compute_domain_flags() doit calculer a partir de l'existence
    reelle d'un dossier, sans lecture de ces colonnes."""
    from repositories.patient_repo import PatientRepository
    from models.medical_record import MedicalRecord
    from models.toxico import ToxicoDossier
    from datetime import date

    admin = create_test_user(db_session, "flags_admin", "admin")
    db_session.flush()
    patient_id, _ = create_test_patient(
        db_session, admin,
        is_clinical=False, is_toxicology=False, is_spiritual=False,
    )
    db_session.flush()

    repo = PatientRepository(db_session)

    # Aucun dossier dans aucun domaine : tout doit etre faux, meme si
    # is_clinical/is_toxicology valaient True en base.
    flags = repo.compute_domain_flags(patient_id)
    assert flags == {"is_clinical": False, "is_toxicology": False, "is_spiritual": False}

    # On ajoute un dossier medical sans jamais toucher aux colonnes
    # is_clinical/is_toxicology/is_spiritual du patient.
    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="TEST"))
    db_session.add(ToxicoDossier(
        patient_id=patient_id, admission_date=date.today(), substance="Alcool",
    ))
    db_session.flush()

    flags = repo.compute_domain_flags(patient_id)
    assert flags == {"is_clinical": True, "is_toxicology": True, "is_spiritual": False}
```

Ajouter en tête du fichier, sous les imports existants (avant `def make_repo_with_mock_session`) :

```python
from tests.conftest import create_test_user, create_test_patient
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `pytest tests/test_patient_repo.py::test_compute_domain_flags_reflete_les_dossiers_reels -v`
Expected: FAIL avec `AttributeError: 'PatientRepository' object has no attribute 'compute_domain_flags'`

- [ ] **Step 3: Ajouter `compute_domain_flags` et les imports nécessaires**

En tête de `repositories/patient_repo.py`, à côté de `from models.medical_record import MedicalRecord` (déjà présent, ligne 11) :

```python
from models.toxico import ToxicoDossier
from models.consultation_spirituelle import ConsultationSpirituel
from sqlalchemy import exists
```

Ajouter la méthode dans `PatientRepository` (par exemple juste après `get_by_id`) :

```python
def compute_domain_flags(self, patient_id: int) -> dict:
    """Calcule les drapeaux de domaine a la lecture, a partir de
    l'existence reelle de dossiers - jamais depuis une colonne stockee.
    Remplace patients.is_clinical/is_toxicology/is_spiritual comme source
    de verite pour toute decision d'affichage ou de filtrage (registre L2,
    chantier 6)."""
    return {
        "is_clinical": self.session.query(
            exists().where(MedicalRecord.patient_id == patient_id)
        ).scalar(),
        "is_toxicology": self.session.query(
            exists().where(ToxicoDossier.patient_id == patient_id)
        ).scalar(),
        "is_spiritual": self.session.query(
            exists().where(ConsultationSpirituel.patient_id == patient_id)
        ).scalar(),
    }
```

- [ ] **Step 4: Lancer le test, vérifier qu'il passe**

Run: `pytest tests/test_patient_repo.py::test_compute_domain_flags_reflete_les_dossiers_reels -v`
Expected: PASS

- [ ] **Step 5: Écrire le test qui échoue pour le filtre par rôle de la liste patients**

Ajouter à `tests/test_patients_pagination.py` :

```python
def test_liste_patients_filtre_par_role_secretaire(db_session, api_client):
    """Bug B6 : list_patients() lisait getattr(user, 'role_name', '')
    qui n'existe jamais sur User -> le filtre par role etait mort, une
    secretaire voyait tous les patients. Chantier 6 l'active via
    _get_user_roles_set(), deja utilisee ailleurs dans ce controller."""
    from repositories.patient_repo import PatientRepository
    from models.medical_record import MedicalRecord
    from models.consultation_spirituelle import ConsultationSpirituel

    secretaire = create_test_user(db_session, "b6_secretaire", "secretaire", password=TEST_PASSWORD)
    admin = create_test_user(db_session, "b6_admin", "admin", password=TEST_PASSWORD)
    clinique_id, _ = create_test_patient(db_session, admin, first_name="Clinique")
    spirituel_id, _ = create_test_patient(db_session, admin, first_name="Spirituel")
    db_session.flush()
    db_session.add(MedicalRecord(patient_id=clinique_id, motif_code="TEST"))
    db_session.add(ConsultationSpirituel(
        patient_id=spirituel_id, created_by=admin.user_id, created_by_name=admin.username,
        type_consultation="spirituelle",
    ))
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "b6_secretaire", TEST_PASSWORD)

    reponse = client.get("/patients/?per_page=50", headers=headers)

    assert reponse.status_code == 200
    codes = [p["patient_id"] for p in reponse.json()["data"]]
    assert spirituel_id in codes
    assert clinique_id not in codes


def test_liste_patients_filtre_par_role_medecin(db_session, api_client):
    from models.medical_record import MedicalRecord
    from models.consultation_spirituelle import ConsultationSpirituel

    medecin = create_test_user(db_session, "b6_medecin", "medecin", password=TEST_PASSWORD)
    admin = create_test_user(db_session, "b6_admin2", "admin", password=TEST_PASSWORD)
    clinique_id, _ = create_test_patient(db_session, admin, first_name="Clinique2")
    spirituel_id, _ = create_test_patient(db_session, admin, first_name="Spirituel2")
    db_session.flush()
    db_session.add(MedicalRecord(patient_id=clinique_id, motif_code="TEST"))
    db_session.add(ConsultationSpirituel(
        patient_id=spirituel_id, created_by=admin.user_id, created_by_name=admin.username,
        type_consultation="spirituelle",
    ))
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "b6_medecin", TEST_PASSWORD)

    reponse = client.get("/patients/?per_page=50", headers=headers)

    assert reponse.status_code == 200
    codes = [p["patient_id"] for p in reponse.json()["data"]]
    assert clinique_id in codes
    assert spirituel_id not in codes
```

- [ ] **Step 6: Lancer les tests, vérifier l'échec**

Run: `pytest tests/test_patients_pagination.py::test_liste_patients_filtre_par_role_secretaire tests/test_patients_pagination.py::test_liste_patients_filtre_par_role_medecin -v`
Expected: FAIL (les deux comptes voient tous les patients — le filtre est mort)

- [ ] **Step 7: Corriger `PatientController.list_patients` et `PatientRepository.list_patients`**

Dans `controller/patient_controller.py`, remplacer les lignes 316-323 :

```python
def list_patients(self, page=1, per_page=10, search=None):
    roles = self._get_user_roles_set()
    filters = {}
    if 'secretaire' in roles:
        filters['is_spiritual'] = True
    elif roles & {'medecin', 'nurse', 'assistant'}:
        filters['is_clinical'] = True
    return self.repo.list_patients(page=page, per_page=per_page, search=search, filters=filters)
```

Dans `repositories/patient_repo.py`, remplacer le bloc `# 1. Filtres de Service` de `list_patients` (lignes 240-247) :

```python
        # 1. Filtres de Service - EXISTS correle, jamais une colonne stockee
        # (chantier 6 : is_clinical/is_toxicology/is_spiritual ne sont plus
        # une source de verite, voir compute_domain_flags)
        if filters:
            if filters.get('is_clinical'):
                query = query.filter(exists().where(MedicalRecord.patient_id == Patient.patient_id))
            if filters.get('is_toxicology'):
                query = query.filter(exists().where(ToxicoDossier.patient_id == Patient.patient_id))
            if filters.get('is_spiritual'):
                query = query.filter(exists().where(ConsultationSpirituel.patient_id == Patient.patient_id))
```

- [ ] **Step 8: Lancer les tests, vérifier qu'ils passent**

Run: `pytest tests/test_patients_pagination.py -v`
Expected: PASS (y compris les tests déjà existants du fichier, non régressés)

- [ ] **Step 9: Corriger `get_patient_dme_summary` pour utiliser les drapeaux calculés**

Dans `controller/medical_controller.py`, remplacer les lignes 107-111 :

```python
            "flags": self.patient_ctrl.repo.compute_domain_flags(patient_id),
```

(remplace le bloc `"flags": {"is_clinical": patient.get('is_clinical', False), ...}` — `patient_ctrl.repo` est un `PatientRepository`, déjà accessible via `MedicalRecordController.__init__(self, repo=None, patient_controller=None, ...)`.)

- [ ] **Step 10: Vérifier la non-régression du module dossiers médicaux**

Run: `pytest tests/test_medical_record_mapping.py -v`
Expected: PASS

---

### Task 2: Rôle `promoteur`

**Files:**
- Modify: `api_backend/backend_app/security/role_map.py`
- Test: `tests/test_role_map.py`
- DB (réelle, hors test) : `INSERT INTO application_roles (role_name) VALUES ('promoteur');`

**Interfaces:**
- Produces: `role_map.PROMOTEUR = "promoteur"`, reconnu par `normalize_role_name("promoteur")` et par `role_required("promoteur")` — **consommé par la Tâche 5** (liste de rôles du nouvel endpoint de dossier consolidé).

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_role_map.py` :

```python
def test_normalizes_the_promoteur_role():
    assert normalize_role_name("promoteur") == "promoteur"
    assert normalize_role_name("Promoteur") == "promoteur"
    assert normalize_role_name("owner") == "promoteur"
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `pytest tests/test_role_map.py::test_normalizes_the_promoteur_role -v`
Expected: FAIL (retourne `None`, `promoteur` inconnu)

- [ ] **Step 3: Ajouter le rôle dans `role_map.py`**

Dans `api_backend/backend_app/security/role_map.py`, ajouter après `MANAGER = "manager"` :

```python
PROMOTEUR = "promoteur"
```

Ajouter `PROMOTEUR` dans `ROLE_CANONICALS` :

```python
ROLE_CANONICALS = {
    ADMIN, MEDECIN, NURSE, SECRETAIRE, LABORANTIN,
    PSYCHOLOGIST, SPIRITUALCOUNSELLOR, TOXICOMANAGER, ASSISTANT,
    MANAGER, PROMOTEUR,
}
```

Ajouter une entrée dans `ROLE_ALIASES` :

```python
    PROMOTEUR: {"promoteur", "promoter", "owner"},
```

- [ ] **Step 4: Lancer le test, vérifier qu'il passe**

Run: `pytest tests/test_role_map.py -v`
Expected: PASS (tous les tests du fichier, y compris les pré-existants)

- [ ] **Step 5: Écriture réelle en base — confirmation obligatoire, hors du sous-agent**

Cette étape n'est **pas** exécutée par le sous-agent implémenteur. Le contrôleur SDD (la session qui pilote ce plan) demande confirmation explicite à l'utilisateur, puis exécute lui-même, contre la base `AH2` locale :

```sql
INSERT INTO application_roles (role_name) VALUES ('promoteur');
```

Vérification après exécution : `SELECT role_id, role_name FROM application_roles WHERE role_name = 'promoteur';` doit renvoyer une ligne. Aucun compte utilisateur n'est créé avec ce rôle dans ce chantier.

---

### Task 3: Rattachement à un patient existant lors de l'admission toxicologique — backend

**Files:**
- Modify: `controller/toxico_controller.py:97-182` (`admission_patient` devient conditionnel)
- Modify: `api_backend/backend_app/routes/toxico/toxico_endpoint.py:141-171` (nouveau champ `patientId` en entrée)
- Test: `tests/test_toxico_admission.py` (nouveau fichier)

**Interfaces:**
- Consumes: `PatientController.get_patient(patient_id) -> Optional[dict]` (déjà existant, `controller/patient_controller.py:313-314`, renvoie un dict avec les clés `patient_id`/`code_patient`/`first_name`/`last_name`/... ou `None`).
- Produces: `ToxicoController.admission_patient(data: dict, ...)` accepte désormais une clé optionnelle `data["patient_id"]` — **consommé par la Tâche 4** (le frontend ajoute ce champ au `FormData` quand un patient existant est sélectionné).

- [ ] **Step 1: Écrire le test qui échoue**

Créer `tests/test_toxico_admission.py` :

```python
from datetime import date

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.routes.patients import patients_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def test_admission_toxico_rattache_a_un_patient_existant_sans_le_dupliquer(db_session, api_client):
    """Avant le chantier 6, l'admission toxico creait systematiquement un
    nouveau patient - impossible de rattacher un dossier toxico a un
    patient deja connu du centre (registre L2). Un patient_id fourni doit
    reutiliser ce patient, sans creer de doublon."""
    assistant = create_test_user(db_session, "toxico_assistant", "Assistant", password=TEST_PASSWORD)
    psy = create_test_user(db_session, "toxico_psy", "Psychologist", password=TEST_PASSWORD)
    patient_id, code_patient = create_test_patient(db_session, assistant, first_name="Existant")
    db_session.flush()

    client = api_client(auth_endpoints, toxico_endpoint, patients_endpoints)
    headers = auth_headers(client, "toxico_assistant", TEST_PASSWORD)

    reponse = client.post(
        "/toxico/admission",
        data={
            "patientId": str(patient_id),
            "admissionDate": date.today().isoformat(),
            "substance": "Alcool",
            "psychologist": str(psy.user_id),
            "guardianName": "Tuteur Test",
            "guardianContact": "0000000000",
        },
        headers=headers,
    )

    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["code_patient"] == code_patient

    total_patients = client.get("/patients/?search=Existant", headers=headers).json()["total"]
    assert total_patients == 1, "le rattachement ne doit pas creer un second patient"


def test_admission_toxico_patient_id_introuvable_est_rejetee(db_session, api_client):
    assistant = create_test_user(db_session, "toxico_assistant2", "Assistant", password=TEST_PASSWORD)
    psy = create_test_user(db_session, "toxico_psy2", "Psychologist", password=TEST_PASSWORD)
    db_session.flush()

    client = api_client(auth_endpoints, toxico_endpoint)
    headers = auth_headers(client, "toxico_assistant2", TEST_PASSWORD)

    reponse = client.post(
        "/toxico/admission",
        data={
            "patientId": "999999",
            "admissionDate": date.today().isoformat(),
            "substance": "Alcool",
            "psychologist": str(psy.user_id),
            "guardianName": "Tuteur Test",
            "guardianContact": "0000000000",
        },
        headers=headers,
    )

    assert reponse.status_code == 500
    assert "introuvable" in reponse.json()["detail"]


def test_admission_toxico_creation_sans_patient_id_inchangee(db_session, api_client):
    """Non-regression : le flux de creation existant (sans patient_id)
    continue de fonctionner exactement comme avant."""
    assistant = create_test_user(db_session, "toxico_assistant3", "Assistant", password=TEST_PASSWORD)
    psy = create_test_user(db_session, "toxico_psy3", "Psychologist", password=TEST_PASSWORD)
    db_session.flush()

    client = api_client(auth_endpoints, toxico_endpoint)
    headers = auth_headers(client, "toxico_assistant3", TEST_PASSWORD)

    reponse = client.post(
        "/toxico/admission",
        data={
            "firstName": "Nouveau",
            "lastName": "Patient",
            "dob": "1990-01-01",
            "mothersName": "Mere Test",
            "admissionDate": date.today().isoformat(),
            "substance": "Cannabis",
            "psychologist": str(psy.user_id),
            "guardianName": "Tuteur Test",
            "guardianContact": "0000000000",
        },
        headers=headers,
    )

    assert reponse.status_code == 201, reponse.text
```

- [ ] **Step 2: Lancer les tests, vérifier l'échec**

Run: `pytest tests/test_toxico_admission.py -v`
Expected: FAIL sur le premier test (422 — `patientId` n'existe pas encore comme champ du formulaire ; `firstName`/`lastName`/`dob`/`mothersName` restent `Form(...)` obligatoires)

- [ ] **Step 3: Rendre les champs patient optionnels et ajouter `patientId` dans l'endpoint**

Dans `api_backend/backend_app/routes/toxico/toxico_endpoint.py`, remplacer la signature de `admission_patient` (lignes 141-158) :

```python
@router.post("/admission", status_code=status.HTTP_201_CREATED,
             # Psychologist n'est PAS ici, c'est correct (il ne peut pas admettre)
             dependencies=[Depends(role_required("ToxicoManager", "admin", "Assistant"))])
async def admission_patient(
    request: Request,
    patientId: Optional[int] = Form(None),
    firstName: Optional[str] = Form(None),
    lastName: Optional[str] = Form(None),
    dob: Optional[date] = Form(None),
    mothersName: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    admissionDate: date = Form(...),
    substance: str = Form(...),
    psychologist: int = Form(...),
    guardianName: str = Form(...),
    guardianContact: str = Form(...),
    notes: Optional[str] = Form(None),
    consentFile: Optional[UploadFile] = File(None),
    ctrl: ToxicoController = Depends(get_toxico_controller)
):
    try:
        data = {
            "patient_id": patientId,
            "firstName": firstName, "lastName": lastName, "dob": dob, "mothersName": mothersName,
            "address": address, "contact": contact, "admissionDate": admissionDate,
            "substance": substance, "psychologist_id": psychologist,
            "guardianName": guardianName, "guardianContact": guardianContact, "notes": notes
        }
        base_url = str(request.base_url).rstrip("/")
        dossier = await ctrl.admission_patient(data=data, consent_file=consentFile, base_url=base_url) # type: ignore
        return {"message": "Admission réussie", "code_patient": dossier.patient.code_patient}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")
```

- [ ] **Step 4: Rendre `admission_patient` conditionnel dans le contrôleur**

Dans `controller/toxico_controller.py`, remplacer le bloc `# 2. Création du Patient via PatientController` (lignes 118-146) :

```python
        # 2. Resolution du patient : rattachement a un patient existant
        # ou creation (chantier 6, registre L2 - avant ce chantier,
        # l'admission toxico creait systematiquement un nouveau patient).
        patient_id_rattachement = data.get('patient_id')
        if patient_id_rattachement:
            patient_existant = self.patient_controller.get_patient(patient_id_rattachement)
            if not patient_existant:
                raise ValueError(f"Patient {patient_id_rattachement} introuvable")
            patient_id = patient_existant['patient_id']
            patient_code = patient_existant['code_patient']
        else:
            champs_requis = ('firstName', 'lastName', 'dob', 'mothersName')
            manquants = [c for c in champs_requis if not data.get(c)]
            if manquants:
                raise ValueError(
                    f"Champs patient requis manquants pour une nouvelle admission: {', '.join(manquants)}"
                )
            try:
                patient_data_for_creation = {
                    "first_name": data['firstName'], 
                    "last_name": data['lastName'], 
                    "birth_date": data['dob'],
                    "mother_name": data.get('mothersName'), 
                    "address": data.get('address'), 
                    "contact_phone": data.get('contact'),
                    "is_toxicology": True, 
                    "is_clinical": False, 
                    "is_spiritual": False, 
                    "gender": "M", 
                    "assurance": None, 
                    "residence": data.get('address'), 
                    "national_id": None, 
                    "father_name": None
                }
                patient_result = self.patient_controller.create_patient(patient_data_for_creation)

                if isinstance(patient_result, tuple):
                    patient_id, patient_code = patient_result
                else:
                    patient_id = patient_result
                    patient_code = "UNKNOWN" # Devrait être récupéré autrement si non retourné

            except ValueError as e:
                raise ValueError(f"Erreur lors de la création du patient: {str(e)}")
```

Aucune donnée du patient existant n'est modifiée par le chemin de rattachement — le reste de la méthode (préparation `toxico_data`, `create_dossier_after_patient_commit`, invalidation Redis, tâche Celery) reste inchangé, `patient_id`/`patient_code` étant désormais définis dans les deux branches.

- [ ] **Step 5: Lancer les tests, vérifier qu'ils passent**

Run: `pytest tests/test_toxico_admission.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Vérifier la non-régression du module toxico**

Run: `pytest tests/ -k toxico -v`
Expected: PASS

---

### Task 4: Recherche patient à l'admission toxico (frontend) + élargissement du rôle `Assistant`

**Files:**
- Modify: `api_backend/backend_app/routes/patients/patients_endpoints.py:23` (dépendance de routeur élargie)
- Modify: `ah2-admin-web/src/services/ToxicoGateway.js` (nouvelle méthode `searchPatients`)
- Modify: `ah2-admin-web/src/stores/toxicoStore.js` (nouvelle action `searchExistingPatients`)
- Modify: `ah2-admin-web/src/components/toxico/ToxicoAdmissionModal.vue` (étape de recherche)
- Test: `tests/test_patients_pagination.py` (le compte `Assistant` peut interroger `GET /patients/`)

**Interfaces:**
- Consumes: `GET /patients/?search=...` (déjà fiabilisé et paginé au chantier 5, enveloppe `{data,total,page,per_page,total_pages}`), Task 3's `POST /toxico/admission` avec `patientId` optionnel.
- Produces: `ToxicoGateway.searchPatients(query: string) -> Promise` ; `toxicoStore.searchExistingPatients(query: string) -> Promise<Array>`.

- [ ] **Step 1: Écrire le test backend qui échoue (élargissement de rôle)**

Ajouter à `tests/test_patients_pagination.py` :

```python
def test_assistant_peut_chercher_un_patient(db_session, api_client):
    """Chantier 6 : la personne qui admet en toxicologie (role Assistant,
    voir POST /toxico/admission) doit pouvoir chercher un patient existant
    avant l'admission. Avant cet ajout, le routeur /patients/ n'autorisait
    pas Assistant (403)."""
    create_test_user(db_session, "b6_assistant", "Assistant", password=TEST_PASSWORD)
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "b6_assistant", TEST_PASSWORD)

    reponse = client.get("/patients/?search=test", headers=headers)

    assert reponse.status_code == 200
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `pytest tests/test_patients_pagination.py::test_assistant_peut_chercher_un_patient -v`
Expected: FAIL (403 — `Assistant` n'est pas dans la liste du routeur)

- [ ] **Step 3: Élargir la dépendance de routeur**

Dans `api_backend/backend_app/routes/patients/patients_endpoints.py`, ligne 23, remplacer :

```python
    dependencies=[Depends(role_required("medecin", "nurse","secretaire","admin","manager"))]
```

par :

```python
    dependencies=[Depends(role_required("medecin", "nurse","secretaire","admin","manager","assistant"))]
```

(élargissement minimal et directement justifié par le besoin de recherche de patient à l'admission toxico — distinct du nettoyage plus large des gardes de rôle `L4b-e` laissé hors périmètre de ce chantier)

- [ ] **Step 4: Lancer le test, vérifier qu'il passe**

Run: `pytest tests/test_patients_pagination.py -v`
Expected: PASS (tout le fichier, non régressé)

- [ ] **Step 5: Ajouter `searchPatients` au gateway**

Dans `ah2-admin-web/src/services/ToxicoGateway.js`, ajouter dans la section `// --- LECTURE ---`, après `getPatientDetails` :

```javascript
    async searchPatients(query) {
        if (!query || query.trim().length < 2) return { data: { data: [], total: 0 } };
        return api.get('/patients/', { params: { search: query.trim(), per_page: 8 } });
    },
```

- [ ] **Step 6: Ajouter l'action au store**

Dans `ah2-admin-web/src/stores/toxicoStore.js`, ajouter une action (près de `fetchPsychologists`) :

```javascript
    async function searchExistingPatients(query) {
        try {
            const response = await ToxicoGateway.searchPatients(query);
            return response.data.data || [];
        } catch (e) {
            console.error("Erreur recherche patient:", e);
            return [];
        }
    }
```

Ajouter `searchExistingPatients` à l'objet retourné par le store (`return { ..., searchExistingPatients }`).

- [ ] **Step 7: Ajouter l'étape de recherche dans la modale d'admission**

Dans `ah2-admin-web/src/components/toxico/ToxicoAdmissionModal.vue`, script : ajouter l'état et les fonctions de recherche, juste après la déclaration de `form` :

```javascript
const searchQuery = ref('');
const searchResults = ref([]);
const isSearching = ref(false);
const selectedExistingPatient = ref(null);
const showNewPatientForm = ref(false);

let searchTimeout = null;
const onSearchInput = () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        if (searchQuery.value.trim().length < 2) {
            searchResults.value = [];
            return;
        }
        isSearching.value = true;
        searchResults.value = await toxicoStore.searchExistingPatients(searchQuery.value);
        isSearching.value = false;
    }, 300);
};

const selectExistingPatient = (patient) => {
    selectedExistingPatient.value = patient;
    showNewPatientForm.value = false;
    searchResults.value = [];
};

const startNewPatient = () => {
    selectedExistingPatient.value = null;
    showNewPatientForm.value = true;
};
```

Dans le template, remplacer le contenu du premier bloc (`<div class="bg-gray-50 p-4 rounded-xl ...">`, actuellement lignes 19-100) par une étape de recherche précédant le formulaire patient existant :

```html
<div class="bg-gray-50 p-4 rounded-xl border border-gray-200">
    <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 border-b border-gray-200 pb-2">
        {{ t('toxico.admission.section_patient') }}
    </h4>

    <div v-if="!showNewPatientForm && !selectedExistingPatient" class="space-y-2">
        <input v-model="searchQuery" @input="onSearchInput" type="text"
               placeholder="Rechercher un patient existant (nom, code)..."
               class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
        <ul v-if="searchResults.length" class="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-48 overflow-y-auto">
            <li v-for="p in searchResults" :key="p.patient_id" @click="selectExistingPatient(p)"
                class="px-3 py-2 hover:bg-indigo-50 cursor-pointer text-sm">
                <span class="font-medium">{{ p.first_name }} {{ p.last_name }}</span>
                <span class="text-gray-500 ml-2">{{ p.code_patient }} — {{ p.birth_date }}</span>
            </li>
        </ul>
        <p v-if="isSearching" class="text-xs text-gray-400">Recherche...</p>
        <button type="button" @click="startNewPatient" class="text-sm text-indigo-600 font-medium hover:underline">
            + Nouveau patient
        </button>
    </div>

    <div v-if="selectedExistingPatient" class="flex items-center justify-between bg-indigo-50 border border-indigo-200 rounded-lg px-3 py-2">
        <span class="text-sm font-medium text-indigo-900">
            {{ selectedExistingPatient.first_name }} {{ selectedExistingPatient.last_name }} ({{ selectedExistingPatient.code_patient }})
        </span>
        <button type="button" @click="selectedExistingPatient = null" class="text-xs text-indigo-600 hover:underline">Changer</button>
    </div>

    <div v-if="showNewPatientForm" class="space-y-4 mt-3">
        <!-- contenu existant du formulaire nouveau patient (grid firstName/lastName, dob/mothersName, address/admissionDate, substance/psychologist, contact) inchange -->
    </div>
</div>
```

(le bloc marqué « contenu existant du formulaire nouveau patient » est exactement le contenu actuel des lignes 24-99 du template, déplacé tel quel sous ce nouveau `v-if`, aucun champ modifié)

- [ ] **Step 8: Adapter la validation et le payload**

Remplacer `isFormValid` :

```javascript
const isFormValid = computed(() => {
    const patientOk = selectedExistingPatient.value || (
        form.firstName.trim() && form.lastName.trim() && form.dob && form.mothersName.trim()
    );
    return patientOk &&
           form.admissionDate &&
           form.substance &&
           form.psychologist &&
           form.guardianName.trim() &&
           form.guardianContact.trim();
});
```

Dans `handleSubmit`, remplacer la construction de `payload` :

```javascript
    const payload = {
        admissionDate: form.admissionDate,
        substance: form.substance,
        psychologist: parseInt(form.psychologist, 10),
        guardianName: form.guardianName.trim(),
        guardianContact: form.guardianContact.trim(),
        consentFile: form.consentFile || "",
        notes: form.notes?.trim() || ""
    };

    if (selectedExistingPatient.value) {
        payload.patientId = selectedExistingPatient.value.patient_id;
    } else {
        payload.firstName = form.firstName.trim();
        payload.lastName = form.lastName.trim();
        payload.dob = form.dob;
        payload.mothersName = form.mothersName.trim();
        payload.address = form.address?.trim() || "";
        payload.contact = form.contact?.trim() || "";
    }
```

Retirer la validation de dates de naissance quand un patient existant est sélectionné (`if (!selectedExistingPatient.value) { ...validation dob/admissionDate... }`, en enveloppant le bloc de validation des dates déjà présent).

- [ ] **Step 9: Adapter le gateway pour un payload conditionnel**

Dans `ah2-admin-web/src/services/ToxicoGateway.js::admitPatient`, remplacer la validation obligatoire des champs patient et la construction du `FormData` :

```javascript
    async admitPatient(data) {
        const admissionDate = data.admissionDate;
        const psychologistId = data.psychologist;

        if (!admissionDate) {
            throw new Error("La date d'admission est requise.");
        }
        const psyIdNumber = Number(psychologistId);
        if (isNaN(psyIdNumber) || psyIdNumber <= 0) {
            throw new Error("L'ID du psychologue est invalide ou manquant.");
        }

        const formData = new FormData();

        if (data.patientId) {
            formData.append('patientId', data.patientId);
        } else {
            const dob = data.dob;
            if (!dob) throw new Error("La date de naissance est requise pour un nouveau patient.");
            if (new Date(dob) > new Date(admissionDate)) {
                throw new Error("La date de naissance ne peut pas être postérieure à la date d'admission.");
            }
            formData.append('firstName', data.firstName || '');
            formData.append('lastName', data.lastName || '');
            formData.append('dob', dob);
            formData.append('mothersName', data.mothersName || '');
            formData.append('address', data.address || '');
            formData.append('contact', data.contact || '');
        }

        formData.append('admissionDate', admissionDate);
        formData.append('substance', data.substance || '');
        formData.append('psychologist', psyIdNumber);
        formData.append('guardianName', data.guardianName || '');
        formData.append('guardianContact', data.guardianContact || '');
        formData.append('notes', data.notes || '');

        if (data.consentFile && data.consentFile instanceof File) {
            formData.append('consentFile', data.consentFile);
        }

        return api.post('/toxico/admission', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    },
```

- [ ] **Step 10: Vérification manuelle (pas de suite de tests frontend automatisée dans ce projet)**

Démarrer le backend (`uvicorn`) et le frontend (`npm run dev` dans `ah2-admin-web/`), se connecter avec un compte `Assistant`, ouvrir la modale d'admission toxico :
1. Chercher un patient existant par nom → vérifier que les résultats s'affichent et que la sélection masque le formulaire "nouveau patient".
2. Soumettre l'admission avec un patient sélectionné → vérifier en base (`SELECT COUNT(*) FROM patients WHERE ...`) qu'aucun nouveau patient n'a été créé et qu'un `toxico_dossiers` a bien été ajouté pour ce `patient_id`.
3. Cliquer "+ Nouveau patient" → vérifier que le formulaire complet réapparaît et que la création fonctionne comme avant (non-régression).

---

### Task 5: Dossier consolidé — backend

**Files:**
- Create: `controller/patient_dossier_controller.py`
- Create: `api_backend/backend_app/routes/patient_dossier/__init__.py`
- Create: `api_backend/backend_app/routes/patient_dossier/patient_dossier_endpoint.py`
- Modify: `api_backend/backend_app/main.py` (import + `include_router`)
- Modify: `controller/toxico_controller.py` (extraction de `serialize_dossier_details`)
- Modify: `api_backend/backend_app/routes/toxico/toxico_endpoint.py:79-139` (réutilise la méthode extraite, comportement inchangé)
- Test: `tests/test_patient_dossier.py` (nouveau fichier)

**Interfaces:**
- Consumes (tous déjà existants et vérifiés) :
  - `PatientController.get_patient(patient_id) -> Optional[dict]`
  - `PatientRepository.compute_domain_flags(patient_id) -> dict` (Tâche 1)
  - `MedicalRecordController.get_patient_dme_summary(patient_id) -> dict` (Tâche 1 : `flags` déjà calculés)
  - `MedicalRecordController.get_patient_history(patient_id) -> List[MedicalRecord]` (ORM)
  - `PrescriptionController.get_patient_prescriptions(patient_id, status=None) -> List[Prescription]` (ORM)
  - `LabController.get_patient_lab_history(patient_id) -> List[dict]` (déjà des dicts)
  - `ConsultationSpirituelController.list_for_patient(patient_id) -> List[ConsultationSpirituel]` (ORM)
  - `ToxicoController.get_dossier_details(patient_id) -> Optional[ToxicoDossier]` (ORM ou `None`)
  - `AuditRepository.log_user_action(current_user, resource_type, action_performed, resource_id=None, old_values=None, new_values=None, ip_address=None, details=None)` — **`details` n'est pas persisté** (voir Step 3, `AuditUserAction` n'a pas de colonne `details`, seul `UserAccessLog` en a une ; `log_user_action` l'ignore silencieusement, ligne 165 de `repositories/audit_repo.py`) : ce plan utilise `new_values` (colonne JSONB réelle) à la place.
  - `MedicalRecordResponse` (`api_backend/backend_app/routes/medical_records/schemas.py`), `PrescriptionResponse` (`.../prescription/prescriptions_schemas.py`), `ConsultationResponse` (`.../cs/schemas_cs.py`) — les trois ont `model_config = {"from_attributes": True}` / `ConfigDict(from_attributes=True)`, réutilisées ici pour convertir les listes ORM en JSON sûr sans dupliquer de logique de sérialisation.
- Produces: `PatientDossierController.get_full_dossier(patient_id) -> dict`, `ToxicoController.serialize_dossier_details(dossier) -> Optional[dict]`, `GET /patients/{patient_id}/dossier` — **consommé par la Tâche 6**.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `tests/test_patient_dossier.py` :

```python
from datetime import date

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patient_dossier import patient_dossier_endpoint
from models.medical_record import MedicalRecord
from models.toxico import ToxicoDossier
from models.audit import AuditUserAction
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def test_dossier_consolide_renvoie_les_domaines_et_journalise(db_session, api_client):
    """Un seul appel doit renvoyer patient + flags + tous les domaines,
    et journaliser la consultation (politique d'acces 2026-09-15 :
    ouverture large, tracabilite forte)."""
    medecin = create_test_user(db_session, "dossier_medecin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="Dossier")
    db_session.flush()
    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="TEST", diagnosis="RAS"))
    db_session.flush()

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "dossier_medecin", TEST_PASSWORD)

    reponse = client.get(f"/patients/{patient_id}/dossier", headers=headers)

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["patient"]["patient_id"] == patient_id
    assert corps["flags"]["is_clinical"] is True
    assert corps["flags"]["is_toxicology"] is False
    assert len(corps["historique_medical"]) == 1
    assert corps["dossier_toxico"] is None
    assert corps["domaines_indisponibles"] == []

    log = (
        db_session.query(AuditUserAction)
        .filter_by(resource_type="Patient", action_performed="VIEW_DOSSIER_COMPLET", resource_id=patient_id)
        .one_or_none()
    )
    assert log is not None, "la consultation du dossier complet doit etre journalisee (tracabilite forte)"


def test_dossier_consolide_tolere_l_echec_d_un_domaine(db_session, api_client, monkeypatch):
    """Un domaine en echec ne doit pas vider les autres - meme principe
    de tolerance aux pannes qu'au chantier 5."""
    medecin = create_test_user(db_session, "dossier_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="Dossier2")
    db_session.flush()

    from controller.lab_controller import LabController
    def echoue(self, patient_id):
        raise RuntimeError("panne simulee labo")
    monkeypatch.setattr(LabController, "get_patient_lab_history", echoue)

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "dossier_medecin2", TEST_PASSWORD)

    reponse = client.get(f"/patients/{patient_id}/dossier", headers=headers)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["historique_labo"] is None
    assert "historique_labo" in corps["domaines_indisponibles"]
    assert corps["patient"]["patient_id"] == patient_id, "les autres domaines restent disponibles"


def test_dossier_consolide_refuse_la_secretaire(db_session, api_client):
    """Politique d'acces 2026-09-15 : secretariat exclu du dossier complet."""
    create_test_user(db_session, "dossier_secretaire", "secretaire", password=TEST_PASSWORD)
    medecin_pour_patient = create_test_user(db_session, "dossier_medecin3", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin_pour_patient, first_name="Dossier3")
    db_session.flush()

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "dossier_secretaire", TEST_PASSWORD)

    reponse = client.get(f"/patients/{patient_id}/dossier", headers=headers)

    assert reponse.status_code == 403
```

- [ ] **Step 2: Lancer les tests, vérifier l'échec**

Run: `pytest tests/test_patient_dossier.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'api_backend.backend_app.routes.patient_dossier'`

- [ ] **Step 3: Extraire `serialize_dossier_details` dans `ToxicoController`**

Dans `controller/toxico_controller.py`, ajouter une méthode juste après `get_dossier_details` (ligne 93) :

```python
    def serialize_dossier_details(self, dossier) -> Optional[Dict[str, Any]]:
        """Serialise un ToxicoDossier ORM en dict JSON-safe. Extrait de
        l'ancien corps de GET /toxico/patients/{patient_id} (chantier 6) -
        reutilise a l'identique par cet endpoint et par le nouveau dossier
        consolide, pour ne pas dupliquer cette logique."""
        if not dossier:
            return None

        psy_name = "Non assigné"
        if dossier.psychologist:
            if hasattr(dossier.psychologist, "full_name"):
                psy_name = dossier.psychologist.full_name
            elif hasattr(dossier.psychologist, "username"):
                psy_name = dossier.psychologist.username
            else:
                psy_name = "Psychologue (Nom inconnu)"

        return {
            "dossier_id": dossier.id,
            "patient_id": dossier.patient_id,
            "code": dossier.patient.code_patient,
            "firstName": dossier.patient.first_name,
            "lastName": dossier.patient.last_name,
            "dob": dossier.patient.birth_date,
            "mothersName": getattr(dossier.patient, "mother_name", getattr(dossier.patient, "mothers_name", None)),
            "address": getattr(dossier.patient, "address", "Non renseignée"),
            "contact": getattr(dossier.patient, "contact_phone", getattr(dossier.patient, "contact", None)),
            "admissionDate": dossier.admission_date,
            "createdAt": dossier.created_at,
            "substance": dossier.substance,
            "currentPhase": dossier.current_phase,
            "relapseCount": dossier.relapse_count,
            "psychologist": psy_name,
            "guardianName": dossier.guardian_name,
            "guardianContact": dossier.guardian_contact,
            "consentFile": dossier.consent_file,
            "notes": dossier.notes_admission,
            "phaseHistory": sorted([
                {
                    "phase": h.phase,
                    "start_date": h.start_date,
                    "end_date": h.end_date,
                    "status": h.status,
                    "comments": h.comments
                } for h in dossier.phase_history
            ], key=lambda x: x['start_date'], reverse=True),
            "evaluations": [
                {
                    "id": e.id,
                    "created_at": e.created_at,
                    "decision": e.decision,
                    "observation": e.observation,
                    "recommendation": e.recommendation,
                    "phase_before": e.phase_before,
                    "phase_after": e.phase_after,
                    "is_relapse": e.is_relapse,
                    "evaluator_name": getattr(e.evaluator, "full_name", "Inconnu") if e.evaluator else "Inconnu"
                } for e in dossier.evaluations
            ]
        }
```

Dans `api_backend/backend_app/routes/toxico/toxico_endpoint.py`, remplacer le corps de `get_patient_detail` (lignes 84-139) :

```python
    dossier = ctrl.get_dossier_details(patient_id) 
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier Toxico introuvable")

    return ctrl.serialize_dossier_details(dossier)
```

- [ ] **Step 4: Lancer les tests toxico existants, vérifier la non-régression**

Run: `pytest tests/ -k toxico -v`
Expected: PASS (le comportement JSON de `/toxico/patients/{patient_id}` est identique, juste réorganisé)

- [ ] **Step 5: Créer `PatientDossierController`**

Créer `controller/patient_dossier_controller.py` :

```python
# controller/patient_dossier_controller.py
import logging
from typing import Any, Dict

from api_backend.backend_app.routes.medical_records.schemas import MedicalRecordResponse
from api_backend.backend_app.routes.prescription.prescriptions_schemas import PrescriptionResponse
from api_backend.backend_app.routes.cs.schemas_cs import ConsultationResponse

logger = logging.getLogger(__name__)


class PatientDossierController:
    """Compose les controleurs de domaine existants en une vue unifiee du
    dossier patient (chantier 6, registre L5). Ne duplique aucune logique
    metier des controleurs existants, les appelle directement - motif deja
    utilise dans ce projet (PrescriptionController prend deja
    patient_controller en dependance)."""

    def __init__(self, patient_ctrl, medical_ctrl, prescription_ctrl, lab_ctrl,
                 cs_ctrl, toxico_ctrl, audit_repo, current_user):
        self.patient_ctrl = patient_ctrl
        self.medical_ctrl = medical_ctrl
        self.prescription_ctrl = prescription_ctrl
        self.lab_ctrl = lab_ctrl
        self.cs_ctrl = cs_ctrl
        self.toxico_ctrl = toxico_ctrl
        self.audit_repo = audit_repo
        self.current_user = current_user
        self.session = patient_ctrl.session

    def get_full_dossier(self, patient_id: int) -> Dict[str, Any]:
        patient = self.patient_ctrl.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} introuvable")

        flags = self.patient_ctrl.repo.compute_domain_flags(patient_id)

        resultats: Dict[str, Any] = {}
        echecs = []
        for cle, appel in [
            ("resume_clinique", lambda: self.medical_ctrl.get_patient_dme_summary(patient_id)),
            ("historique_medical", lambda: [
                MedicalRecordResponse.model_validate(r).model_dump(mode="json")
                for r in self.medical_ctrl.get_patient_history(patient_id)
            ]),
            ("prescriptions", lambda: [
                PrescriptionResponse.model_validate(p).model_dump(mode="json")
                for p in self.prescription_ctrl.get_patient_prescriptions(patient_id)
            ]),
            ("historique_labo", lambda: self.lab_ctrl.get_patient_lab_history(patient_id)),
            ("historique_spirituel", lambda: [
                ConsultationResponse.model_validate(c).model_dump(mode="json")
                for c in self.cs_ctrl.list_for_patient(patient_id)
            ]),
            ("dossier_toxico", lambda: self.toxico_ctrl.serialize_dossier_details(
                self.toxico_ctrl.get_dossier_details(patient_id)
            )),
        ]:
            try:
                resultats[cle] = appel()
            except Exception:
                echecs.append(cle)
                resultats[cle] = None
                logger.exception(f"Echec chargement '{cle}' pour le dossier patient {patient_id}")

        # 'details' n'est pas une colonne de audit_user_actions (seul
        # UserAccessLog en a une) - log_user_action l'ignore en silence.
        # new_values (JSONB reel) porte l'information a la place.
        self.audit_repo.log_user_action(
            current_user=self.current_user,
            resource_type="Patient",
            resource_id=patient_id,
            action_performed="VIEW_DOSSIER_COMPLET",
            new_values={"domaines_en_echec": echecs} if echecs else None,
        )
        self.session.commit()

        return {
            "patient": patient,
            "flags": flags,
            **resultats,
            "domaines_indisponibles": echecs,
        }
```

- [ ] **Step 6: Créer le nouveau routeur**

Créer `api_backend/backend_app/routes/patient_dossier/__init__.py` (vide, même structure que `routes/finance/`).

Créer `api_backend/backend_app/routes/patient_dossier/patient_dossier_endpoint.py` :

```python
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api_backend.backend_app.database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from controller.auth_controller import AuthController
from controller.patient_controller import PatientController
from controller.medical_controller import MedicalRecordController
from controller.prescription_controller import PrescriptionController
from controller.lab_controller import LabController
from controller.cs_controller import ConsultationSpirituelController
from controller.toxico_controller import ToxicoController
from controller.patient_dossier_controller import PatientDossierController
from repositories.audit_repo import AuditRepository
from repositories.medical_repo import MedicalRecordRepository
from repositories.prescription_repo import PrescriptionRepository
from repositories.lab_repo import LabRepository
from repositories.cs_repo import ConsultationSpirituelRepository
from repositories.toxico_repo import ToxicoRepository

# Routeur separe de patients_endpoints.py : ce dernier porte une
# dependance de ROUTEUR (role_required(...)) qui s'ET-erait avec toute
# route ajoutee ici, restreignant l'acces a l'intersection des deux
# listes au lieu de leur union (chantier 6, meme constat qu'au chantier 5
# pour routes/finance/).
router = APIRouter(prefix="/patients", tags=["Dossier patient"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_patient_dossier_controller(
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientDossierController:
    auth_ctrl = AuthController(db_session=db)
    audit_repo = AuditRepository(db)
    patient_ctrl = PatientController(repo=auth_ctrl.patient_repo, current_user=current_user, audit_repo=audit_repo)
    medical_ctrl = MedicalRecordController(
        repo=MedicalRecordRepository(db), patient_controller=patient_ctrl,
        current_user=current_user, audit_repo=audit_repo,
    )
    prescription_ctrl = PrescriptionController(
        repo=PrescriptionRepository(db), patient_controller=patient_ctrl,
        current_user=current_user, audit_repo=audit_repo,
    )
    lab_ctrl = LabController(repo=LabRepository(db), current_user=current_user)
    cs_ctrl = ConsultationSpirituelController(
        repo=ConsultationSpirituelRepository(session=db), patient_controller=patient_ctrl,
        current_user=current_user,
    )
    toxico_ctrl = ToxicoController(
        repo=ToxicoRepository(session=db), patient_controller=patient_ctrl, current_user=current_user,
    )
    return PatientDossierController(
        patient_ctrl=patient_ctrl, medical_ctrl=medical_ctrl, prescription_ctrl=prescription_ctrl,
        lab_ctrl=lab_ctrl, cs_ctrl=cs_ctrl, toxico_ctrl=toxico_ctrl,
        audit_repo=audit_repo, current_user=current_user,
    )


@router.get(
    "/{patient_id}/dossier",
    response_model=Any,
    dependencies=[Depends(role_required(
        "medecin", "nurse", "psychologist", "spiritualcounsellor",
        "toxicomanager", "laborantin", "assistant", "admin", "promoteur",
    ))],
)
def get_patient_dossier(
    patient_id: int,
    ctrl: PatientDossierController = Depends(get_patient_dossier_controller),
):
    """Dossier consolide : les 6 domaines en un appel, tolerant aux pannes
    par domaine, journalise (politique d'acces 2026-09-15 - soignants +
    admin + promoteur, secretariat exclu, tracabilite forte)."""
    try:
        return ctrl.get_full_dossier(patient_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

- [ ] **Step 7: Enregistrer le routeur dans `main.py`**

Dans `api_backend/backend_app/main.py`, ajouter l'import après `from .routes.toxico import toxico_endpoint` (ligne 20) :

```python
from .routes.patient_dossier import patient_dossier_endpoint
```

Ajouter l'enregistrement après `app.include_router(toxico_endpoint.router)` :

```python
app.include_router(patient_dossier_endpoint.router)
```

- [ ] **Step 8: Lancer les tests, vérifier qu'ils passent**

Run: `pytest tests/test_patient_dossier.py -v`
Expected: PASS (3 tests)

- [ ] **Step 9: Vérifier la non-régression complète**

Run: `pytest tests/ -v`
Expected: PASS (aucune régression sur la suite complète)

---

### Task 6: Dossier consolidé — frontend

**Files:**
- Modify: `ah2-admin-web/src/stores/patientDossierStore.js`
- Modify: `ah2-admin-web/src/views/modules/patients/PatientDetailView.vue`

**Interfaces:**
- Consumes: `GET /patients/{id}/dossier` (Tâche 5), réponse `{patient, flags, resume_clinique, historique_medical, prescriptions, historique_labo, historique_spirituel, dossier_toxico, domaines_indisponibles}`.

- [ ] **Step 1: Remplacer `fetchDossierComplete` par un seul appel**

Dans `ah2-admin-web/src/stores/patientDossierStore.js`, remplacer l'état et `fetchDossierComplete` :

```javascript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '@/services/api'; 

export const usePatientDossierStore = defineStore('patientDossier', () => {
    
    // --- ÉTAT (STATE) ---
    const patientSummary = ref(null);
    const medicalHistory = ref([]);
    const prescriptionHistory = ref([]);
    const labHistory = ref([]);
    const spiritualHistory = ref([]);
    const toxicoDossier = ref(null);
    const domainesIndisponibles = ref([]);

    const isLoading = ref(false);
    const error = ref(null);

    // --- ACTIONS ---

    async function fetchDossierComplete(patientId) {
        isLoading.value = true;
        error.value = null;

        try {
            const { data } = await api.get(`/patients/${patientId}/dossier`);

            patientSummary.value = data.resume_clinique;
            medicalHistory.value = data.historique_medical || [];
            prescriptionHistory.value = data.prescriptions || [];
            labHistory.value = data.historique_labo || [];
            spiritualHistory.value = data.historique_spirituel || [];
            toxicoDossier.value = data.dossier_toxico;
            domainesIndisponibles.value = data.domaines_indisponibles || [];

            if (patientSummary.value) {
                patientSummary.value.flags = data.flags;
            }
        } catch (err) {
            console.error("Erreur chargement dossier:", err);
            error.value = "Impossible de charger le dossier complet.";
        } finally {
            isLoading.value = false;
        }
    }

    async function refreshMedicalHistory(patientId) {
        try {
            const res = await api.get(`/medical_records/patient/${patientId}/history`);
            medicalHistory.value = res.data || [];
            
            const sumRes = await api.get(`/medical_records/patient/${patientId}/dme_summary`);
            patientSummary.value = sumRes.data;
        } catch (err) {
            console.error("Erreur refresh medical:", err);
        }
    }

    // --- GETTERS (Inchangés) ---
    const isToxicology = computed(() => patientSummary.value?.flags?.is_toxicology || false);
    const isSpiritual = computed(() => patientSummary.value?.flags?.is_spiritual || false);
    const isClinical = computed(() => patientSummary.value?.flags?.is_clinical || false);
    const fullName = computed(() => patientSummary.value?.full_name || 'Patient Inconnu');
    const code = computed(() => patientSummary.value?.code || '-');
    const isDomaineIndisponible = (cle) => domainesIndisponibles.value.includes(cle);

    const vitals = computed(() => ({
        bp: patientSummary.value?.last_bp || '-',
        weight: patientSummary.value?.last_weight ? `${patientSummary.value.last_weight} kg` : '-',
        temp: patientSummary.value?.last_temp ? `${patientSummary.value.last_temp}°C` : '-',
        lastDate: patientSummary.value?.last_consultation_date 
            ? new Date(patientSummary.value.last_consultation_date).toLocaleDateString('fr-FR') 
            : '-'
    }));

    return {
        patientSummary,
        medicalHistory,
        prescriptionHistory,
        labHistory,
        spiritualHistory,
        toxicoDossier,
        domainesIndisponibles,
        isLoading,
        error,
        fetchDossierComplete,
        refreshMedicalHistory,
        isToxicology,
        isSpiritual,
        isClinical,
        fullName,
        code,
        vitals,
        isDomaineIndisponible
    };
});
```

(`refreshMedicalHistory` reste inchangé — appelé après une sauvegarde ponctuelle dans l'onglet MEDICAL, hors périmètre de ce chantier)

- [ ] **Step 2: Afficher "Indisponible" plutôt que vide, activer l'onglet TOXICO**

Dans `ah2-admin-web/src/views/modules/patients/PatientDetailView.vue`, remplacer le contenu du `<div v-if="currentTab === 'TOXICO'">` (lignes 91-101) :

```html
                <div v-if="currentTab === 'TOXICO'">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-bold text-gray-800 text-orange-600">
                            {{ t('medical.tabs.toxico_followup') }}
                        </h3>
                    </div>
                    <div v-if="dossierStore.isDomaineIndisponible('dossier_toxico')" class="bg-gray-50 p-4 rounded-lg border border-gray-200 text-gray-500 text-sm">
                        Indisponible pour le moment — réessayez plus tard.
                    </div>
                    <div v-else-if="dossierStore.toxicoDossier" class="bg-orange-50 p-4 rounded-lg border border-orange-200 space-y-2">
                        <p><span class="font-medium text-orange-800">Substance :</span> {{ dossierStore.toxicoDossier.substance }}</p>
                        <p><span class="font-medium text-orange-800">Phase actuelle :</span> {{ dossierStore.toxicoDossier.currentPhase }}</p>
                        <p><span class="font-medium text-orange-800">Psychologue :</span> {{ dossierStore.toxicoDossier.psychologist }}</p>
                        <p><span class="font-medium text-orange-800">Admission :</span> {{ dossierStore.toxicoDossier.admissionDate }}</p>
                    </div>
                    <div v-else class="text-sm text-gray-400">Aucun dossier toxicologie pour ce patient.</div>
                </div>
```

Ajouter un bandeau générique pour les autres onglets indisponibles, juste avant la fermeture du bloc `<div class="p-6">` (après la ligne 101) :

```html
                <div v-if="dossierStore.domainesIndisponibles.length" class="mt-4 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                    Certaines informations sont temporairement indisponibles : {{ dossierStore.domainesIndisponibles.join(', ') }}.
                </div>
```

- [ ] **Step 3: Vérification manuelle**

Démarrer backend + frontend, ouvrir un dossier patient avec des données dans plusieurs domaines (clinique + toxico par exemple, via l'admission testée en Tâche 4) :
1. Vérifier que les onglets MEDICAL/LABO/PHARMA/TOXICO affichent les bonnes données en un seul chargement réseau (onglet Réseau du navigateur : un seul appel `GET /patients/{id}/dossier` au lieu des 5 appels dispersés).
2. Vérifier que l'onglet TOXICO affiche désormais des données réelles (plus l'encart statique).
3. Se connecter avec un compte secrétariat, tenter d'ouvrir un dossier patient → vérifier un 403 sur l'appel réseau (le composant peut rester à améliorer côté message d'erreur, non bloquant pour ce chantier).
4. Vérifier en base que `audit_user_actions` reçoit bien une ligne `VIEW_DOSSIER_COMPLET` à chaque consultation de dossier.

---

## Self-Review

**1. Couverture de la spec :**
- Rattachement à un patient existant (Section 1) → Tâches 3-4. ✅
- Drapeaux calculés (Section 2) → Tâche 1. ✅
- Filtre B6 activé (Section 2) → Tâche 1. ✅
- Dossier consolidé + tolérance aux pannes + journalisation (Section 3) → Tâche 5. ✅
- Frontend dossier consolidé, onglet TOXICO réel (Section 3) → Tâche 6. ✅
- Rôle `promoteur` (Section 4) → Tâche 2. ✅
- Politique d'accès (soignants + admin + promoteur, secrétariat exclu) → testée explicitement en Tâche 5 (`test_dossier_consolide_refuse_la_secretaire`). ✅
- Correction du routeur séparé (post-approbation spec) → Tâche 5, Contraintes globales. ✅
- Exclusions explicites de la spec (dédoublonnage, gardes L4b-e, hors ligne) : aucune tâche n'y touche — vérifié fichier par fichier dans chaque tâche. ✅

**2. Scan de placeholders :** aucun "TBD"/"TODO" ; chaque étape de code contient le code réel à écrire, pas une description. Un point mérite d'être signalé explicitement plutôt que caché : le plan dévie de la lecture littérale du pseudocode de la spec (Section 3) sur deux points, tous deux vérifiés contre le code réel et documentés inline dans les tâches concernées — (a) la sérialisation des résultats ORM (`historique_medical`/`prescriptions`/`historique_spirituel`/`dossier_toxico`) via les schémas Pydantic existants et une méthode extraite de `ToxicoController`, la spec étant muette sur ce point ; (b) `details=` remplacé par `new_values=` dans l'appel `log_user_action`, `AuditUserAction` n'ayant pas de colonne `details` (vérifié dans `models/audit.py`) — sans ce changement, la traçabilité des échecs par domaine serait silencieusement perdue.

**3. Cohérence des types/signatures :** `compute_domain_flags` (Tâche 1) est appelée telle quelle en Tâche 5 (`self.patient_ctrl.repo.compute_domain_flags`). `ToxicoController.serialize_dossier_details` (introduite Tâche 5) a la même signature partout où elle est appelée (Tâche 5's `PatientDossierController`, et `toxico_endpoint.py` après extraction). `data["patient_id"]` (Tâche 3, backend) correspond exactement à `payload.patientId` → `formData.append('patientId', ...)` (Tâche 4, frontend) → `patientId: Optional[int] = Form(None)` (Tâche 3, endpoint). `PatientDossierController.__init__` (Tâche 5) prend exactement les 8 paramètres nommés utilisés par `get_patient_dossier_controller` dans le même fichier.
