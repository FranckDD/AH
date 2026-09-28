# Fenêtre médicale — périmètre patient et résultats labo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restreindre `medecin`/`nurse` (uniquement ces deux rôles) au périmètre clinique du dossier patient consolidé et des résultats de laboratoire, avec journalisation d'accès conservée, sans jamais dupliquer ni bloquer le suivi parallèle d'un même patient dans plusieurs services.

**Architecture:** Filtrage côté backend (jamais côté frontend seul) sur deux endpoints existants déjà utilisés par ces rôles — aucune nouvelle route de données, aucun nouveau paramètre côté appelant. Le seul ajout de surface est une route frontend dédiée dans `MedicalLayout.vue` qui remplace la navigation cassée vers l'écran labo.

**Tech Stack:** FastAPI + SQLAlchemy (backend), Vue 3 + Pinia + vue-router (frontend), pytest (tests backend).

**Spec:** `docs/superpowers/specs/2026-09-22-fenetre-medicale-perimetre-design.md`

## Global Constraints

- Le revirement de politique d'accès ne concerne QUE les rôles `medecin`/`nurse`. Aucun autre rôle (`laborantin`, `psychologist`, `spiritualcounsellor`, `toxicomanager`, `assistant`, `admin`, `promoteur`, `secretaire`) n'est touché par ce plan — leur comportement actuel doit rester identique, vérifié par des tests de non-régression explicites, pas seulement par omission.
- La journalisation d'accès existante (`AuditUserAction`, action `VIEW_DOSSIER_COMPLET`) est conservée intégralement, y compris pour un accès filtré.
- Aucune donnée n'est supprimée, dupliquée ou bloquée : `compute_domain_flags()` (`repositories/patient_repo.py:238-254`) reste la seule source de vérité sur les domaines d'un patient, inchangée. Ce plan ne touche qu'à ce qui est *renvoyé à l'appelant*, jamais à ce qui existe en base.
- Filtrage systématiquement côté serveur (jamais un simple masquage d'écran) : un appel API direct avec des paramètres manipulés (ex. `?status=pending`) doit produire le même résultat filtré qu'un usage normal de l'écran.
- Rôles identifiés via `current_user.roles` (liste de chaînes canoniques minuscules, déjà peuplée par `get_current_user`, `api_backend/backend_app/routes/auth/auth_endpoints.py:178`) — jamais une nouvelle logique de résolution de rôle.

---

### Task 1: Filtrage du dossier consolidé par domaine

**Files:**
- Modify: `controller/patient_dossier_controller.py:33-114` (méthode `get_full_dossier`)
- Modify: `tests/test_patient_dossier.py` (corriger une assertion existante devenue fausse, ajouter 2 tests)

**Interfaces:**
- Consomme : `self.current_user.roles` (liste de chaînes, déjà disponible sur l'objet passé au constructeur de `PatientDossierController`, voir `api_backend/backend_app/routes/patient_dossier/patient_dossier_endpoint.py:39-66`).
- Ne change aucune signature publique — `get_full_dossier(patient_id: int) -> Dict[str, Any]` reste identique, seul son contenu de retour varie selon le rôle appelant.

- [ ] **Step 1: Écrire les tests qui échouent**

Dans `tests/test_patient_dossier.py`, d'abord corriger l'assertion existante qui deviendra fausse (le test utilise déjà un compte `medecin` — avant ce chantier, `dossier_toxico` valait `None` par absence de données ; après, la clé doit être absente pour ce rôle, peu importe s'il y a des données) :

```python
def test_dossier_consolide_renvoie_les_domaines_et_journalise(db_session, api_client):
    """Un seul appel doit renvoyer patient + flags + tous les domaines
    cliniques, et journaliser la consultation (politique d'acces
    2026-09-15 : ouverture large, tracabilite forte). Le caller est
    medecin : depuis le 2026-09-22, dossier_toxico/historique_spirituel
    sont absents de la reponse pour ce role (voir test dedie plus bas),
    donc on ne les asserte plus ici comme presents-et-nuls."""
    medecin = create_test_user(db_session, "dossier_medecin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="Dossier")
    db_session.flush()
    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="free", diagnosis="RAS"))
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
    assert "dossier_toxico" not in corps
    assert "historique_spirituel" not in corps
    assert corps["domaines_indisponibles"] == []
    assert "is_clinical" not in corps["patient"]
    assert "is_toxicology" not in corps["patient"]
    assert "is_spiritual" not in corps["patient"]

    log = (
        db_session.query(AuditUserAction)
        .filter_by(resource_type="Patient", action_performed="VIEW_DOSSIER_COMPLET", resource_id=patient_id)
        .one_or_none()
    )
    assert log is not None, "la consultation du dossier complet doit etre journalisee (tracabilite forte)"
```

Ajouter à la fin du fichier deux nouveaux tests :

```python
def test_dossier_consolide_medecin_ne_voit_pas_toxico_ni_spirituel(db_session, api_client):
    """Coeur du chantier 2026-09-22 : un patient reellement suivi dans les
    3 domaines a la fois (aucun doublon, chantier 6) ne doit exposer que
    le clinique a un medecin/nurse - jamais toxico/spirituel, mais sans
    jamais bloquer leur EXISTENCE (verifiee via 'flags')."""
    from datetime import date
    from models.toxico import ToxicoDossier
    from models.consultation_spirituelle import ConsultationSpirituel

    medecin = create_test_user(db_session, "dossier_medecin_multi", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="Multi")
    db_session.flush()

    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="free", diagnosis="RAS"))
    db_session.add(ToxicoDossier(
        patient_id=patient_id, admission_date=date(2026, 1, 10), substance="Alcool",
    ))
    db_session.add(ConsultationSpirituel(
        patient_id=patient_id, created_by=medecin.user_id, created_by_name=medecin.username,
        type_consultation="Spiritual",
    ))
    db_session.flush()

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "dossier_medecin_multi", TEST_PASSWORD)

    reponse = client.get(f"/patients/{patient_id}/dossier", headers=headers)

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    # les 3 domaines existent reellement (verifie via flags, jamais efface)
    assert corps["flags"]["is_clinical"] is True
    assert corps["flags"]["is_toxicology"] is True
    assert corps["flags"]["is_spiritual"] is True
    # mais seul le clinique est expose au medecin
    assert len(corps["historique_medical"]) == 1
    assert "dossier_toxico" not in corps
    assert "historique_spirituel" not in corps


def test_dossier_consolide_admin_voit_toujours_tous_les_domaines(db_session, api_client):
    """Non-regression explicite : le revirement ne concerne QUE
    medecin/nurse. Meme patient multi-domaines que le test precedent,
    vu par un admin - les 5 domaines doivent rester presents (politique
    L5 du chantier 6, inchangee pour ce role)."""
    from datetime import date
    from models.toxico import ToxicoDossier
    from models.consultation_spirituelle import ConsultationSpirituel

    admin = create_test_user(db_session, "dossier_admin_multi", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="MultiAdmin")
    db_session.flush()

    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="free", diagnosis="RAS"))
    db_session.add(ToxicoDossier(
        patient_id=patient_id, admission_date=date(2026, 1, 10), substance="Alcool",
    ))
    db_session.add(ConsultationSpirituel(
        patient_id=patient_id, created_by=admin.user_id, created_by_name=admin.username,
        type_consultation="Spiritual",
    ))
    db_session.flush()

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "dossier_admin_multi", TEST_PASSWORD)

    reponse = client.get(f"/patients/{patient_id}/dossier", headers=headers)

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert "dossier_toxico" in corps
    assert corps["dossier_toxico"] is not None
    assert "historique_spirituel" in corps
    assert len(corps["historique_spirituel"]) == 1
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent pour la bonne raison**

Run: `python -m pytest tests/test_patient_dossier.py -v`
Expected: `test_dossier_consolide_renvoie_les_domaines_et_journalise` échoue sur `assert "dossier_toxico" not in corps` (la clé existe encore, valeur `None`) ; les deux nouveaux tests échouent de la même façon sur les nouvelles assertions `not in`.

- [ ] **Step 3: Implémenter le filtrage**

Dans `controller/patient_dossier_controller.py`, modifier la fin de `get_full_dossier` :

```python
        patient_sans_drapeaux_obsoletes = {
            k: v for k, v in patient.items()
            if k not in ("is_clinical", "is_toxicology", "is_spiritual")
        }

        # Revirement de politique (2026-09-22, decision utilisateur) :
        # medecin/nurse ne voient que le clinique dans le dossier
        # consolide - jamais toxico/spirituel, meme si le patient a ces
        # deux domaines. Cle absente de la reponse, pas juste a None :
        # un frontend qui checkait "if (dossier_toxico)" laisserait
        # passer une valeur null par erreur de logique, une cle absente
        # ne peut pas se confondre avec "pas encore de donnees". flags
        # reste toujours renvoye, a tous les roles - savoir qu'un
        # domaine existe reste cliniquement utile sans en exposer le
        # detail. La tracabilite (log_user_action ci-dessus) ne change
        # pas : un acces filtre reste un acces trace.
        roles = set(getattr(self.current_user, "roles", []) or [])
        est_medical_seul = bool(roles & {"medecin", "nurse"})

        reponse = {
            "patient": patient_sans_drapeaux_obsoletes,
            "flags": flags,
            **resultats,
            "domaines_indisponibles": echecs,
        }
        if est_medical_seul:
            reponse.pop("dossier_toxico", None)
            reponse.pop("historique_spirituel", None)
        return reponse
```

- [ ] **Step 4: Relancer les tests, vérifier qu'ils passent**

Run: `python -m pytest tests/test_patient_dossier.py -v`
Expected: 5 tests passent (3 existants + 2 nouveaux).

- [ ] **Step 5: Commit**

```bash
git add controller/patient_dossier_controller.py tests/test_patient_dossier.py
git commit -m "feat: restreindre le dossier consolide au clinique pour medecin/nurse"
```

---

### Task 2: Verrouillage des onglets patients par domaine

**Files:**
- Modify: `api_backend/backend_app/routes/patients/patients_endpoints.py:84,124` (décorateurs de `/patients/toxicology` et `/patients/spiritual/list`)
- Test: `tests/test_patients.py` (ajouter les tests)

**Interfaces:**
- Consomme : `role_required(*allowed_roles)` (déjà importé dans ce fichier, `api_backend/backend_app/routes/auth/auth_endpoints.py`).
- Aucune nouvelle interface produite.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/test_patients.py` :

```python
def test_medecin_refuse_sur_onglet_toxicologie(db_session, api_client):
    """Meme si medecin/nurse est deja restreint par defaut sur /patients/
    (registre B6, chantier 6), rien n'empechait aujourd'hui d'appeler
    directement /patients/toxicology - route sans garde de role propre."""
    create_test_user(db_session, "medecin_onglet_toxico", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "medecin_onglet_toxico", TEST_PASSWORD)

    resp = client.get("/patients/toxicology", headers=headers)

    assert resp.status_code == 403


def test_nurse_refuse_sur_onglet_spirituel(db_session, api_client):
    create_test_user(db_session, "nurse_onglet_spirituel", "nurse", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "nurse_onglet_spirituel", TEST_PASSWORD)

    resp = client.get("/patients/spiritual/list", headers=headers)

    assert resp.status_code == 403


def test_secretaire_toujours_autorisee_sur_onglet_spirituel(db_session, api_client):
    """Non-regression : seuls medecin/nurse sont exclus, secretaire garde
    l'acces existant (deja utilise par la fiche patient secretariat)."""
    create_test_user(db_session, "secretaire_onglet_spirituel", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "secretaire_onglet_spirituel", TEST_PASSWORD)

    resp = client.get("/patients/spiritual/list", headers=headers)

    assert resp.status_code == 200


def test_medecin_toujours_autorise_sur_onglet_clinique(db_session, api_client):
    """Non-regression : /patients/clinical reste ouvert a medecin - c'est
    son propre perimetre, jamais touche par ce chantier."""
    create_test_user(db_session, "medecin_onglet_clinique", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "medecin_onglet_clinique", TEST_PASSWORD)

    resp = client.get("/patients/clinical", headers=headers)

    assert resp.status_code == 200
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `python -m pytest tests/test_patients.py -k "onglet" -v`
Expected: `test_medecin_refuse_sur_onglet_toxicologie` et `test_nurse_refuse_sur_onglet_spirituel` échouent (200 reçu au lieu de 403 attendu). Les deux tests de non-régression passent déjà (rien à casser).

- [ ] **Step 3: Implémenter la restriction**

Dans `api_backend/backend_app/routes/patients/patients_endpoints.py`, modifier les deux décorateurs (le routeur garde `medecin, nurse, secretaire, admin, manager, assistant, ToxicoManager` en dépendance globale — la dépendance de route ci-dessous s'ET-e avec elle, ne la remplace jamais, même motif que le chantier `L4b-e`) :

```python
@router.get(
    "/toxicology", response_model=PatientListResponse,
    # Revirement de politique (2026-09-22) : medecin/nurse ne voient que
    # le clinique - cette liste par role etait ouverte a tout le monde
    # jusqu'ici (seul le routeur global protegeait), aucune garde propre.
    dependencies=[Depends(role_required("secretaire", "admin", "manager", "assistant", "ToxicoManager"))],
)
def list_toxicology_patients(
```

```python
@router.get(
    "/spiritual/list", response_model=PatientListResponse,
    dependencies=[Depends(role_required("secretaire", "admin", "manager", "assistant", "ToxicoManager"))],
)
def list_spiritual_patients_paginated(
```

`/clinical` (ligne 105-121) reste inchangé, sans dépendance de route ajoutée.

- [ ] **Step 4: Relancer les tests**

Run: `python -m pytest tests/test_patients.py -v`
Expected: tous les tests du fichier passent, y compris les 4 nouveaux.

- [ ] **Step 5: Commit**

```bash
git add api_backend/backend_app/routes/patients/patients_endpoints.py tests/test_patients.py
git commit -m "feat: exclure medecin/nurse des onglets patients toxico/spirituel"
```

---

### Task 3: Résultats de laboratoire — lecture seule, statut "complet" uniquement

**Files:**
- Modify: `controller/lab_controller.py` (méthodes `get_paginated_results` ligne 189, `get_result_detail` ligne 376, `get_patient_lab_history` ligne 617 ; nouvelle méthode privée `_est_medical_lecture_seule`)
- Modify: `api_backend/backend_app/routes/labo/lab_endpoints.py:193-199` (`get_result_detail`, mapper `PermissionError` → 403)
- Test: nouveau fichier `tests/test_lab_medical_scope.py`

**Interfaces:**
- Consomme : `self.user.roles` (liste de chaînes, déjà posé par `get_lab_controller`, `api_backend/backend_app/routes/labo/lab_endpoints.py:51-56`, lui-même alimenté par `get_current_user`).
- Produit : `LabController._est_medical_lecture_seule() -> bool`, réutilisée dans les 3 méthodes de lecture de ce fichier. Aucune méthode existante ne change de signature.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `tests/test_lab_medical_scope.py` :

```python
# tests/test_lab_medical_scope.py
import sys
import os
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from models.lab import Examen, LabResult
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "Correct123!"


def _creer_examen(db_session, code_suffix):
    examen = Examen(code=f"EX-{code_suffix}", nom="Glycémie", categorie="Biochimie", prix=1500)
    db_session.add(examen)
    db_session.flush()
    return examen


def _creer_resultat(db_session, patient_id, examen_id, status, code_suffix):
    r = LabResult(
        patient_id=patient_id,
        test_type="Glycémie",
        status=status,
        examen_id=examen_id,
        code_lab_patient=f"LAB-{code_suffix}-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(r)
    db_session.flush()
    return r


def test_medecin_ne_voit_que_les_resultats_completed_dans_historique(db_session, api_client):
    medecin = create_test_user(db_session, "lab_medecin_hist", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="LaboHist")
    examen = _creer_examen(db_session, "HIST1")
    _creer_resultat(db_session, patient_id, examen.id, "pending", "P")
    _creer_resultat(db_session, patient_id, examen.id, "completed", "C")
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_medecin_hist", TEST_PASSWORD)

    # Tentative explicite de contourner le filtre par le parametre - doit
    # etre ignoree, jamais respectee, pour ce role.
    resp = client.get("/labo/history/paginated?status=pending", headers=headers)

    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    statuses = {item["status"] for item in items}
    assert statuses == {"completed"}


def test_laborantin_voit_toujours_tous_les_statuts_dans_historique(db_session, api_client):
    """Non-regression : seul medecin/nurse est filtre."""
    laborantin = create_test_user(db_session, "lab_laborantin_hist", "laborantin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, laborantin, first_name="LaboHist2")
    examen = _creer_examen(db_session, "HIST2")
    _creer_resultat(db_session, patient_id, examen.id, "pending", "P2")
    _creer_resultat(db_session, patient_id, examen.id, "completed", "C2")
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_laborantin_hist", TEST_PASSWORD)

    resp = client.get("/labo/history/paginated?status=pending", headers=headers)

    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "pending"


def test_nurse_ne_voit_que_completed_dans_historique_patient(db_session, api_client):
    nurse = create_test_user(db_session, "lab_nurse_patient_hist", "nurse", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse, first_name="LaboPatientHist")
    examen = _creer_examen(db_session, "PATHIST")
    _creer_resultat(db_session, patient_id, examen.id, "partial", "PA")
    _creer_resultat(db_session, patient_id, examen.id, "completed", "CO")
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_nurse_patient_hist", TEST_PASSWORD)

    resp = client.get(f"/labo/patient/{patient_id}/history", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "completed"


def test_medecin_refuse_sur_detail_resultat_non_complet(db_session, api_client):
    medecin = create_test_user(db_session, "lab_medecin_detail", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="LaboDetail")
    examen = _creer_examen(db_session, "DET1")
    resultat = _creer_resultat(db_session, patient_id, examen.id, "pending", "D")
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_medecin_detail", TEST_PASSWORD)

    resp = client.get(f"/labo/results/{resultat.result_id}", headers=headers)

    assert resp.status_code == 403


def test_medecin_autorise_sur_detail_resultat_complet(db_session, api_client):
    medecin = create_test_user(db_session, "lab_medecin_detail_ok", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="LaboDetailOk")
    examen = _creer_examen(db_session, "DET2")
    resultat = _creer_resultat(db_session, patient_id, examen.id, "completed", "DOK")
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_medecin_detail_ok", TEST_PASSWORD)

    resp = client.get(f"/labo/results/{resultat.result_id}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


def test_laborantin_toujours_autorise_sur_detail_non_complet(db_session, api_client):
    """Non-regression explicite."""
    laborantin = create_test_user(db_session, "lab_laborantin_detail", "laborantin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, laborantin, first_name="LaboDetail3")
    examen = _creer_examen(db_session, "DET3")
    resultat = _creer_resultat(db_session, patient_id, examen.id, "pending", "D3")
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_laborantin_detail", TEST_PASSWORD)

    resp = client.get(f"/labo/results/{resultat.result_id}", headers=headers)

    assert resp.status_code == 200
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `python -m pytest tests/test_lab_medical_scope.py -v`
Expected: `test_medecin_ne_voit_que_les_resultats_completed_dans_historique`, `test_nurse_ne_voit_que_completed_dans_historique_patient`, `test_medecin_refuse_sur_detail_resultat_non_complet` échouent (statut `pending` encore visible, 200 reçu au lieu de 403). Les 3 tests de non-régression (`laborantin`) passent déjà.

- [ ] **Step 3: Implémenter le filtrage dans le contrôleur**

Dans `controller/lab_controller.py`, ajouter juste après `__init__` (ligne 21) :

```python
    def _est_medical_lecture_seule(self) -> bool:
        """medecin/nurse : lecture seule, uniquement les examens
        'completed' - decision utilisateur 2026-09-22 (chantier perimetre
        medical). laborantin/admin/ToxicoManager ne sont jamais concernes."""
        roles = set(getattr(self.user, "roles", []) or [])
        return bool(roles & {"medecin", "nurse"})
```

Modifier `get_paginated_results` (ligne 189) :

```python
    def get_paginated_results(self, page: int = 1, limit: int = 20, search: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère l'historique paginé et formaté pour le frontend.
        """
        if self._est_medical_lecture_seule():
            # Le parametre appelant est ignore pour ce role, jamais fusionne -
            # sinon un appel direct avec ?status=pending contournerait le
            # filtre malgre l'ecran qui ne l'exposerait jamais.
            status = "completed"

        # Sécurité : on évite les pages négatives ou zéro
        if page < 1:
```
(le reste de la méthode est inchangé)

Modifier `get_result_detail` (ligne 376) :

```python
    def get_result_detail(self, result_id: int) -> Optional[Dict]:
        """Récupère le dossier complet pour affichage/saisie."""
        r = self.repo.get_full_lab_result(result_id)
        if not r: return None

        if self._est_medical_lecture_seule() and r.status != "completed":
            raise PermissionError(
                "Ce resultat n'est pas encore complet - reserve au laboratoire."
            )

        details_out = []
```
(le reste de la méthode est inchangé)

Modifier `get_patient_lab_history` (ligne 617) :

```python
    def get_patient_lab_history(self, patient_id: int) -> List[Dict]:
        """Historique par patient."""
        results = self.repo.list_results_for_patient(patient_id)
        if self._est_medical_lecture_seule():
            results = [r for r in results if r.status == "completed"]
        return [{
```
(le reste de la méthode est inchangé)

- [ ] **Step 4: Mapper `PermissionError` en 403 dans l'endpoint**

Dans `api_backend/backend_app/routes/labo/lab_endpoints.py`, modifier `get_result_detail` (ligne 193-199) :

```python
@router.get("/results/{result_id}", response_model=Dict,
            dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager", "medecin", "nurse"))])
def get_result_detail(result_id: int, ctrl: LabController = Depends(get_lab_controller)):
    try:
        res = ctrl.get_result_detail(result_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not res:
        raise HTTPException(status_code=404, detail="Dossier introuvable.")
    return res
```

(`PermissionError` est une exception native Python, aucun nouvel import nécessaire.)

- [ ] **Step 5: Relancer les tests**

Run: `python -m pytest tests/test_lab_medical_scope.py -v`
Expected: 6 tests passent.

- [ ] **Step 6: Commit**

```bash
git add controller/lab_controller.py api_backend/backend_app/routes/labo/lab_endpoints.py tests/test_lab_medical_scope.py
git commit -m "feat: restreindre medecin/nurse aux resultats labo completes, lecture seule"
```

---

### Task 4: Écran labo dédié dans la fenêtre médicale

**Files:**
- Create: `ah2-admin-web/src/views/modules/labo/MedicalLabResults.vue`
- Modify: `ah2-admin-web/src/router/index.js` (nouvelle route `/medical/lab-results` ligne ~291 ; retirer `medecin`/`nurse` de `meta.roles` de la route `history` ligne 99)
- Modify: `ah2-admin-web/src/components/layout/MedicalLayout.vue:178-182` (entrée de menu)
- Modify: `ah2-admin-web/src/views/modules/labo/LabLayout.vue:73` (`canSeeHistory`, cohérence avec le retrait ci-dessus)
- Modify: `ah2-admin-web/src/i18n.js` (nouvelle clé `lab.nav.medical_results`, fr + en)

**Interfaces:**
- Consomme : `useLabStore()` (`fetchPaginatedHistory`, `fetchResultDetail`, `downloadPDF`, état `paginatedHistory`/`loading` — déjà utilisés à l'identique par `LabHistory.vue`, aucune méthode de store modifiée par cette tâche), `ResultDetailModal.vue` (déjà en lecture seule, aucune modification).
- Ne produit aucune interface consommée par une tâche suivante (dernière tâche du plan).

- [ ] **Step 1: Créer le composant dédié**

Créer `ah2-admin-web/src/views/modules/labo/MedicalLabResults.vue` — copie de `ah2-admin-web/src/views/modules/labo/LabHistory.vue` avec le sélecteur de statut retiré (il n'y a plus qu'une seule valeur possible côté serveur depuis la Tâche 3 — l'afficher permettrait de sélectionner "En attente" pour ne jamais rien voir, source de confusion) :

```vue
<template>
  <div class="max-w-7xl mx-auto p-6 space-y-6 animate-fade-in-up h-full flex flex-col">

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-col md:flex-row gap-4 items-center justify-between">
      <div class="relative flex-1 max-w-md">
          <MagnifyingGlassIcon class="w-5 h-5 text-gray-400 absolute left-3 top-3"/>
          <input
              v-model="filters.query"
              @input="handleSearch"
              type="text"
              placeholder="Rechercher un patient ou un code..."
              class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-xl focus:ring-indigo-500 focus:border-indigo-500 transition"
          >
      </div>

      <button @click="refresh" class="p-2 text-gray-500 hover:bg-gray-100 rounded-full transition" title="Actualiser">
        <ArrowPathIcon class="w-5 h-5" :class="{'animate-spin': store.loading}"/>
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col">
      <div class="overflow-y-auto flex-1">
        <table class="w-full text-sm text-left">
            <thead class="bg-gray-50 text-gray-500 uppercase font-bold text-xs border-b border-gray-100 sticky top-0 z-10">
            <tr>
                <th class="px-6 py-4">Date & ID</th>
                <th class="px-6 py-4">Patient</th>
                <th class="px-6 py-4">Examen</th>
                <th class="px-6 py-4 text-center">Actions</th>
            </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
            <tr v-for="res in store.paginatedHistory.items" :key="res.result_id" class="hover:bg-gray-50 transition group">
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-gray-900 font-medium">{{ formatDate(res.test_date) }}</div>
                    <div class="text-[10px] text-gray-400 font-mono">#{{ res.result_id }} <span v-if="res.code">| {{ res.code }}</span></div>
                </td>

                <td class="px-6 py-4">
                    <div class="font-bold text-gray-800">{{ res.patient_name }}</div>
                    <div class="flex gap-2 mt-1">
                        <span class="text-[10px] text-gray-500">{{ res.patient_age }} • {{ res.patient_sexe }}</span>
                        <span v-if="res.is_external" class="text-[9px] bg-orange-50 text-orange-600 px-1.5 py-0.5 rounded font-black uppercase">Externe</span>
                    </div>
                </td>

                <td class="px-6 py-4 text-gray-600 font-medium">
                    {{ res.examen_nom }}
                </td>

                <td class="px-6 py-4">
                    <div class="flex items-center justify-center gap-2">
                        <button
                            @click="openView(res)"
                            class="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition border border-transparent hover:border-indigo-100"
                            title="Voir les détails"
                        >
                            <EyeIcon class="w-5 h-5"/>
                        </button>

                        <button
                            @click="downloadPdf(res)"
                            class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition border border-transparent hover:border-red-100"
                            title="Télécharger PDF"
                        >
                            <PrinterIcon class="w-5 h-5"/>
                        </button>
                    </div>
                </td>
            </tr>
            </tbody>
        </table>

        <div v-if="store.paginatedHistory.items.length === 0 && !store.loading" class="flex flex-col items-center justify-center h-64 text-gray-400">
            <DocumentMagnifyingGlassIcon class="w-16 h-16 mb-2 opacity-20"/>
            <p class="font-medium">Aucun examen complet trouvé.</p>
            <p class="text-xs">Les examens en cours restent visibles uniquement par le laboratoire.</p>
        </div>
      </div>

      <div v-if="store.paginatedHistory.total_pages > 0" class="border-t border-gray-100 bg-gray-50 px-6 py-3 flex items-center justify-between">
          <div class="text-sm text-gray-500">
              Affichage de <span class="font-medium">{{ store.paginatedHistory.items.length }}</span> sur <span class="font-medium">{{ store.paginatedHistory.total_items }}</span> résultats
          </div>
          <div class="flex items-center space-x-2 text-sm">
              <button
                  @click="prevPage"
                  :disabled="filters.page === 1"
                  class="px-3 py-1 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                  Précédent
              </button>
              <span class="px-3 py-1 text-gray-600 font-medium">
                  Page {{ store.paginatedHistory.current_page }} / {{ store.paginatedHistory.total_pages }}
              </span>
              <button
                  @click="nextPage"
                  :disabled="filters.page >= store.paginatedHistory.total_pages"
                  class="px-3 py-1 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                  Suivant
              </button>
          </div>
      </div>
    </div>

    <ResultDetailModal
        v-if="selectedResult"
        :result="selectedResult"
        @close="selectedResult = null"
        @print="downloadPdf"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useLabStore } from '@/stores/labStore';
import ResultDetailModal from '@/components/lab/ResultDetailModal.vue';
import dayjs from 'dayjs';
import debounce from 'lodash/debounce';
import {
    MagnifyingGlassIcon, ArrowPathIcon, PrinterIcon,
    DocumentMagnifyingGlassIcon, EyeIcon
} from '@heroicons/vue/24/outline';

// Vue dediee medecin/nurse (chantier perimetre medical, 2026-09-22) - pas
// de selecteur de statut : le backend (controller/lab_controller.py,
// Tache 3 de ce meme plan) force deja "completed" pour ce role, quel que
// soit le parametre envoye. L'afficher laisserait croire qu'on peut choisir
// "en attente" pour ne jamais rien voir.
const store = useLabStore();
const selectedResult = ref(null);

const filters = ref({
    query: '',
    page: 1,
    limit: 15
});

const fetchData = async () => {
    const q = filters.value.query;
    if (q.length === 1) return;

    await store.fetchPaginatedHistory({
        page: filters.value.page,
        limit: filters.value.limit,
        search: q.length >= 2 ? q : null,
    });
};

const handleSearch = debounce(() => {
    filters.value.page = 1;
    fetchData();
}, 400);

const nextPage = () => {
    if (filters.value.page < store.paginatedHistory.total_pages) {
        filters.value.page++;
        fetchData();
    }
};

const prevPage = () => {
    if (filters.value.page > 1) {
        filters.value.page--;
        fetchData();
    }
};

const refresh = () => {
    filters.value.query = '';
    filters.value.page = 1;
    fetchData();
};

const openView = async (item) => {
    const detail = await store.fetchResultDetail(item.result_id);
    if (detail) {
        selectedResult.value = detail;
    }
};

const downloadPdf = async (item) => {
    const filename = `Resultat_${item.result_id}.pdf`;
    await store.downloadPDF(item.result_id, filename);
};

const formatDate = (d) => {
    if (!d) return 'N/A';
    return dayjs(d).format('DD/MM/YYYY HH:mm');
};

onMounted(() => {
    fetchData();
});
</script>

<style scoped>
.animate-fade-in-up {
  animation: fadeInUp 0.4s ease-out;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
```

- [ ] **Step 2: Ajouter la route dédiée, retirer medecin/nurse de l'ancienne**

Dans `ah2-admin-web/src/router/index.js`, à l'intérieur du bloc `/medical` (après l'enfant `consultations`, avant la fermeture du tableau `children`, vers la ligne 291) :

```javascript
      {
        path: 'consultations',
        name: 'medical-consultations',
        component: () => import('@/views/modules/consultations/ConsultationsList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
      {
        path: 'lab-results',
        name: 'medical-lab-results',
        component: () => import('@/views/modules/labo/MedicalLabResults.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      }
    ]
  },
```

Dans le même fichier, retirer `medecin`/`nurse` de la route `history` existante (ligne 94-100 — ce shell (`MainLayout` → `LabLayout`) n'est plus le chemin de ces deux rôles, ils ont désormais leur propre vue) :

```javascript
            // 3. HISTORIQUE
            {
                path: 'history',
                name: 'lab-history',
                component: () => import('@/views/modules/labo/LabHistory.vue'),
                meta: { requiresAuth: true, roles: ['admin', 'laborantin', 'ToxicoManager'] }
            },
```

- [ ] **Step 3: Mettre à jour le menu de la fenêtre médicale**

Dans `ah2-admin-web/src/components/layout/MedicalLayout.vue`, remplacer l'entrée (lignes 178-182) :

```javascript
  {
    path: '/dashboard/labo/history',
    labelKey: 'lab.nav.history',
    icon: BeakerIcon,
  },
```

par :

```javascript
  {
    path: '/medical/lab-results',
    labelKey: 'lab.nav.medical_results',
    icon: BeakerIcon,
  },
```

- [ ] **Step 4: Aligner l'onglet de `LabLayout.vue`**

Dans `ah2-admin-web/src/views/modules/labo/LabLayout.vue`, ligne 73, retirer `medecin`/`nurse` de `canSeeHistory` (cohérence avec la route — ces deux rôles ne passent plus jamais par ce shell) :

```javascript
const canSeeHistory = computed(() => authStore.hasRole(['admin', 'laborantin', 'ToxicoManager']));
```

- [ ] **Step 5: Ajouter la clé i18n**

Dans `ah2-admin-web/src/i18n.js`, bloc `lab.nav` français (autour de la ligne 779-784) :

```javascript
      nav: {
        dashboard: "Tableau de Bord",
        entry: "Saisie Résultats",
        history: "Historique",
        medical_results: "Résultats d'examens",
        config: "Configuration"
      },
```

Bloc anglais (autour de la ligne 1635-1640) :

```javascript
      nav: {
        dashboard: "Dashboard",
        entry: "Result Entry",
        history: "History",
        medical_results: "Exam Results",
        config: "Configuration"
      },
```

- [ ] **Step 6: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi, aucune erreur.

- [ ] **Step 7: Commit**

```bash
git add ah2-admin-web/src/views/modules/labo/MedicalLabResults.vue ah2-admin-web/src/router/index.js ah2-admin-web/src/components/layout/MedicalLayout.vue ah2-admin-web/src/views/modules/labo/LabLayout.vue ah2-admin-web/src/i18n.js
git commit -m "feat: ecran labo dedie dans la fenetre medicale, corrige la navigation cassee"
```

---

## Vérification finale (hors tâches, à la charge du contrôleur après la dernière tâche)

- Relancer la suite complète (`python -m pytest tests/ -q`) et confirmer qu'aucun nouvel échec n'apparaît en dehors des échecs pré-existants déjà documentés dans `docs/superpowers/SUIVI-AVANCEMENT.md`.
- Vérifier manuellement (ou demander à l'utilisateur de vérifier) : depuis `MedicalLayout`, cliquer sur "Résultats d'examens" garde le menu médical visible (contrairement à l'ancien comportement).
