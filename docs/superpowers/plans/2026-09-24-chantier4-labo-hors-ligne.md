# Chantier 4, sous-projet 5 — Labo hors ligne — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre le rôle laborantin offline-first sur les écrans réception + paillasse + saisie, et corriger au passage un bug réel de production où les valeurs saisies dans `LabValidation.vue` ne sont jamais réellement sauvegardées (en ligne comme hors ligne).

**Architecture:** Même motif que les sous-projets 1-4 : écriture toujours locale (table PowerSync SQLite) pour `laborantin`, lecture HTTP d'abord avec secours local uniquement sur coupure réseau réelle (`!err.response`). `lab_results` gagne une colonne `uuid` (unique, résolution serveur des dossiers créés hors ligne) et `batch_uuid` (partagée, non unique, résolution du code LAB commun à un lot envoyé en plusieurs opérations CRUD séparées). Connecteur unique `DossierConnector.js` étendu avec 2 nouveaux cas (`lab_results:PUT`, `lab_result_details:PUT`).

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (Mapped/mapped_column) + Alembic côté backend ; Vue 3 (Options API pour `labStore.js`, Composition API pour les autres) + Pinia + PowerSync Web SDK côté frontend.

**Spec:** `docs/superpowers/specs/2026-09-24-chantier4-labo-hors-ligne-design.md`

## Global Constraints

- Aucun commit git — snapshots avant/après (`cp` vers `task-N-before/`) et `diff -u` pour chaque revue de tâche, jamais `git diff` (ce dépôt ne committe jamais dans cette session).
- Travail direct sur le répertoire principal — pas de worktree.
- Migration réelle appliquée uniquement après accord explicite de l'utilisateur via `AskUserQuestion` — jamais automatiquement, même si la tâche 1 est "terminée" au sens du code.
- Jamais deux subagents implémenteurs en parallèle.
- Alias `FROM <source> AS <table_locale>` obligatoire dans `sync-config.yaml` partout où les noms diffèrent.
- Identifiant de révision Alembic ≤ 32 caractères.
- Toute référence à une entité créée dans le même lot hors ligne (patient, dossier labo) doit être résolue par `uuid` côté serveur dès la conception — jamais un `server_id` local en attente d'un re-téléchargement.
- Un seul code LAB partagé par réception à plusieurs examens (comportement actuel en ligne, à préserver hors ligne).
- Interprétation (normal/anormal), calcul de statut final (`completed`/`partial`) : toujours calculés côté serveur, jamais dupliqués côté client.
- Réception ET saisie hors ligne, y compris enchaînées dans le même geste (dossier reçu hors ligne, saisi hors ligne avant toute reconnexion).
- Patients internes ET externes enregistrables hors ligne à la réception.
- Vérifier `docker ps` (conteneurs `powersync-*` stables) avant tout test manuel réel. Test manuel = vraie coupure réseau (arrêter le serveur), jamais DevTools.

---

## File Structure

Backend :
- `alembic/versions/012_lab_results_uuid_batch_uuid.py` (nouveau) — migration `uuid`/`batch_uuid`.
- `models/lab.py` — `LabResult` gagne `uuid`, `batch_uuid`.
- `repositories/lab_repo.py` — `create_lab_result` gère `uuid`/`batch_uuid` ; nouvelles méthodes `get_lab_result_by_uuid`, `get_lab_result_by_batch_uuid` ; `save_results_values` accepte des clés `parametre_id` en plus de `detail_id`.
- `api_backend/backend_app/utils/patient_resolution.py` — nouvelles fonctions `resolve_lab_result_id`, `resolve_lab_result_id_from_path`.
- `api_backend/backend_app/routes/labo/labo_schemas.py` — `BatchItem` gagne `uuid` ; `BatchResultCreate` gagne `patient_uuid`, `origin_prescription_id`, `batch_uuid` ; validateur assoupli.
- `controller/lab_controller.py` — `create_batch_results` réécrit (résolution par `batch_uuid`, idempotence par `uuid`).
- `api_backend/backend_app/routes/labo/lab_endpoints.py` — `POST /results/batch` transmet les nouveaux champs (déjà automatique via `model_dump()`) ; `PUT /results/{result_id}/values` accepte un id textuel (`int` ou `uuid`).

Frontend :
- `ah2-admin-web/src/views/modules/labo/LabValidation.vue` — corrige l'appel à `saveValues` (2 args, payload structuré).
- `ah2-admin-web/src/stores/labStore.js` — `saveValues` corrigé (signature + forme du payload) ; branches locales `laborantin` pour `createBatchRequest`, `fetchDashboardData`/`fetchWorklist`/`fetchPaillasseList`, `fetchResultDetail`, `saveValues`.
- `ah2-admin-web/src/stores/auth.js`, `ah2-admin-web/src/App.vue` — garde `connectPowerSync` étendue à `laborantin`.
- `ah2-admin-web/src/powersync-client/client.js` — 5 nouveaux streams souscrits pour `laborantin`, + réutilisation `patients_lookup`/`doctors_lookup`/`reference_exam_catalog`.
- `ah2-admin-web/src/powersync-client/AppSchema.js` — `lab_results` gagne des colonnes d'écriture ; nouvelles tables `lab_result_details`, `lab_pending_prescriptions`, `reference_lab_params`, `reference_lab_ranges`.
- `powersync/sync-config.yaml` — 5 nouveaux streams.
- `ah2-admin-web/src/services/labGateway.js` — secours local sur `searchInternalPrescriptions`, `createBatchResults`, `getResultDetail`, `updateResultValues`, `getWorklist`, `getPaillasseList`.
- `ah2-admin-web/src/views/modules/labo/LabReception.vue` — envoie `uuid`/`batch_uuid`/`origin_prescription_id` (renommage `prescription_id` → `origin_prescription_id`).
- `ah2-admin-web/src/powersync-client/DossierConnector.js` — cas `lab_results:PUT`, `lab_result_details:PUT`.
- `ah2-admin-web/src/powersync-client/syncQuarantine.js` — `isLabResultQuarantined`.
- `ah2-admin-web/src/views/sync/SyncFailuresView.vue` — affichage des dossiers labo en quarantaine (extension d'un écran existant, pas de nouveau composant).

---

### Task 1: Migration `lab_results.uuid` + `batch_uuid`

**Files:**
- Create: `alembic/versions/012_lab_results_uuid_batch_uuid.py`
- Modify: `ci/schema_only.sql` (régénéré après application — voir Step 4)

**Interfaces:**
- Produces: colonne `lab_results.uuid` (UUID, `DEFAULT gen_random_uuid()`, index unique `ix_lab_results_uuid`) ; colonne `lab_results.batch_uuid` (VARCHAR(36), nullable, index non unique `ix_lab_results_batch_uuid`). Toutes les tâches backend suivantes en dépendent.

- [ ] **Step 1: Écrire la migration**

```python
"""lab_results uuid + batch_uuid

Revision ID: 012_lab_results_uuid
Revises: 011_medrec_uuid_unique
Create Date: 2026-09-24

"""
from alembic import op
import sqlalchemy as sa

revision = '012_lab_results_uuid'
down_revision = '011_medrec_uuid_unique'
branch_labels = None
depends_on = None


def upgrade():
    # Étape 1 : colonne nullable d'abord (les lignes existantes n'ont pas
    # encore de valeur) - même motif que la migration 009 (caisse.uuid).
    op.add_column('lab_results', sa.Column('uuid', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE lab_results SET uuid = gen_random_uuid() WHERE uuid IS NULL")
    op.alter_column('lab_results', 'uuid', nullable=False, server_default=sa.text('gen_random_uuid()'))
    op.create_index('ix_lab_results_uuid', 'lab_results', ['uuid'], unique=True)

    # batch_uuid : volontairement NON unique (partagé par toutes les lignes
    # d'une même réception à plusieurs examens - voir spec section 2).
    op.add_column('lab_results', sa.Column('batch_uuid', sa.String(length=36), nullable=True))
    op.create_index('ix_lab_results_batch_uuid', 'lab_results', ['batch_uuid'], unique=False)


def downgrade():
    op.drop_index('ix_lab_results_batch_uuid', table_name='lab_results')
    op.drop_column('lab_results', 'batch_uuid')
    op.drop_index('ix_lab_results_uuid', table_name='lab_results')
    op.drop_column('lab_results', 'uuid')
```

- [ ] **Step 2: Vérifier la longueur de l'id de révision**

Run: `python -c "print(len('012_lab_results_uuid'))"`
Expected: `21` (≤ 32 — sinon l'`UPDATE` final d'Alembic sur `alembic_version.version_num` (`varchar(32)`) échoue silencieusement en fin de transaction, piège déjà rencontré aux migrations 010/011).

- [ ] **Step 3: NE PAS appliquer la migration contre la base réelle**

La migration reste à l'état de fichier jusqu'à l'accord explicite de l'utilisateur (règle projet). Ne pas lancer `alembic upgrade head` dans cette tâche — cette étape est différée à la Tâche 11 (vérification finale), après accord.

- [ ] **Step 4: Régénérer `ci/schema_only.sql` UNIQUEMENT après application réelle**

Rappel pour la Tâche 11 : `ci/schema_only.sql` doit refléter le schéma réel après migration, sinon le CI diverge silencieusement de la base de développement (leçon déjà rencontrée sur la migration 003). Ne rien faire ici — ce Step documente juste où ce sera fait.

---

### Task 2: Backend — modèle et dépôt (`create_lab_result`, résolutions)

**Files:**
- Modify: `models/lab.py` (classe `LabResult`, après la ligne `batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True)`)
- Modify: `repositories/lab_repo.py` (`create_lab_result` lignes 228-308 ; `save_results_values` ligne ~389)
- Test: `tests/test_lab_repo.py` (nouveau si absent, sinon complété)

**Interfaces:**
- Consumes: `LabResult` (models/lab.py), session SQLAlchemy passée au constructeur `LabRepository(session)`.
- Produces: `LabRepository.create_lab_result(data: dict) -> LabResult` accepte désormais des clés `uuid` (str/UUID optionnelle) et `batch_uuid` (str optionnelle) dans `data`. `LabRepository.get_lab_result_by_uuid(client_uuid: str) -> Optional[LabResult]`. `LabRepository.get_lab_result_by_batch_uuid(batch_uuid: str) -> Optional[LabResult]`. `LabRepository.save_results_values(result_id, values, completed, note)` accepte désormais, pour chaque clé de `values`, soit un `detail_id` réel soit un `parametre_id` (résolution par tentative, voir Step 3).

- [ ] **Step 1: Ajouter les colonnes au modèle**

Dans `models/lab.py`, juste après la ligne `batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True)` (ligne 77) :

```python
    # uuid : identite stable connue AVANT confirmation serveur (genere par
    # le client hors ligne) - permet la resolution idempotente d'un dossier
    # cree hors ligne (voir get_lab_result_by_uuid). batch_uuid : identite
    # de LOT generee par le client, volontairement PARTAGEE par toutes les
    # lignes d'une meme reception a plusieurs examens - permet de retrouver
    # "un autre item de ce lot a-t-il deja ete cree ?" quand chaque ligne
    # part dans sa propre operation CRUD PowerSync (voir get_lab_result_by_batch_uuid,
    # remplace la logique "le premier de la boucle genere, les suivants
    # reutilisent" qui supposait un seul appel HTTP synchrone).
    uuid: Mapped[Optional["uuid.UUID"]] = mapped_column(UUID(as_uuid=True), unique=True, nullable=True)
    batch_uuid: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
```

- [ ] **Step 2: Modifier `create_lab_result` pour gérer `uuid`**

Dans `repositories/lab_repo.py`, remplacer le début de `create_lab_result` :

```python
    def create_lab_result(self, data: Dict[str, Any]) -> LabResult:
        details_data = data.pop('details', [])
        client_uuid = data.pop('uuid', None)
        passed_code = data.get('code_lab_patient')
        try:
            if not data.get('test_type'):
                data['test_type'] = "Analyse Labo"

            if not passed_code:
                data['code_lab_patient'] = "TEMP_GENERATING"

            result = LabResult(**data)
            self.session.add(result)
            self.session.flush()

            # Explicite APRES flush uniquement : un uuid=None passe au
            # constructeur ecraserait le DEFAULT gen_random_uuid() de la
            # colonne (piege deja documente sur patients/medical_records/
            # prescriptions - Postgres traite une valeur explicitement NULL
            # differemment d'une colonne absente).
            if client_uuid:
                result.uuid = uuid.UUID(str(client_uuid))

            if result.code_lab_patient == "TEMP_GENERATING":
```

(le reste de la méthode, à partir de `is_external = (result.patient_id is None)`, ne change pas.)

- [ ] **Step 3: Ajouter les deux méthodes de résolution**

Dans `repositories/lab_repo.py`, juste après `create_lab_result` (avant `get_full_lab_result` ou la méthode suivante) :

```python
    def get_lab_result_by_uuid(self, client_uuid: str) -> Optional[LabResult]:
        """Rejeu idempotent d'un dossier labo cree hors ligne - meme motif
        que la resolution patient/consultation par uuid (chantier 4 sous-
        projet 4)."""
        return self.session.query(LabResult).filter(
            LabResult.uuid == uuid.UUID(str(client_uuid))
        ).first()

    def get_lab_result_by_batch_uuid(self, batch_uuid: str) -> Optional[LabResult]:
        """Premier dossier deja cree pour ce lot hors ligne (batch_uuid
        client) - permet de reutiliser le meme code_lab_patient quand les
        items d'un meme lot arrivent dans des appels HTTP separes (chaque
        ligne locale genere sa propre operation d'envoi PowerSync,
        contrairement a la creation en ligne qui envoie tout le lot en un
        seul appel synchrone)."""
        return self.session.query(LabResult).filter(
            LabResult.batch_uuid == batch_uuid
        ).order_by(LabResult.result_id.asc()).first()
```

- [ ] **Step 4: Rendre `save_results_values` tolérant à des clés `parametre_id`**

Lire d'abord `repositories/lab_repo.py::save_results_values` en entier (lignes ~389-460) pour situer la boucle qui itère `values.items()` et résout chaque `detail_id`. Modifier cette résolution : pour chaque `key, value` de `values.items()`, chercher d'abord une `LabResultDetail` par `detail_id == int(key) AND result_id == result_id` (comportement actuel, préserve la compatibilité avec tout appelant en ligne existant) ; si aucune ligne trouvée, chercher par `result_id == result_id AND parametre_id == int(key)` (nouveau — cas d'un dossier créé hors ligne où le client ne connaît jamais le `detail_id` serveur généré à la création, seulement le `parametre_id`, comme prévu par l'Approche A de la spec). Si aucune des deux résolutions n'aboutit, ignorer cette entrée (`continue`) plutôt que lever une exception — une valeur orpheline (paramètre retiré du catalogue entre-temps) ne doit jamais faire échouer tout le dossier.

```python
        for key, value in (values or {}).items():
            try:
                key_int = int(key)
            except (TypeError, ValueError):
                continue
            detail = self.session.query(LabResultDetail).filter(
                LabResultDetail.detail_id == key_int,
                LabResultDetail.result_id == result_id,
            ).first()
            if not detail:
                detail = self.session.query(LabResultDetail).filter(
                    LabResultDetail.parametre_id == key_int,
                    LabResultDetail.result_id == result_id,
                ).first()
            if not detail:
                continue
            # ... suite inchangee : ecriture de valeur_text/valeur_num,
            # interpretation via _interpret_single_detail, etc.
```

Adapter cette insertion au nom réel de la variable de boucle déjà présente dans le fichier (le corps existant après résolution du `detail` ne change pas — seule la façon de le trouver change).

- [ ] **Step 5: Test — idempotence + résolution par uuid/batch_uuid**

```python
# tests/test_lab_repo.py
import uuid
from repositories.lab_repo import LabRepository


def test_create_lab_result_stores_client_uuid(db_session):
    repo = LabRepository(db_session)
    client_uuid = str(uuid.uuid4())
    result = repo.create_lab_result({
        "uuid": client_uuid, "examen_id": 1, "patient_id": None,
        "external_patient_info": {"nom": "Externe Test"},
    })
    assert str(result.uuid) == client_uuid


def test_get_lab_result_by_uuid_roundtrip(db_session):
    repo = LabRepository(db_session)
    client_uuid = str(uuid.uuid4())
    created = repo.create_lab_result({
        "uuid": client_uuid, "examen_id": 1, "patient_id": None,
        "external_patient_info": {"nom": "Externe Test"},
    })
    found = repo.get_lab_result_by_uuid(client_uuid)
    assert found.result_id == created.result_id


def test_get_lab_result_by_batch_uuid_finds_sibling(db_session):
    repo = LabRepository(db_session)
    batch_uuid = str(uuid.uuid4())
    first = repo.create_lab_result({
        "uuid": str(uuid.uuid4()), "batch_uuid": batch_uuid, "examen_id": 1,
        "patient_id": None, "external_patient_info": {"nom": "Externe Test"},
    })
    sibling = repo.get_lab_result_by_batch_uuid(batch_uuid)
    assert sibling.result_id == first.result_id
```

- [ ] **Step 6: Exécuter les tests**

Run: `pytest tests/test_lab_repo.py -v`
Expected: PASS (adapter la fixture `db_session` au nom réel utilisé ailleurs dans `tests/` — vérifier `tests/conftest.py` si le nom diffère).

---

### Task 3: Backend — réception par lot hors ligne (schémas + contrôleur)

**Files:**
- Modify: `api_backend/backend_app/routes/labo/labo_schemas.py` (`BatchItem`, `BatchResultCreate`)
- Modify: `controller/lab_controller.py` (`create_batch_results`, import de `resolve_patient_id`)
- Modify: `ah2-admin-web/src/views/modules/labo/LabReception.vue` (renommage `prescription_id` → `origin_prescription_id`, ajout `uuid`/`batch_uuid`)
- Test: `tests/test_lab_endpoints.py` (complété)

**Interfaces:**
- Consumes: `LabRepository.get_lab_result_by_uuid`, `LabRepository.get_lab_result_by_batch_uuid`, `LabRepository.create_lab_result` (Task 2) ; `resolve_patient_id(session, patient_id, patient_uuid)` (déjà existant, `api_backend/backend_app/utils/patient_resolution.py`).
- Produces: `POST /labo/results/batch` accepte par item `{examen_id, value, note, uuid}` et globalement `{patient_id, patient_uuid, prescribed_by_id, prescribed_by_name, external_patient_info, origin_prescription_id, batch_uuid, results}`. Réponse inchangée `{success, count, shared_code, batch_id}`.

- [ ] **Step 1: Étendre les schémas**

Dans `api_backend/backend_app/routes/labo/labo_schemas.py`, remplacer `BatchItem` et `BatchResultCreate` :

```python
class BatchItem(BaseModel):
    """
    Représente une demande d'examen dans le panier.
    On ne demande PAS la valeur ici, car l'examen n'est pas encore fait.
    """
    examen_id: int  # Doit correspondre exactement à ce que le JS envoie
    value: Optional[Union[float, str]] = None
    note: Optional[str] = None # Optionnel : note spécifique à cet examen
    # uuid genere par le client (hors ligne) - permet le rejeu idempotent
    # d'un item deja envoye (meme motif que patients.uuid). Absent en ligne.
    uuid: Optional[UUID] = None

class BatchResultCreate(BaseModel):
    """
    Le payload reçu du Frontend pour une demande multiple.
    """
    patient_id: Optional[int] = None
    # patient_uuid : patient interne cree hors ligne dans le meme geste,
    # pas encore de patient_id cote client (chantier 4 sous-projet 5, meme
    # motif que consultation/prescription au sous-projet 4).
    patient_uuid: Optional[UUID] = None
    prescribed_by_id: Optional[int] = None
    prescribed_by_name: Optional[str] = None
    external_patient_info: Optional[Dict[str, Any]] = None
    # Prescription medicale source (worklist medecin) - propage l'exclusion
    # cote get_lab_worklist() une fois le dossier cree. Jusqu'ici jamais
    # effectivement lu par le backend malgre son envoi depuis LabReception.vue
    # (bug reel corrige dans ce chantier, hors perimetre hors-ligne).
    origin_prescription_id: Optional[int] = None
    # batch_uuid : identite de lot generee par le client hors ligne,
    # volontairement PARTAGEE par tous les items de cette reception -
    # permet de retrouver le code LAB deja attribue a un item-frere envoye
    # dans une operation CRUD separee (chaque ligne locale = son propre
    # appel HTTP hors ligne, contrairement a l'envoi synchrone en ligne).
    batch_uuid: Optional[str] = None

    # Liste des examens (ex: [ {examen_id: 1}, {examen_id: 5} ])
    results: List[BatchItem]

    @model_validator(mode='after')
    def check_patient_exists(self):
        if not self.patient_id and not self.patient_uuid and not self.external_patient_info:
            raise ValueError("Un patient_id, patient_uuid ou external_patient_info est requis.")
        return self
```

- [ ] **Step 2: Réécrire `create_batch_results`**

Dans `controller/lab_controller.py`, ajouter l'import en tête de fichier (à côté des autres imports du module) :

```python
from api_backend.backend_app.utils.patient_resolution import resolve_patient_id
```

Puis remplacer la méthode `create_batch_results` entière :

```python
    def create_batch_results(self, payload: Dict[str, Any], current_user) -> Dict:
        patient_id = payload.get('patient_id')
        patient_uuid = payload.get('patient_uuid')
        external_info = payload.get('external_patient_info')
        results_list = payload.get('results', [])
        prescribed_by_id = payload.get('prescribed_by_id')
        prescribed_by_name = payload.get('prescribed_by_name')
        origin_prescription_id = payload.get('origin_prescription_id')
        batch_uuid = payload.get('batch_uuid')

        resolved_patient_id = None
        if patient_id or patient_uuid:
            resolved_patient_id = resolve_patient_id(self.repo.session, patient_id, patient_uuid)

        # Un autre item de ce meme lot (batch_uuid) a-t-il deja ete cree
        # (envoye dans une operation CRUD anterieure) ? Si oui, on reutilise
        # son code LAB et son groupement Postgres (batch_id) au lieu d'en
        # generer de nouveaux - remplace la logique "le premier de la
        # boucle genere, les suivants reutilisent" qui supposait un seul
        # appel HTTP synchrone (invalide hors ligne, chaque item part dans
        # sa propre operation).
        existing_sibling = self.repo.get_lab_result_by_batch_uuid(batch_uuid) if batch_uuid else None
        server_batch_id = existing_sibling.batch_id if existing_sibling else uuid.uuid4()
        shared_code = existing_sibling.code_lab_patient if existing_sibling else None

        success_count = 0
        for item in results_list:
            item_uuid = item.get('uuid')
            if item_uuid:
                already = self.repo.get_lab_result_by_uuid(item_uuid)
                if already:
                    # Rejeu d'un item deja accepte - idempotent, ne duplique pas.
                    success_count += 1
                    if not shared_code:
                        shared_code = already.code_lab_patient
                    continue

            payload_item = {
                "uuid": item_uuid,
                "batch_uuid": batch_uuid,
                "examen_id": item.get('examen_id'),
                "patient_id": resolved_patient_id,
                "external_patient_info": external_info,
                "batch_id": server_batch_id,
                "code_lab_patient": shared_code,
                "prescribed_by": prescribed_by_id,
                "prescribed_by_name": prescribed_by_name,
                "origin_prescription_id": origin_prescription_id,
                "technician_id": current_user.user_id,
                "technician_name": current_user.full_name,
                "created_by": current_user.user_id,
                "created_by_name": current_user.full_name,
            }
            new_res = self.repo.create_lab_result(payload_item)
            if not shared_code:
                shared_code = new_res.code_lab_patient
            success_count += 1

        return {"success": True, "count": success_count, "shared_code": shared_code, "batch_id": str(server_batch_id)}
```

- [ ] **Step 3: Corriger la propagation de `origin_prescription_id` côté frontend**

Dans `ah2-admin-web/src/views/modules/labo/LabReception.vue`, dans `submitRequest()` (autour de la ligne 414-425), remplacer :

```javascript
      const payload = {
        // ...
        patient_id: null,
        prescription_id: null,
        // ...
      };

      if (selectedPatient.value) {
          payload.patient_id = selectedPatient.value.id;
          payload.prescription_id = selectedPatient.value.prescription_id || selectedPatient.value.last_prescription_id || null;
```

par :

```javascript
      const payload = {
        // ...
        patient_id: null,
        origin_prescription_id: null,
        // ...
      };

      if (selectedPatient.value) {
          payload.patient_id = selectedPatient.value.id;
          payload.origin_prescription_id = selectedPatient.value.prescription_id || selectedPatient.value.last_prescription_id || null;
```

(garder le reste de `submitRequest` identique — seul le nom du champ change, pour correspondre au champ que `BatchResultCreate` lit désormais réellement.)

- [ ] **Step 4: Test backend — code partagé sur 2 appels séparés + idempotence + origin_prescription_id**

```python
# tests/test_lab_endpoints.py
def test_batch_results_shares_code_across_two_separate_calls(client, laborantin_token, examen_id):
    batch_uuid = "batch-test-001"
    item1_uuid = "11111111-1111-1111-1111-111111111111"
    item2_uuid = "22222222-2222-2222-2222-222222222222"

    r1 = client.post("/labo/results/batch", json={
        "external_patient_info": {"nom": "Externe Un"},
        "batch_uuid": batch_uuid,
        "results": [{"examen_id": examen_id, "uuid": item1_uuid}],
    }, headers={"Authorization": f"Bearer {laborantin_token}"})
    assert r1.status_code == 201
    code1 = r1.json()["shared_code"]

    r2 = client.post("/labo/results/batch", json={
        "external_patient_info": {"nom": "Externe Un"},
        "batch_uuid": batch_uuid,
        "results": [{"examen_id": examen_id, "uuid": item2_uuid}],
    }, headers={"Authorization": f"Bearer {laborantin_token}"})
    assert r2.status_code == 201
    assert r2.json()["shared_code"] == code1


def test_batch_results_replay_same_uuid_is_idempotent(client, laborantin_token, examen_id):
    item_uuid = "33333333-3333-3333-3333-333333333333"
    payload = {
        "external_patient_info": {"nom": "Externe Deux"},
        "batch_uuid": "batch-test-002",
        "results": [{"examen_id": examen_id, "uuid": item_uuid}],
    }
    headers = {"Authorization": f"Bearer {laborantin_token}"}
    r1 = client.post("/labo/results/batch", json=payload, headers=headers)
    r2 = client.post("/labo/results/batch", json=payload, headers=headers)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["count"] == 1 and r2.json()["count"] == 1
    # Une seule ligne reellement creee en base malgre 2 appels identiques.
```

- [ ] **Step 5: Exécuter les tests**

Run: `pytest tests/test_lab_endpoints.py -v -k batch`
Expected: PASS. Adapter les fixtures (`laborantin_token`, `examen_id`) aux fixtures réellement disponibles dans `tests/conftest.py` — si elles n'existent pas sous ce nom, réutiliser les fixtures équivalentes déjà utilisées par les autres tests de ce fichier.

---

### Task 4: Backend — saisie de valeurs résolue par uuid

**Files:**
- Modify: `api_backend/backend_app/utils/patient_resolution.py` (nouvelles fonctions)
- Modify: `api_backend/backend_app/routes/labo/lab_endpoints.py` (route `PUT /results/{result_id}/values`, lignes 208-220)
- Test: `tests/test_lab_endpoints.py` (complété)

**Interfaces:**
- Consumes: `LabRepository.get_lab_result_by_uuid` (Task 2).
- Produces: `resolve_lab_result_id_from_path(session, raw_id: str) -> int` — accepte soit un `result_id` entier (chaîne numérique), soit un `uuid` de dossier créé hors ligne, et renvoie toujours le `result_id` entier réel. Route `PUT /labo/results/{result_id}/values` accepte désormais `result_id` comme segment texte (int OU uuid).

- [ ] **Step 1: Ajouter les fonctions de résolution**

Dans `api_backend/backend_app/utils/patient_resolution.py`, ajouter à la fin du fichier (après `resolve_medical_record_id`) :

```python
def resolve_lab_result_id(session: Session, result_id: Optional[int], result_uuid: Optional[str]) -> int:
    """result_id a utiliser pour une saisie de valeurs labo - meme motif que
    resolve_patient_id/resolve_medical_record_id. Contrairement a la
    consultation, le lien est obligatoire ici : on ne peut pas saisir des
    valeurs sans savoir a quel dossier elles appartiennent."""
    if result_id is not None:
        return result_id
    if not result_uuid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="result_id ou result_uuid est requis")
    try:
        normalized = str(uuid_lib.UUID(str(result_uuid)))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="result_uuid invalide")
    row = session.execute(
        text("SELECT result_id FROM lab_results WHERE uuid = CAST(:u AS uuid)"),
        {"u": normalized},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dossier labo introuvable pour ce result_uuid")
    return int(row[0])


def resolve_lab_result_id_from_path(session: Session, raw_id: str) -> int:
    """result_id a partir d'un segment d'URL qui peut etre soit l'entier
    server_id (dossier deja synchronise), soit l'uuid local d'un dossier
    cree hors ligne pas encore confirme - saisie de valeurs sur un dossier
    lui-meme cree hors ligne dans le meme geste (enchainement complet,
    decision utilisateur 2026-09-24)."""
    try:
        return int(raw_id)
    except ValueError:
        return resolve_lab_result_id(session, None, raw_id)
```

- [ ] **Step 2: Adapter la route**

Dans `api_backend/backend_app/routes/labo/lab_endpoints.py`, ajouter l'import :

```python
from api_backend.backend_app.utils.patient_resolution import resolve_lab_result_id_from_path
```

Remplacer la route `update_result_values` (lignes 208-220) :

```python
@router.put("/results/{result_id}/values", 
            dependencies=[Depends(role_required("laborantin", "admin", "ToxicoManager"))])
def update_result_values(result_id: str, payload: Dict[str, Any] = Body(...), ctrl: LabController = Depends(get_lab_controller)):
    try:
        resolved_id = resolve_lab_result_id_from_path(ctrl.repo.session, result_id)
        values = payload.get("values", {})
        completed = payload.get("completed", False)
        global_note = payload.get("note", None)
        return ctrl.submit_values(resolved_id, values, completed, global_note)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur sauvegarde valeurs {result_id}")
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde.")
```

Note : `result_id: int` devient `result_id: str` — seule cette route change de type, les routes `GET /results/{result_id}`, `DELETE /results/{result_id}` et `GET /results/{result_id}/pdf` restent en `int` (elles ne sont jamais appelées sur un dossier créé hors ligne pas encore synchronisé, hors périmètre de ce chantier).

- [ ] **Step 3: Test — résolution par uuid, uuid inconnu → 422**

```python
def test_update_values_by_result_uuid(client, laborantin_token, db_session, created_lab_result_with_uuid):
    result_uuid = created_lab_result_with_uuid.uuid
    r = client.put(f"/labo/results/{result_uuid}/values", json={
        "values": {}, "completed": False,
    }, headers={"Authorization": f"Bearer {laborantin_token}"})
    assert r.status_code == 200


def test_update_values_unknown_uuid_returns_422(client, laborantin_token):
    r = client.put("/labo/results/99999999-9999-9999-9999-999999999999/values", json={
        "values": {}, "completed": False,
    }, headers={"Authorization": f"Bearer {laborantin_token}"})
    assert r.status_code == 422
```

- [ ] **Step 4: Exécuter les tests**

Run: `pytest tests/test_lab_endpoints.py -v -k values`
Expected: PASS. Créer la fixture `created_lab_result_with_uuid` si absente (un `LabResult` créé via `LabRepository.create_lab_result` avec un `uuid` connu, réutilisable par ce seul test).

---

### Task 5: Frontend — corriger le bug de sauvegarde des valeurs (production, en ligne comme hors ligne)

**Files:**
- Modify: `ah2-admin-web/src/views/modules/labo/LabValidation.vue` (`handleSave`, lignes ~211-243)
- Modify: `ah2-admin-web/src/stores/labStore.js` (`saveValues`, lignes 304-331)

**Interfaces:**
- Consumes: `PUT /labo/results/{result_id}/values` (Task 4, mais la forme du payload `{values, completed, note}` existait déjà côté backend avant ce chantier — c'est uniquement le client qui l'envoyait mal).
- Produces: `labStore.saveValues(resultId, valuesMap, completed)` (signature à 3 arguments, remplace la signature à 2 arguments) — c'est cette nouvelle signature que la Task 8 étendra avec la branche locale `laborantin`.

- [ ] **Step 1: Corriger `handleSave` pour construire un formValues keyé par parametre_id**

Le bug racine : `formValues.value` est actuellement rempli par `detail.id` (le `detail_id` serveur - lignes ~200-201 de `LabValidation.vue`, dans le `onMounted`), pas par `parametre_id` - il faut vérifier lequel `detail.id` désigne réellement en lisant la réponse de `getResultDetail`. `LabResultOutDetail` (backend, `labo_schemas.py`) sérialise `detail_id`, pas `id` - donc si `LabValidation.vue` lit `detail.id`, c'est que la couche intermédiaire (ou un getter) renomme déjà `detail_id` en `id`. Ne rien changer à cette partie du câblage — elle reste valide pour un dossier créé EN LIGNE (le seul cas existant avant ce chantier). Se contenter de corriger l'appel à `saveValues` :

```javascript
const handleSave = async (markCompleted) => {
  if (markCompleted && !confirm("Attention : Cette action est irréversible. Voulez-vous valider et clôturer ce dossier ?")) {
    return;
  }

  isSaving.value = true;
  try {
    const success = await store.saveValues(route.params.id, {
      values: formValues.value,
      completed: markCompleted,
      note: null,
    });

    if (success) {
      if (markCompleted) {
        const wantPrint = confirm("Dossier validé ! Voulez-vous imprimer le PDF maintenant ?");
        if (wantPrint) {
          await handlePrint();
        }
        router.push({ name: 'LabTechnician' });
      }
    }
  } catch (e) {
    console.error(e);
  } finally {
    isSaving.value = false;
  }
};
```

- [ ] **Step 2: Corriger `saveValues` dans le store pour accepter le payload structuré**

Dans `ah2-admin-web/src/stores/labStore.js`, remplacer la signature de `saveValues` :

```javascript
        // Sauvegarder les valeurs saisies par le laborantin
        // payload = { values: {detailId_ou_parametreId: valeur}, completed: bool, note: string|null }
        async saveValues(resultId, payload) {
            this.loading = true;
            this.error = null;
            this.successMessage = null;
            try {
                await LabGateway.updateResultValues(resultId, payload);

                if (payload.completed) {
                    this.successMessage = "Dossier validé et clôturé !";
                    this.paillasseList = this.paillasseList.filter(item => item.result_id !== resultId);
                    this.currentResult = null;
                } else {
                    this.successMessage = "Brouillon sauvegardé.";
                    await this.fetchResultDetail(resultId);
                }

                return true;
            } catch (err) {
                this.error = "Erreur lors de la sauvegarde.";
                return false;
            } finally {
                this.loading = false;
            }
        },
```

La forme du payload envoyé (`{values, completed, note}`) est désormais identique à ce que `PUT /labo/results/{id}/values` a toujours lu côté backend (`payload.get("values", {})` etc., inchangé depuis avant ce chantier) — c'est uniquement le décalage d'appel côté client qui empêchait toute sauvegarde de fonctionner.

- [ ] **Step 3: Build frontend**

Run: `cd ah2-admin-web && npm run build`
Expected: build vert, aucune erreur.

- [ ] **Step 4: Vérification manuelle immédiate (ce bug est en production dès maintenant)**

Se connecter en `laborantin`, ouvrir un dossier `pending`/`partial` existant via `/labo/validation/:id`, saisir une valeur, cliquer "Enregistrer brouillon", vérifier dans l'onglet Réseau du navigateur que la requête `PUT /labo/results/{id}/values` envoie bien `{values: {...}, completed: false, note: null}` et reçoit un 200 (pas un 500 silencieusement ignoré par le catch). Recharger la page, vérifier que la valeur saisie est bien rechargée dans le formulaire.

---

### Task 6: Sync — garde `connectPowerSync`, souscriptions, schéma local, streams serveur

**Files:**
- Modify: `ah2-admin-web/src/stores/auth.js` (ligne 77)
- Modify: `ah2-admin-web/src/App.vue` (ligne 16)
- Modify: `ah2-admin-web/src/powersync-client/client.js` (bloc de souscription, lignes 96-124)
- Modify: `ah2-admin-web/src/powersync-client/AppSchema.js` (table `lab_results`, nouvelles tables)
- Modify: `powersync/sync-config.yaml` (5 nouveaux streams)

**Interfaces:**
- Produces: colonne locale `lab_results.uuid` (texte, PK PowerSync), `lab_results.batch_uuid`, `lab_results.examen_id`, `lab_results.origin_prescription_id`, `lab_results.patient_uuid` (écriture — Task 7 les consomme) ; nouvelle table locale `lab_result_details` (PK = `uuid::text` local, voir Step 3) ; nouvelle table `lab_pending_prescriptions` ; nouvelles tables `reference_lab_params`, `reference_lab_ranges`.

- [ ] **Step 1: Étendre la garde `connectPowerSync`**

Dans `ah2-admin-web/src/stores/auth.js`, ligne 77, remplacer :

```javascript
        if (role === 'medecin' || role === 'nurse' || role === 'secretaire') {
```

par :

```javascript
        if (role === 'medecin' || role === 'nurse' || role === 'secretaire' || role === 'laborantin') {
```

Dans `ah2-admin-web/src/App.vue`, ligne 16, même remplacement :

```javascript
  if (role === 'medecin' || role === 'nurse' || role === 'secretaire' || role === 'laborantin') {
```

- [ ] **Step 2: Étendre le catalogue d'examens et le motif de souscription**

Dans `ah2-admin-web/src/powersync-client/client.js`, dans `openConnection(role)` :

Remplacer la ligne 118 (`if (role === 'medecin' || role === 'nurse' || role === 'secretaire') {`) par :

```javascript
    if (role === 'medecin' || role === 'nurse' || role === 'secretaire' || role === 'laborantin') {
      streamHandles.push(db.syncStream('reference_exam_catalog'));
    }
```

Puis, juste après ce bloc (avant le bloc `reference_motifs`, qui reste réservé à `medecin`/`nurse`), ajouter un nouveau bloc `laborantin` :

```javascript
    if (role === 'laborantin') {
      streamHandles.push(db.syncStream('lab_pending_prescriptions'));
      streamHandles.push(db.syncStream('lab_active_results'));
      streamHandles.push(db.syncStream('lab_active_result_details'));
      streamHandles.push(db.syncStream('reference_lab_params'));
      streamHandles.push(db.syncStream('reference_lab_ranges'));
    }
```

`patients_lookup`/`doctors_lookup` (lignes 102-103) sont déjà souscrits pour tout rôle sans condition — aucun changement nécessaire pour la recherche patient interne et le nom du médecin prescripteur.

- [ ] **Step 3: Étendre `AppSchema.js`**

Dans `ah2-admin-web/src/powersync-client/AppSchema.js`, remplacer la définition actuelle de `lab_results` (lignes 118-133) :

```javascript
// Ecriture locale pour laborantin (reception + saisie hors ligne, chantier 4
// sous-projet 5) - PATCH via lab_result_details separee (une ligne par
// parametre, voir plus bas), jamais directement sur lab_results. Lecture
// seule pour medecin/nurse (stream clinical_lab_results, status='completed'
// uniquement) - conventions PK differentes coexistent sans risque car les
// roles sont mutuellement exclusifs par session et les filtres de statut ne
// se recouvrent jamais (completed vs pending/partial).
const lab_results = new Table(
  {
    server_id: column.integer,
    patient_id: column.integer,
    patient_uuid: column.text,
    test_type: column.text,
    test_date: column.text,
    status: column.text,
    note: column.text,
    examen_id: column.integer,
    code_lab_patient: column.text,
    prescribed_by_name: column.text,
    prescribed_by: column.integer,
    origin_prescription_id: column.integer,
    batch_uuid: column.text,
    external_patient_info: column.text,
  },
  { indexes: { by_patient: ['patient_id'], by_batch_uuid: ['batch_uuid'] } }
);

// Une ligne par parametre d'un dossier lab_results local (reception +
// saisie hors ligne). PK locale = son propre uuid client (genere a la
// reception, jamais l'entier detail_id serveur - inconnu tant que le
// dossier n'est pas confirme). result_uuid pointe vers lab_results.id
// (uuid du dossier parent, PAS son server_id - meme motif que
// prescriptions.medical_record_id pouvant chainer une consultation creee
// dans le meme geste hors ligne).
const lab_result_details = new Table(
  {
    result_uuid: column.text,
    parametre_id: column.integer,
    valeur_text: column.text,
    valeur_num: column.text,
  },
  { indexes: { by_result: ['result_uuid'] } }
);

// Prescriptions medicales actives de type examen, pas encore transformees
// en dossier labo - alimente le pre-remplissage des examens a la reception
// d'un patient interne (LabReception.vue). Lecture seule.
const lab_pending_prescriptions = new Table({
  server_id: column.integer,
  patient_id: column.integer,
  prescribed_by_name: column.text,
  lab_exams_list: column.text,
  start_date: column.text,
});

// Parametres definis pour chaque examen (ex: Leucocytes pour une NFS) -
// necessaires pour construire les lignes lab_result_details a la reception
// hors ligne (une ligne vide par parametre de l'examen choisi, meme motif
// que create_lab_result cote serveur). Lecture seule.
const reference_lab_params = new Table({
  server_id: column.integer,
  examen_id: column.integer,
  nom_parametre: column.text,
  unite: column.text,
  type_valeur: column.text,
  input_type: column.text,
  options_list: column.text,
}, { indexes: { by_examen: ['examen_id'] } });

// Valeurs de reference par age/sexe - affichage INDICATIF uniquement cote
// client (l'interpretation qui fait autorite reste calculee serveur a la
// synchronisation, jamais dupliquee ici). Lecture seule.
const reference_lab_ranges = new Table({
  server_id: column.integer,
  parametre_id: column.integer,
  sexe: column.text,
  age_min: column.integer,
  age_max: column.integer,
  valeur_min: column.text,
  valeur_max: column.text,
}, { indexes: { by_parametre: ['parametre_id'] } });
```

Puis dans `export const AppSchema = new Schema({...})` (lignes 248-263), ajouter les 4 nouvelles tables :

```javascript
export const AppSchema = new Schema({
  appointments,
  patients_lookup,
  doctors_lookup,
  patients,
  medical_records,
  prescriptions,
  lab_results,
  lab_result_details,
  lab_pending_prescriptions,
  reference_lab_params,
  reference_lab_ranges,
  caisse,
  caisse_retrait,
  paiement_echelonne,
  pharmacy_stock,
  exam_catalog,
  motifs,
  sync_quarantine,
});
```

- [ ] **Step 4: Ajouter les 5 streams serveur**

Dans `powersync/sync-config.yaml`, ajouter à la fin du fichier (après le stream `reference_motifs`) :

```yaml
  # Chantier 4 sous-projet 5 : role laborantin, reception + paillasse +
  # saisie hors ligne. Colonnes qualifiees par table partout ou une jointure
  # met plusieurs tables en scope (meme regle que clinical_lab_results).

  lab_pending_prescriptions:
    auto_subscribe: false
    queries:
      - SELECT prescriptions.uuid::text AS id, prescriptions.prescription_id AS server_id,
          prescriptions.patient_id, prescriptions.prescribed_by_name,
          prescriptions.lab_exams_list::text AS lab_exams_list,
          prescriptions.start_date::text AS start_date
        FROM prescriptions
        JOIN patients ON patients.patient_id = prescriptions.patient_id
        WHERE patients.is_deleted = false
          AND prescriptions.is_lab_order = true
          AND prescriptions.status = 'active'

  lab_active_results:
    auto_subscribe: false
    queries:
      - SELECT lab_results.uuid::text AS id, lab_results.result_id AS server_id,
          lab_results.patient_id, lab_results.patient_uuid::text AS patient_uuid,
          lab_results.test_type, lab_results.test_date::text AS test_date,
          lab_results.status, lab_results.note, lab_results.examen_id,
          lab_results.code_lab_patient, lab_results.prescribed_by_name,
          lab_results.prescribed_by, lab_results.origin_prescription_id,
          lab_results.batch_uuid, lab_results.external_patient_info::text AS external_patient_info
        FROM lab_results
        WHERE lab_results.status IN ('pending', 'partial')

  lab_active_result_details:
    auto_subscribe: false
    queries:
      - SELECT lab_result_details.detail_id::text AS id,
          lab_results.uuid::text AS result_uuid, lab_result_details.parametre_id,
          lab_result_details.valeur_text, lab_result_details.valeur_num::text AS valeur_num
        FROM lab_result_details
        JOIN lab_results ON lab_results.result_id = lab_result_details.result_id
        WHERE lab_results.status IN ('pending', 'partial')

  reference_lab_params:
    auto_subscribe: false
    queries:
      - SELECT id::text AS id, id AS server_id, examen_id, nom_parametre,
          unite, type_valeur, input_type, options_list
        FROM parametres

  reference_lab_ranges:
    auto_subscribe: false
    queries:
      - SELECT id::text AS id, id AS server_id, parametre_id, sexe, age_min,
          age_max, valeur_min::text AS valeur_min, valeur_max::text AS valeur_max
        FROM reference_ranges
```

Note importante : `lab_active_result_details` ne réutilise PAS la convention `uuid::text AS id` locale — les lignes `lab_result_details` créées hors ligne portent leur propre uuid client généré côté client (Task 8), jamais téléchargées avec cet id-là depuis le serveur (elles n'existent en base serveur qu'avec un `detail_id` entier classique, jamais de colonne `uuid` propre — non prévue par la spec, pas nécessaire : `lab_result_details` n'est jamais résolue individuellement par un id stable, seulement retrouvée via `(result_uuid, parametre_id)`). `detail_id::text AS id` suffit donc ici pour le téléchargement, exactement comme `clinical_lab_results` utilise `result_id::text AS id` — ce sont deux lignes PowerSync locales différentes pour la même ligne serveur (une créée localement à la réception, une téléchargée après synchronisation) qui finissent par coexister sous deux id locaux différents dans `lab_result_details` ; ce n'est pas un problème car la Task 8 lit toujours par `(result_uuid, parametre_id)`, jamais par id de ligne brut.

- [ ] **Step 5: Redémarrer le service PowerSync et vérifier l'absence d'erreur de règles**

Run (après avoir modifié `sync-config.yaml`) : `docker restart powersync-powersync-1`
Puis vérifier les logs : `docker logs --since 30s powersync-powersync-1`
Expected: aucune erreur de parsing des règles de synchronisation (une erreur de règle bloque TOUT le service PowerSync pour tous les rôles, pas seulement `laborantin` — vérifier immédiatement, ne pas attendre la Task 11).

- [ ] **Step 6: Build frontend**

Run: `cd ah2-admin-web && npm run build`
Expected: build vert.

---

### Task 7: Frontend — réception hors ligne (patient interne et externe)

**Files:**
- Modify: `ah2-admin-web/src/services/labGateway.js` (`getAllExams`, `searchInternalPrescriptions`, `createBatchResults`)
- Modify: `ah2-admin-web/src/stores/labStore.js` (`createBatchRequest`)

**Interfaces:**
- Consumes: tables locales `lab_pending_prescriptions`, `reference_lab_params`, `patients_lookup` (Task 6) ; `authStore.hasRole` (existant).
- Produces: écriture locale dans `lab_results` + `lab_result_details` pour `laborantin` déconnecté, avec `uuid`/`batch_uuid` cohérents pour la Task 9 (connecteur).

- [ ] **Step 1: Ajouter `laborantin` au secours local du catalogue d'examens**

Dans `ah2-admin-web/src/services/labGateway.js`, `getAllExams()` (lignes 12-25), remplacer :

```javascript
            if (!err.response && authStore.hasRole(['secretaire', 'medecin', 'nurse'])) {
```

par :

```javascript
            if (!err.response && authStore.hasRole(['secretaire', 'medecin', 'nurse', 'laborantin'])) {
```

- [ ] **Step 2: Secours local pour la recherche interne avec prescriptions**

Dans `ah2-admin-web/src/services/labGateway.js`, remplacer `searchInternalPrescriptions` :

```javascript
    searchInternalPrescriptions: async (query) => {
        try {
            return await api.get('/labo/search-internal', {
                params: { q: query }
            });
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['laborantin'])) {
                const { db } = await import('@/powersync-client/client');
                const q = `%${query}%`;
                const rows = await db.getAll(
                    `SELECT p.patient_id AS patient_id, p.first_name || ' ' || p.last_name AS nom,
                            p.code_patient AS patient_code, lp.prescribed_by_name,
                            lp.lab_exams_list, lp.id AS prescription_id
                     FROM patients_lookup p
                     LEFT JOIN lab_pending_prescriptions lp ON lp.patient_id = p.patient_id
                     WHERE p.first_name LIKE ? OR p.last_name LIKE ? OR p.code_patient LIKE ?
                     LIMIT 20`,
                    [q, q, q]
                );
                return { data: rows.map((r) => ({
                    id: r.patient_id,
                    nom: r.nom,
                    patient_code: r.patient_code,
                    prescribed_by_name: r.prescribed_by_name || null,
                    exams_prescribed: r.lab_exams_list ? JSON.parse(r.lab_exams_list) : [],
                    prescription_id: r.prescription_id || null,
                })) };
            }
            throw err;
        }
    },
```

- [ ] **Step 3: Écriture locale de la réception dans `createBatchRequest`**

Dans `ah2-admin-web/src/stores/labStore.js`, remplacer `createBatchRequest` :

```javascript
       async createBatchRequest(payload) {
            this.loading = true;
            this.error = null;
            this.successMessage = null;

            try {
                const { useAuthStore } = await import('@/stores/auth');
                const authStore = useAuthStore();

                if (authStore.hasRole(['laborantin'])) {
                    const { db } = await import('@/powersync-client/client');
                    const batchUuid = crypto.randomUUID();
                    let createdCount = 0;

                    await db.writeTransaction(async (tx) => {
                        for (const item of payload.results) {
                            const resultUuid = crypto.randomUUID();
                            await tx.execute(
                                `INSERT INTO lab_results (
                                    id, patient_id, patient_uuid, test_type, status,
                                    examen_id, prescribed_by, prescribed_by_name,
                                    origin_prescription_id, batch_uuid, external_patient_info
                                 ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)`,
                                [
                                    resultUuid, payload.patient_id || null, payload.patient_uuid || null,
                                    'Analyse Labo', item.examen_id, payload.prescribed_by_id || null,
                                    payload.prescribed_by_name || null, payload.origin_prescription_id || null,
                                    batchUuid, payload.external_patient_info ? JSON.stringify(payload.external_patient_info) : null,
                                ]
                            );
                            const params = await tx.getAll(
                                'SELECT id FROM reference_lab_params WHERE examen_id = ?',
                                [item.examen_id]
                            );
                            for (const p of params) {
                                await tx.execute(
                                    `INSERT INTO lab_result_details (id, result_uuid, parametre_id, valeur_text)
                                     VALUES (?, ?, ?, '')`,
                                    [crypto.randomUUID(), resultUuid, p.id]
                                );
                            }
                            createdCount += 1;
                        }
                    });

                    this.successMessage = `${createdCount} examen(s) enregistré(s) localement, en attente de synchronisation.`;
                    return { success: true, count: createdCount, shared_code: null, batch_id: batchUuid };
                }

                const response = await LabGateway.createBatchResults(payload);
                const data = response.data;
                const count = data.count || 0;
                const codeAffiche = data.shared_code || "EN_COURS...";
                this.successMessage = `Succès : ${count} Examens créés sous le numéro ${codeAffiche}.`;
                return data;

            } catch (err) {
                console.error("Erreur Batch Store:", err);
                if (err.response && err.response.data && err.response.data.detail) {
                    const detail = err.response.data.detail;
                    this.error = Array.isArray(detail)
                        ? "Erreur de format : " + detail[0].msg
                        : detail;
                } else {
                    this.error = "Erreur lors de l'enregistrement groupé.";
                }
                return null;
            } finally {
                this.loading = false;
            }
        },
```

Note : cette branche écrit toujours en local pour `laborantin`, qu'il soit réellement hors ligne ou non — même motif que `patients:PUT`/`medical_records:PUT` dans les sous-projets précédents (écriture toujours locale pour le rôle concerné, jamais un choix "en ligne vs hors ligne" décidé côté client).

- [ ] **Step 4: Build frontend**

Run: `cd ah2-admin-web && npm run build`
Expected: build vert.

---

### Task 8: Frontend — paillasse et saisie hors ligne

**Files:**
- Modify: `ah2-admin-web/src/stores/labStore.js` (`fetchDashboardData`, `fetchWorklist`, `fetchPaillasseList`, `fetchResultDetail`, `saveValues`)
- Modify: `ah2-admin-web/src/services/labGateway.js` (`getPaillasseList`, `getResultDetail`, `updateResultValues`)

**Interfaces:**
- Consumes: `lab_results`/`lab_result_details`/`reference_lab_params`/`reference_lab_ranges` locales (Task 6), `createBatchRequest` (Task 7, pour la cohérence de forme des dossiers créés).
- Produces: `labStore.saveValues(resultId, {values, completed, note})` (Task 5) gagne une branche locale pour `laborantin` qui écrit `lab_result_details` directement, sans appel réseau, quand une coupure réseau réelle est détectée.

- [ ] **Step 1: Secours local pour la paillasse**

Dans `ah2-admin-web/src/services/labGateway.js`, remplacer `getPaillasseList` :

```javascript
    async getPaillasseList() {
        try {
            return await api.get('/labo/paillasse');
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['laborantin'])) {
                const { db } = await import('@/powersync-client/client');
                const rows = await db.getAll(
                    `SELECT lr.id AS result_id, lr.code_lab_patient AS code,
                            lr.status, lr.test_date,
                            COALESCE(p.first_name || ' ' || p.last_name, json_extract(lr.external_patient_info, '$.nom')) AS patient_name
                     FROM lab_results lr
                     LEFT JOIN patients_lookup p ON p.patient_id = lr.patient_id
                     WHERE lr.status IN ('pending', 'partial')
                     ORDER BY lr.test_date DESC`
                );
                return { data: rows };
            }
            throw err;
        }
    },
```

- [ ] **Step 2: Secours local pour le détail d'un dossier**

Dans `ah2-admin-web/src/services/labGateway.js`, remplacer `getResultDetail` :

```javascript
    async getResultDetail(resultId) {
        try {
            return await api.get(`/labo/results/${resultId}`);
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['laborantin'])) {
                const { db } = await import('@/powersync-client/client');
                const result = await db.get(
                    `SELECT lr.id AS uuid, lr.code_lab_patient AS code, lr.status,
                            lr.patient_id, lr.examen_id, lr.external_patient_info,
                            COALESCE(p.first_name || ' ' || p.last_name, json_extract(lr.external_patient_info, '$.nom')) AS patient_name
                     FROM lab_results lr
                     LEFT JOIN patients_lookup p ON p.patient_id = lr.patient_id
                     WHERE lr.id = ?`,
                    [resultId]
                );
                const details = await db.getAll(
                    `SELECT d.parametre_id AS id, d.parametre_id, d.valeur_text AS value,
                            rp.nom_parametre, rp.unite, rp.input_type, rp.options_list
                     FROM lab_result_details d
                     JOIN reference_lab_params rp ON rp.id = d.parametre_id
                     WHERE d.result_uuid = ?`,
                    [resultId]
                );
                return { data: { ...result, exams: [{ examen_id: result.examen_id, details }] } };
            }
            throw err;
        }
    },
```

Note : la clé `id` de chaque ligne renvoyée dans `details` vaut ici `parametre_id`, exactement ce qu'attend désormais `LabValidation.vue` (`formValues.value[detail.id] = ...`) pour un dossier créé hors ligne — cohérent avec Task 2/Step 4 côté backend (résolution des valeurs par `parametre_id` quand le `detail_id` réel n'existe pas encore).

- [ ] **Step 3: Secours local pour l'enregistrement des valeurs**

Dans `ah2-admin-web/src/services/labGateway.js`, remplacer `updateResultValues` :

```javascript
    async updateResultValues(resultId, payload) {
        try {
            return await api.put(`/labo/results/${resultId}/values`, payload);
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['laborantin'])) {
                const { db } = await import('@/powersync-client/client');
                await db.writeTransaction(async (tx) => {
                    for (const [parametreId, value] of Object.entries(payload.values || {})) {
                        const existing = await tx.getOptional(
                            'SELECT id FROM lab_result_details WHERE result_uuid = ? AND parametre_id = ?',
                            [resultId, Number(parametreId)]
                        );
                        if (existing) {
                            await tx.execute(
                                'UPDATE lab_result_details SET valeur_text = ? WHERE id = ?',
                                [String(value ?? ''), existing.id]
                            );
                        } else {
                            await tx.execute(
                                `INSERT INTO lab_result_details (id, result_uuid, parametre_id, valeur_text)
                                 VALUES (?, ?, ?, ?)`,
                                [crypto.randomUUID(), resultId, Number(parametreId), String(value ?? '')]
                            );
                        }
                    }
                    if (payload.completed) {
                        await tx.execute("UPDATE lab_results SET status = 'partial' WHERE id = ?", [resultId]);
                        // Statut final ('completed' vs 'partial') recalcule cote
                        // serveur a la synchronisation (voir DossierConnector.js,
                        // Task 9) - 'partial' ici est une valeur d'attente locale
                        // seulement, jamais celle qui fait autorite.
                    }
                });
                return { data: { success: true } };
            }
            throw err;
        }
    },
```

- [ ] **Step 4: Secours local pour le tableau de bord/worklist**

Dans `ah2-admin-web/src/stores/labStore.js`, `fetchDashboardData` et `fetchWorklist` restent inchangés dans leur logique (ils appellent déjà `LabGateway.getStats()`/`LabGateway.getWorklist()`) — `getWorklist` reste HTTP-only par choix : le worklist (prescriptions médicales pas encore transformées en dossier) est déjà couvert par `lab_pending_prescriptions` côté secours de recherche (Step 2 de la Task 7), et `LabTechnician.vue`/le tableau de bord ne bloquent aucun geste métier hors ligne critique — seule la paillasse (Step 1 ci-dessus) et la saisie (Step 2-3) sont dans le chemin "enchaînement complet" approuvé par l'utilisateur. Ne pas ajouter de secours supplémentaire ici : conserver `fetchDashboardData`/`fetchWorklist` tels quels.

- [ ] **Step 5: Ajouter `fetchPaillasseList` au flux existant**

`fetchPaillasseList` (`labStore.js`, lignes 345-355) appelle déjà `LabGateway.getPaillasseList()` sans modification nécessaire — le secours ajouté au Step 1 s'applique automatiquement à travers cet appel existant.

- [ ] **Step 6: Build frontend**

Run: `cd ah2-admin-web && npm run build`
Expected: build vert.

---

### Task 9: Connecteur — upload des dossiers et valeurs créés hors ligne

**Files:**
- Modify: `ah2-admin-web/src/powersync-client/DossierConnector.js` (nouveau `case`)
- Modify: `ah2-admin-web/src/services/labGateway.js` (aucune nouvelle méthode gateway nécessaire — réutilise `createBatchResults`/`updateResultValues` existants)

**Interfaces:**
- Consumes: `LabGateway.createBatchResults` (existant), `LabGateway.updateResultValues` (existant, forme confirmée Task 5) ; `isPatientQuarantined`/`quarantine` (existant, `syncQuarantine.js`).
- Produces: chaque ligne `lab_results` locale créée hors ligne (Task 7) est envoyée individuellement via `POST /labo/results/batch` avec un seul item (le serveur résout le `batch_uuid` partagé — Task 3) ; chaque ligne `lab_result_details` locale est envoyée via `PUT /labo/results/{result_uuid}/values`.

- [ ] **Step 1: Ajouter le cas `lab_results:PUT`**

Dans `ah2-admin-web/src/powersync-client/DossierConnector.js`, ajouter un nouveau `case` dans le `switch` de `uploadData`, juste avant `case 'paiement_echelonne:PUT':` :

```javascript
          case 'lab_results:PUT': {
            // Patient interne en quarantaine (refuse definitivement) : le
            // dossier labo qui le reference rejoint la quarantaine au lieu
            // d'etre envoye vers un patient inexistant - meme motif que
            // medical_records/prescriptions au sous-projet 4.
            if (op.opData.patient_uuid && await isPatientQuarantined(database, op.opData.patient_uuid)) {
              await quarantine(database, {
                kind: 'lab_result',
                localId: op.id,
                patientUuid: op.opData.patient_uuid,
                payload: op.opData,
                error: 'Patient en echec de synchronisation',
              });
              break;
            }
            await LabGateway.createBatchResults({
              patient_id: op.opData.patient_id || null,
              patient_uuid: op.opData.patient_uuid || null,
              prescribed_by_id: op.opData.prescribed_by || null,
              prescribed_by_name: op.opData.prescribed_by_name || null,
              external_patient_info: op.opData.external_patient_info ? JSON.parse(op.opData.external_patient_info) : null,
              origin_prescription_id: op.opData.origin_prescription_id || null,
              batch_uuid: op.opData.batch_uuid,
              results: [{ examen_id: op.opData.examen_id, uuid: op.id }],
            });
            break;
          }
          case 'lab_result_details:PUT': {
            // Le dossier parent peut lui-meme etre en quarantaine (memes
            // conditions que lab_results:PUT ci-dessus, valeur saisie hors
            // ligne AVANT que l'echec de reception ne soit connu - cas rare
            // mais possible, spec section 4). On la retient avec lui plutot
            // que de tenter un envoi qui echouera de toute facon (le dossier
            // lui-meme n'existera jamais cote serveur).
            const parent = await database.getOptional(
              'SELECT patient_uuid FROM lab_results WHERE id = ?',
              [op.opData.result_uuid]
            );
            if (parent?.patient_uuid && await isPatientQuarantined(database, parent.patient_uuid)) {
              await quarantine(database, {
                kind: 'lab_result_detail',
                localId: op.id,
                patientUuid: parent.patient_uuid,
                payload: op.opData,
                error: 'Dossier labo en echec de synchronisation',
              });
              break;
            }
            await LabGateway.updateResultValues(op.opData.result_uuid, {
              values: { [op.opData.parametre_id]: op.opData.valeur_text },
              completed: false,
              note: null,
            });
            break;
          }
          case 'lab_results:PATCH': {
            // Seule ecriture locale possible sur lab_results apres sa
            // creation (Task 8/Step 3 : le bouton "Valider & Cloturer" hors
            // ligne passe par UPDATE lab_results SET status = 'partial').
            // PowerSync ne genere jamais de PATCH a partir d'une ligne
            // telechargee (seulement a partir d'une ecriture locale) - ce
            // cas ne peut donc provenir que de cette marque locale, jamais
            // d'un dossier simplement synchronise depuis le serveur.
            // Porte le signal mark_completed jusqu'au serveur : sans ce cas,
            // "Valider & Cloturer" hors ligne n'aurait aucun effet cote
            // serveur (les valeurs arriveraient via lab_result_details:PUT
            // ci-dessus, mais le dossier resterait indefiniment pending/
            // partial) - violerait la spec section 3 ("mark_completed
            // transite tel quel").
            const current = await database.getOptional(
              'SELECT status, patient_uuid FROM lab_results WHERE id = ?',
              [op.id]
            );
            if (current?.status !== 'partial') {
              break;
            }
            if (current.patient_uuid && await isPatientQuarantined(database, current.patient_uuid)) {
              break;
            }
            await LabGateway.updateResultValues(op.id, {
              values: {},
              completed: true,
              note: null,
            });
            break;
          }
```

Ajouter l'import en tête de fichier, avec les autres gateways :

```javascript
import { LabGateway } from '@/services/labGateway';
```

- [ ] **Step 2: Vérifier que `submit_values`/`save_results_values` acceptent un `values` vide**

Le cas `lab_results:PATCH` ci-dessus appelle `updateResultValues` avec `values: {}` (les valeurs elles-mêmes ont déjà été envoyées séparément par les opérations `lab_result_details:PUT`, potentiellement dans une transaction CRUD antérieure) — seul le `completed: true` compte pour cet appel. Vérifier dans `repositories/lab_repo.py::save_results_values` (déjà lu à la Task 2/Step 4) qu'un dict `values` vide ne lève aucune exception (la boucle `for key, value in (values or {}).items()` ne s'exécute simplement aucune fois) et que le calcul du statut final (`completed`/`partial`) s'appuie bien sur les `LabResultDetail` déjà en base pour ce `result_id`, pas sur le contenu de `values` reçu dans cet appel précis — comportement déjà garanti par le code existant (`save_results_values` relit toujours les détails du dossier en base pour décider de son statut final, jamais seulement les clés reçues), à confirmer par simple lecture, aucune modification de code attendue à ce Step.

- [ ] **Step 3: Build frontend**

Run: `cd ah2-admin-web && npm run build`
Expected: build vert.

---

### Task 10: Quarantaine — `isLabResultQuarantined` + affichage

**Files:**
- Modify: `ah2-admin-web/src/powersync-client/syncQuarantine.js` (nouvelle fonction)
- Modify: `ah2-admin-web/src/views/sync/SyncFailuresView.vue` (affichage étendu — lire le fichier d'abord pour situer la structure existante, il liste déjà les entrées `sync_quarantine` par `kind`)

**Interfaces:**
- Consumes: table `sync_quarantine` (existante, `localOnly`).
- Produces: `isLabResultQuarantined(database, resultUuid) -> Promise<boolean>` — pas utilisé par le connecteur (qui interroge directement `isPatientQuarantined` sur le patient, Task 9), utilisé par la Task 8 pour éviter d'afficher dans la paillasse un dossier déjà en quarantaine.

- [ ] **Step 1: Ajouter la fonction**

Dans `ah2-admin-web/src/powersync-client/syncQuarantine.js`, ajouter après `isPatientQuarantined` :

```javascript
export async function isLabResultQuarantined(database, resultUuid) {
  if (!resultUuid) return false;
  const row = await database.getOptional(
    "SELECT id FROM sync_quarantine WHERE kind IN ('lab_result', 'lab_result_detail') AND local_id = ?",
    [resultUuid]
  );
  return !!row;
}
```

- [ ] **Step 2: Exclure les dossiers en quarantaine de la paillasse locale**

Dans `ah2-admin-web/src/services/labGateway.js`, `getPaillasseList` (Task 8/Step 1), la requête locale interroge directement `lab_results.status IN ('pending', 'partial')` — un dossier mis en quarantaine par le connecteur (Task 9) n'est PAS supprimé de `lab_results` (seule sa ligne `sync_quarantine` est ajoutée), donc il continuerait à apparaître dans la paillasse locale après son échec. Modifier la requête pour l'exclure :

```javascript
                const rows = await db.getAll(
                    `SELECT lr.id AS result_id, lr.code_lab_patient AS code,
                            lr.status, lr.test_date,
                            COALESCE(p.first_name || ' ' || p.last_name, json_extract(lr.external_patient_info, '$.nom')) AS patient_name
                     FROM lab_results lr
                     LEFT JOIN patients_lookup p ON p.patient_id = lr.patient_id
                     WHERE lr.status IN ('pending', 'partial')
                       AND NOT EXISTS (
                         SELECT 1 FROM sync_quarantine sq
                         WHERE sq.kind IN ('lab_result', 'lab_result_detail') AND sq.local_id = lr.id
                       )
                     ORDER BY lr.test_date DESC`
                );
```

(remplace la requête écrite à la Task 8/Step 1 — cette Task 10/Step 2 en est la version finale, ne pas appliquer les deux versions successivement dans le code final.)

- [ ] **Step 3: Étendre `SyncFailuresView.vue`**

Lire `ah2-admin-web/src/views/sync/SyncFailuresView.vue` en entier avant modification pour situer comment il affiche déjà les entrées `kind: 'patient'`/`'medical_record'`/`'prescription'` (probablement une boucle générique sur `listQuarantine()` avec un libellé par `kind`). Ajouter les libellés `lab_result` → "Dossier labo" et `lab_result_detail` → "Valeur de dossier labo" à la table/au switch de libellés déjà en place pour les `kind` existants, en suivant exactement le même motif (pas de nouveau composant, pas de nouvel écran — uniquement l'ajout de deux entrées au dictionnaire de libellés ou à la liste de `kind` déjà itérée).

- [ ] **Step 4: Build frontend**

Run: `cd ah2-admin-web && npm run build`
Expected: build vert.

---

### Task 11: Vérification finale — migration réelle (accord requis), non-régression, test manuel

**Files:**
- Aucun fichier de code — tâche de vérification et de clôture.
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md` (clôture du chantier)
- Modify: `ci/schema_only.sql` (régénéré après application réelle de la migration)

**Interfaces:**
- Consumes: l'ensemble des tâches 1-10.

- [ ] **Step 1: Demander l'accord explicite pour appliquer la migration réelle**

Avant toute action sur la base réelle, demander confirmation via `AskUserQuestion` (règle projet immuable) : "Appliquer la migration 012 (`lab_results.uuid`/`batch_uuid`) contre la base AH2 locale ?"

- [ ] **Step 2: Appliquer la migration (uniquement après accord)**

Run: `alembic upgrade head`
Expected: migration appliquée sans erreur, `alembic current` affiche `012_lab_results_uuid`.

- [ ] **Step 3: Régénérer `ci/schema_only.sql`**

Run (adapter à la commande déjà utilisée pour les migrations précédentes de ce projet, ex. `pg_dump --schema-only` filtré) : voir la commande exacte utilisée lors de la clôture de la migration 003 dans `docs/superpowers/SUIVI-AVANCEMENT.md` et la reproduire à l'identique contre la base après migration 012.

- [ ] **Step 4: Tests backend complets**

Run: `pytest tests/ -v -k "lab"`
Expected: tous les tests des Tasks 2-4 PASS.

- [ ] **Step 5: Redémarrer PowerSync et vérifier les logs**

Run: `docker restart powersync-powersync-1` puis `docker logs --since 30s powersync-powersync-1`
Expected: aucune erreur de règles de synchronisation pour les 5 nouveaux streams (déjà vérifié à la Task 6/Step 5, revérifier après la migration réelle car les colonnes `uuid`/`batch_uuid` référencées par `lab_active_results` n'existent en base que depuis cette étape).

- [ ] **Step 6: Test manuel — patient interne, 2 examens, enchaînement complet, vraie coupure réseau**

Vérifier `docker ps` (conteneurs `powersync-*` stables) avant de commencer. Se connecter en `laborantin`. Couper le réseau réellement (arrêter le serveur `uvicorn`, jamais DevTools). Réceptionner un patient interne avec 2 examens déjà prescrits par un médecin. Saisir les valeurs des 2 examens hors ligne. Reconnecter le réseau (relancer `uvicorn`). Attendre la synchronisation. Vérifier côté serveur (via l'écran médecin ou une requête directe) qu'un SEUL code LAB a été attribué aux 2 examens, et que la prescription source apparaît désormais traitée (n'apparaît plus dans le worklist médecin).

- [ ] **Step 7: Test manuel — patient externe hors ligne**

Réceptionner un patient externe hors ligne. Reconnecter. Vérifier que le dossier est présent côté serveur avec un code attribué.

- [ ] **Step 8: Test manuel — examen supprimé du catalogue pendant la coupure**

Créer un dossier hors ligne référençant un examen, puis (avec un accès admin séparé, pendant la coupure simulée côté laborantin) supprimer cet examen du catalogue. Reconnecter. Vérifier que le dossier atterrit en quarantaine (visible dans "Échecs de synchronisation" via l'extension de la Task 10), jamais perdu silencieusement.

- [ ] **Step 9: Non-régression**

Vérifier que `admin`/`ToxicoManager` sur les mêmes écrans labo conservent un comportement HTTP inchangé (pas de branche locale déclenchée pour ces rôles — toutes les branches ajoutées dans ce chantier sont gardées par `authStore.hasRole(['laborantin'])`). Revérifier rapidement les 4 sous-projets précédents (RDV, dossier patient, caisse, formulaires) : connexion/déconnexion PowerSync toujours fonctionnelle pour `medecin`/`nurse`/`secretaire` (Task 6/Step 1 a touché les mêmes lignes de garde).

- [ ] **Step 10: Clôture**

Mettre à jour `docs/superpowers/SUIVI-AVANCEMENT.md` : chantier 4 sous-projet 5 clos, résumé des 4 bugs de production corrigés au passage (saveValues 2-vs-3 arguments, forme du payload, `origin_prescription_id` jamais propagé, `create_batch_results` invalide hors ligne). Mettre à jour la mémoire auto (`project_chantier4_powersync.md`) : sous-projet 5 clos, labo hors ligne opérationnel, chantier 4 entièrement terminé (tous les modules RDV/dossier patient/caisse/formulaires/labo couverts). Supprimer l'espace de travail SDD de ce plan (`.superpowers/sdd/2026-09-24-chantier4-labo-hors-ligne/`).
