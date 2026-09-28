# Chantier 4, sous-projet 3 — Caisse/secrétariat hors-ligne Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre le module caisse/retrait/paiement échelonné réellement utilisable hors ligne pour `secretaire` — lecture ET écriture, infrastructure PowerSync et câblage UI dans le même chantier (leçon du sous-projet 2 : un chantier infra-seul laisse tout inutilisé).

**Architecture:** Écriture toujours locale pour `secretaire` (`db.execute()`, en ligne comme hors ligne), extension du connecteur unique déjà en place (`DossierConnector.js`). Lecture HTTP par défaut, secours local uniquement sur échec réseau réel. Stock pharmacy synchronisé en lecture seule pour affichage informatif (décision utilisateur : pas de risque de concurrence, un seul poste secrétariat utilisé en alternance).

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL (migration Alembic), Vue 3 / Pinia, `@powersync/web`.

**Spec:** `docs/superpowers/specs/2026-09-23-chantier4-caisse-secretariat-hors-ligne-design.md`

## Global Constraints

- Rôle concerné : `secretaire` uniquement (`authStore.hasRole(['secretaire'])`). Tout autre rôle
  (`admin` inclus, qui a aussi accès à `/caisse`/`/retrait`) garde son chemin HTTP actuel
  strictement inchangé.
- Annuler ou ajouter un paiement échelonné sur un enregistrement pas encore synchronisé (pas de
  `server_id` réel) : impossible, bouton désactivé côté UI — jamais une écriture locale
  arbitraire sur ces actions.
- La vente de médicaments/carnets reste autorisée hors ligne — le stock réel n'est jamais
  vérifié/déduit côté client, uniquement affiché à titre informatif depuis la dernière
  synchronisation connue. La déduction réelle reste exclusivement côté serveur, au moment de
  l'upload par le connecteur (endpoint `POST /caisse/` existant, inchangé).
- **Garde-fou obligatoire** : un échec définitif (400/404/409/422, ex. stock insuffisant au
  moment de l'upload) sur une transaction caisse ne doit **jamais** être abandonné en silence -
  contrairement au comportement actuel du connecteur pour les autres tables. Un signal visible
  doit être persisté localement.
- Toute migration Alembic modifiant réellement le schéma nécessite l'accord explicite de
  l'utilisateur avant application contre la base de développement réelle.
- **Aucun commit git** — convention constante de ce projet.

---

### Task 1: Migration — `uuid` sur `caisse`/`caisse_retrait`/`paiement_echelonne` + `upload_error` sur `caisse`

**Files:**
- Create: `alembic/versions/009_caisse_uuid_and_upload_error.py`

**Interfaces:**
- Consumes: rien d'une tâche antérieure de ce plan.
- Produces: colonnes `caisse.uuid`, `caisse.upload_error`, `caisse_retrait.uuid`,
  `paiement_echelonne.uuid` — consommées par la Tâche 2 (backend) et la Tâche 5 (connecteur).

Contrairement à `appointments`/`medical_records`/`prescriptions`, **aucune des 3 tables
concernées n'a de colonne `uuid`** (vérifié directement dans `ci/schema_only.sql` avant
d'écrire cette tâche — aucune tentative de deviner). Même motif que
`004_appointments_uuid_unique.py` : colonne `uuid uuid DEFAULT gen_random_uuid() NOT NULL` +
index unique, une fois par table. `caisse.upload_error` (nouvelle, `text`, nullable) porte le
garde-fou anti-perte-silencieuse de la Tâche 5.

- [ ] **Step 1: Écrire la migration**

```python
# alembic/versions/009_caisse_uuid_and_upload_error.py
"""add uuid to caisse/caisse_retrait/paiement_echelonne + caisse.upload_error (chantier 4 sous-projet 3)

Revision ID: 009_caisse_uuid_and_upload_error
Revises: 008_medrec_uuid_param
Create Date: 2026-09-23 00:00:00.000000

Aucune des 3 tables (caisse, caisse_retrait, paiement_echelonne) n'avait de
colonne uuid avant ce chantier - contrairement a appointments/medical_records/
prescriptions, qui l'avaient deja avant meme le premier chantier PowerSync.
Meme motif que 004_appointments_uuid_unique.py : DEFAULT gen_random_uuid(),
index unique par table, aucun impact sur les lignes existantes (le defaut
s'applique aussi aux lignes deja en base via ALTER TABLE ... ADD COLUMN
... DEFAULT, PostgreSQL 11+ le fait sans reecrire la table).

caisse.upload_error (text, nullable) : garde-fou anti-perte-silencieuse
(chantier exports/impressions puis ce chantier) - le connecteur PowerSync
(DossierConnector.js) traite aujourd'hui tout echec 400/404/409/422 comme
definitivement fatal et abandonne l'operation sans autre trace qu'un
console.error. Une vente reellement effectuee au guichet, rejetee au moment
de l'upload (ex. stock insuffisant entre-temps), ne doit jamais disparaitre
silencieusement - cette colonne recoit le message d'erreur, affiche comme
badge visible dans l'ecran caisse (Tache 9).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009_caisse_uuid_and_upload_error'
down_revision: Union[str, Sequence[str], None] = '008_medrec_uuid_param'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        ALTER TABLE public.caisse
            ADD COLUMN IF NOT EXISTS uuid uuid DEFAULT gen_random_uuid() NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS caisse_uuid_key ON public.caisse (uuid);

        ALTER TABLE public.caisse
            ADD COLUMN IF NOT EXISTS upload_error text;

        ALTER TABLE public.caisse_retrait
            ADD COLUMN IF NOT EXISTS uuid uuid DEFAULT gen_random_uuid() NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS caisse_retrait_uuid_key ON public.caisse_retrait (uuid);

        ALTER TABLE public.paiement_echelonne
            ADD COLUMN IF NOT EXISTS uuid uuid DEFAULT gen_random_uuid() NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS paiement_echelonne_uuid_key ON public.paiement_echelonne (uuid);
    """)


def downgrade() -> None:
    """Downgrade schema. Aucune perte de donnees metier - uuid/upload_error
    sont des colonnes ajoutees par ce chantier, jamais lues par le code
    existant avant ce chantier."""
    op.execute("""
        DROP INDEX IF EXISTS caisse_uuid_key;
        ALTER TABLE public.caisse DROP COLUMN IF EXISTS uuid;
        ALTER TABLE public.caisse DROP COLUMN IF EXISTS upload_error;

        DROP INDEX IF EXISTS caisse_retrait_uuid_key;
        ALTER TABLE public.caisse_retrait DROP COLUMN IF EXISTS uuid;

        DROP INDEX IF EXISTS paiement_echelonne_uuid_key;
        ALTER TABLE public.paiement_echelonne DROP COLUMN IF EXISTS uuid;
    """)
```

**Application réelle contre la base de développement nécessite l'accord explicite de
l'utilisateur** — demander avant `alembic upgrade head`, comme pour la migration 008.
Régénérer `ci/schema_only.sql` après application (`pg_dump --schema-only`, diff vérifié avant
d'écraser).

- [ ] **Step 2: Ajouter `uuid`/`upload_error` aux modèles SQLAlchemy**

Dans `models/caisse.py`, ajouter à la classe `Caisse` :

```python
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid_lib.uuid4)
    upload_error = Column(Text, nullable=True)
```

Ajouter les imports nécessaires en tête du fichier (vérifier d'abord qu'ils ne sont pas déjà
présents) :

```python
import uuid as uuid_lib
from sqlalchemy.dialects.postgresql import UUID
```

(Alias `uuid_lib` pour éviter tout conflit avec le nom de la colonne `uuid` elle-même dans la
classe — même motif que `models/appointment.py`, `models/medical_record.py`,
`models/prescription.py`, qui utilisent tous `import uuid` sans alias parce que la colonne
s'appelle littéralement `uuid` dans leur cas aussi — **vérifier le style réel de ces 3 fichiers
avant d'écrire l'import ici, pour rester cohérent avec l'existant plutôt que d'introduire un
style différent sans raison**.)

Dans `models/retrait.py`, ajouter à la classe `CaisseRetrait` :

```python
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid_lib.uuid4)
```

(même import à ajouter/vérifier)

Dans `models/paiement_echelonne.py`, ajouter à la classe `PaiementEchelonne` :

```python
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid_lib.uuid4)
```

(même import à ajouter/vérifier — `models/paiement_echelonne.py` n'importe actuellement ni
`uuid` ni `UUID` de `sqlalchemy.dialects.postgresql`, à ajouter en tête de fichier)

- [ ] **Step 3: Vérifier**

Run: `python -c "from models.caisse import Caisse; from models.retrait import CaisseRetrait; from models.paiement_echelonne import PaiementEchelonne; print('OK')"`
Expected: `OK`, aucune erreur d'import.

---

### Task 2: Backend — accepter `uuid` sur création (transaction, retrait, versement)

**Files:**
- Modify: `repositories/caisse_repo.py` (méthodes `create_transaction`, `add_payment_installment`)
- Modify: `repositories/caisse_retrait_repo.py` (méthode `create`)
- Modify: `controller/caisse_retrait_controller.py` (méthode `effectuer_retrait`)
- Modify: `api_backend/backend_app/routes/retrait/retrait_endpoints.py` (route `POST /`)
- Modify: `api_backend/backend_app/routes/caisse/caisse_schemas.py` (`InstallmentPaymentIn`, `PaymentEchelonneOut`)
- Modify: `api_backend/backend_app/routes/caisse/mapping.py` (`normalize_caisse_data`)
- Modify: `api_backend/backend_app/routes/retrait/mapping.py` (`normalize_retrait_data`)
- Test: `tests/test_caisse_uuid.py`

**Interfaces:**
- Consumes: colonnes `uuid` créées à la Tâche 1.
- Produces: `POST /caisse/` accepte `data["uuid"]` (clé optionnelle dans le dict libre déjà
  utilisé), réponse inclut `"uuid"`. `POST /caisse/{id}/payment` accepte
  `InstallmentPaymentIn.uuid`, réponse `PaymentEchelonneOut.uuid`. `POST /retrait/` accepte un
  nouveau `Body` param `uuid`, réponse inclut `"uuid"`. Consommés par la Tâche 7/8 (gateways
  frontend) et la Tâche 5 (connecteur).

`create_transaction`/`caisse_retrait_repo.create`/`add_payment_installment` n'utilisent **aucun
schéma Pydantic** pour la création (dict libre côté `create_transaction`, kwargs positionnels
côté `caisse_retrait_repo.create`) — contrairement à `medical_records`/`prescriptions`, pas
besoin de modifier de classe `*Create`, juste de lire/passer une clé `uuid` optionnelle
supplémentaire.

- [ ] **Step 1: Écrire les tests qui échouent**

```python
# tests/test_caisse_uuid.py
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from api_backend.backend_app.routes.retrait import retrait_endpoints
from tests.conftest import create_test_user, auth_headers

TEST_PASSWORD = "TestPass123!"


def test_create_transaction_avec_uuid_client_le_persiste(db_session, api_client):
    """Chantier 4 sous-projet 3 : une transaction caisse creee hors ligne
    (PowerSync) fournit son propre uuid - le serveur doit le persister tel
    quel, jamais en generer un nouveau."""
    secretaire = create_test_user(db_session, "test_caisse_uuid_secretaire", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_uuid_secretaire", TEST_PASSWORD)

    client_uuid = "aaaaaaaa-1111-2222-3333-444444444444"
    resp = client.post("/caisse/", json={
        "amount": 50.0,
        "advance_amount": 50.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 50.0, "quantity": 1, "line_total": 50.0}],
        "uuid": client_uuid,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] == client_uuid


def test_create_transaction_sans_uuid_en_genere_un(db_session, api_client):
    """Non-regression : la creation en ligne (aucun uuid fourni) continue
    de fonctionner, Postgres genere le uuid comme avant ce chantier."""
    secretaire = create_test_user(db_session, "test_caisse_uuid_secretaire2", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_uuid_secretaire2", TEST_PASSWORD)

    resp = client.post("/caisse/", json={
        "amount": 30.0,
        "advance_amount": 30.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 30.0, "quantity": 1, "line_total": 30.0}],
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] is not None


def test_create_retrait_avec_uuid_client_le_persiste(db_session, api_client):
    secretaire = create_test_user(db_session, "test_retrait_uuid_secretaire", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_uuid_secretaire", TEST_PASSWORD)

    client_uuid = "bbbbbbbb-1111-2222-3333-444444444444"
    resp = client.post("/retrait/", json={
        "amount": 20.0,
        "justification": "Test retrait uuid",
        "uuid": client_uuid,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] == client_uuid
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `python -m pytest tests/test_caisse_uuid.py -v`
Expected: FAIL — `uuid` non reconnu/non renvoyé par les 3 endpoints.

- [ ] **Step 3: `repositories/caisse_repo.py::create_transaction`**

Dans `create_transaction`, juste après la construction de l'objet `tx = Caisse(...)` (avant
`self.session.add(tx)`), ajouter la conversion et l'affectation du uuid s'il est fourni :

```python
        tx = Caisse(
            patient_id       = data.get("patient_id"),
            patient_label    = data.get("patient_label"),
            amount           = data["amount"],
            advance_amount   = 0.0,
            paid_at          = data.get("paid_at", datetime.now()),
            created_by_name  = current_user.username,
            handled_by       = current_user.user_id,
            payment_method   = data["payment_method"],
            transaction_type = data["transaction_type"],
            note             = data.get("note"),
            status           = 'active'
        )
        if data.get("uuid"):
            import uuid as uuid_lib
            tx.uuid = uuid_lib.UUID(str(data["uuid"]))
        self.session.add(tx)
```

(L'import local `import uuid as uuid_lib` à l'intérieur de la méthode suit le motif déjà
utilisé par `repositories/appointment_repo.py` pour ce même besoin — vérifier le style réel de
ce fichier avant d'écrire, pour rester cohérent.)

- [ ] **Step 4: `repositories/caisse_repo.py::add_payment_installment`**

Dans `add_payment_installment`, dans la construction de `payment = PaiementEchelonne(...)`,
ajouter la même logique :

```python
        payment = PaiementEchelonne(
            transaction_id = transaction_id,
            paid_amount    = data["paid_amount"],
            payment_method = data["payment_method"],
            payment_type   = data.get("payment_type", "VERSEMENT"),
            handled_by     = current_user.user_id,
            note           = data.get("note", "")
        )
        if data.get("uuid"):
            import uuid as uuid_lib
            payment.uuid = uuid_lib.UUID(str(data["uuid"]))
        self.session.add(payment)
```

- [ ] **Step 5: `repositories/caisse_retrait_repo.py::create`**

Remplacer la signature et le corps :

```python
    def create(self, amount: float, justification: str, handled_by: int,
               category: str = None, payment_method: str = None, uuid: str = None) -> CaisseRetrait:
        """
        Insère un nouveau retrait actif avec les détails optionnels.
        """
        new_retrait = CaisseRetrait(
            amount=amount,
            justification=justification,
            handled_by=handled_by,
            category=category,
            payment_method=payment_method
        )
        if uuid:
            import uuid as uuid_lib
            new_retrait.uuid = uuid_lib.UUID(str(uuid))
        self.session.add(new_retrait)
        self.session.commit()
        return new_retrait
```

- [ ] **Step 6: `controller/caisse_retrait_controller.py::effectuer_retrait`**

Remplacer la signature et l'appel au repo :

```python
    def effectuer_retrait(self, amount: float, justification: str,
                          category: str = None, payment_method: str = None, uuid: str = None) -> CaisseRetrait:
        """
        Crée un nouveau retrait avec catégorie et méthode de paiement.
        """
        if amount <= 0:
            raise ValueError("Le montant du retrait doit être strictement positif.")

        return self.repo.create(
            amount=amount,
            justification=justification,
            handled_by=self.user.user_id,
            category=category,
            payment_method=payment_method,
            uuid=uuid,
        )
```

- [ ] **Step 7: `api_backend/backend_app/routes/retrait/retrait_endpoints.py`**

Dans `create_retrait`, ajouter le paramètre et le passer au contrôleur :

```python
@router.post("/", response_model=Any, status_code=status.HTTP_201_CREATED)
def create_retrait(
    amount: float = Body(..., gt=0),
    justification: str = Body(...),
    category: Optional[str] = Body(None),
    payment_method: Optional[str] = Body(None),
    uuid: Optional[str] = Body(None),
    retrait_ctrl: CaisseRetraitController = Depends(get_retrait_controller),
):
    try:
        retrait = retrait_ctrl.effectuer_retrait(
            amount=amount,
            justification=justification,
            category=category,
            payment_method=payment_method,
            uuid=uuid,
        )
        return normalize_retrait_data(retrait)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except IntegrityError as ie:
```

(Ne modifier que la signature et l'appel — le reste du corps de la fonction, y compris le
`except IntegrityError` et ce qui suit, reste identique.)

- [ ] **Step 8: `api_backend/backend_app/routes/caisse/caisse_schemas.py`**

Dans `InstallmentPaymentIn`, ajouter :

```python
class InstallmentPaymentIn(BaseModel):
    paid_amount: float = Field(..., gt=0, description="Montant du versement effectué maintenant.")
    payment_method: str = Field(..., description="Mode de paiement utilisé pour ce versement (ex: Espèces, Virement).")
    payment_type: Optional[str] = Field("VERSEMENT_ECHEANCE", description="Type de versement. Par défaut 'VERSEMENT_ECHEANCE', peut être 'SOLDE'.")
    note: Optional[str] = Field(None, description="Note spécifique à ce versement.")
    uuid: Optional[str] = Field(None, description="UUID client (creation hors ligne PowerSync) - si absent, Postgres en genere un")

    class Config:
        from_attributes = True
```

Dans `PaymentEchelonneOut`, ajouter le champ et son validateur (même motif que
`AppointmentResponse`/`MedicalRecordResponse`/`PrescriptionResponse` — la colonne est un
`UUID(as_uuid=True)`, Pydantic v2 ne coerce plus automatiquement en `str`) :

```python
class PaymentEchelonneOut(BaseModel):
    payment_id: int
    transaction_id: int
    paid_amount: float
    payment_date: datetime
    payment_method: str
    payment_type: str
    handled_by: int
    note: Optional[str]
    uuid: Optional[str] = None

    @field_validator("uuid", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        return str(v) if v is not None else v

    class Config:
        from_attributes = True
```

(Vérifier si `field_validator` est déjà importé en tête de `caisse_schemas.py` avant d'ajouter
l'import — sinon l'ajouter : `from pydantic import BaseModel, Field, field_validator`.)

- [ ] **Step 9: `api_backend/backend_app/routes/caisse/mapping.py::normalize_caisse_data`**

Ajouter une entrée dans le dict de `normalize_data(raw, {...})`, dans le bloc "Identifiants" :

```python
        "transaction_id": lambda r: get_field(r, "transaction_id"),
        "caisse_id": lambda r: get_field(r, "transaction_id"),
        "uuid": lambda r: str(get_field(r, "uuid")) if get_field(r, "uuid") else None,
```

- [ ] **Step 10: `api_backend/backend_app/routes/retrait/mapping.py::normalize_retrait_data`**

Ajouter une clé dans le dict retourné :

```python
    return {
        "retrait_id": retrait.retrait_id,
        "amount": float(retrait.amount),
        "uuid": str(retrait.uuid) if retrait.uuid else None,
```

(Insérer juste après `"amount"` — vérifier le reste des clés existantes du dict avant d'écrire,
pour insérer au bon endroit sans dupliquer/casser une clé existante.)

- [ ] **Step 11: Lancer les tests pour vérifier qu'ils passent**

Run: `python -m pytest tests/test_caisse_uuid.py -v`
Expected: PASS (3 tests)

- [ ] **Step 12: Non-régression**

Run: `python -m pytest tests/test_caisse.py tests/test_retrait.py -v`
Expected: mêmes résultats qu'avant cette tâche (échecs déjà documentés inchangés, aucun nouveau).

---

### Task 3: Règles de sync PowerSync — caisse, retrait, paiement, stock

**Files:**
- Modify: `powersync/sync-config.yaml`

**Interfaces:**
- Consumes: colonnes `uuid` (Tâche 1), colonnes réelles de `caisse`/`caisse_retrait`/
  `paiement_echelonne`/`pharmacy` (vérifiées ci-dessous).
- Produces: streams `secretariat_caisse`, `secretariat_retraits`, `secretariat_payments`,
  `secretariat_pharmacy_stock` — consommés par la Tâche 6 (`client.js`).

**Rappel du piège déjà rencontré au sous-projet 2** : le parseur SQL de PowerSync (sous-ensemble,
pas du Postgres complet) rejette `EXISTS(...)` et les colonnes non qualifiées dès qu'un `JOIN`
met 2 tables en scope. Aucune des 4 requêtes ci-dessous n'utilise `EXISTS` ni de `JOIN` — si le
service rejette quand même l'une d'elles au démarrage (`docker logs`), adapter en qualifiant
toutes les colonnes par table, même motif que la correction déjà appliquée à
`clinical_lab_results` au sous-projet 2.

- [ ] **Step 1: Ajouter les 4 nouveaux streams**

```yaml
  secretariat_caisse:
    auto_subscribe: false
    queries:
      # Pas de filtre par secretaire proprietaire - toutes les transactions
      # sont visibles a l'ecran caisse aujourd'hui (pas de cloisonnement
      # par utilisateur cote REST non plus), meme politique hors ligne.
      - SELECT uuid::text AS id, transaction_id AS server_id, patient_id,
          patient_label, amount::text AS amount, advance_amount::text AS advance_amount,
          paid_at::text AS paid_at, payment_method, transaction_type, note,
          status, upload_error
        FROM caisse

  secretariat_retraits:
    auto_subscribe: false
    queries:
      - SELECT uuid::text AS id, retrait_id AS server_id, amount::text AS amount,
          justification, retrait_at::text AS retrait_at, status, category,
          payment_method
        FROM caisse_retrait

  secretariat_payments:
    auto_subscribe: false
    queries:
      - SELECT uuid::text AS id, payment_id AS server_id, transaction_id,
          paid_amount::text AS paid_amount, payment_date::text AS payment_date,
          payment_method, payment_type, note
        FROM paiement_echelonne

  secretariat_pharmacy_stock:
    auto_subscribe: false
    queries:
      # Lecture seule (jamais d'ecriture locale) - affichage informatif du
      # stock au moment de la vente hors ligne, decision utilisateur
      # 2026-09-23 (pas de verification/deduction cote client, la
      # deduction reelle reste exclusivement serveur au moment de l'upload).
      - SELECT medication_id::text AS id, medication_id AS server_id,
          drug_name, quantity, threshold, price::text AS price, stock_status
        FROM pharmacy
```

- [ ] **Step 2: Redémarrer le service PowerSync**

Run: `docker restart powersync-powersync-1`
Expected: démarrage propre. Vérifier : `docker logs powersync-powersync-1 --tail 50` — aucune
erreur de parsing. Si une requête est rejetée, l'adapter selon le motif déjà rencontré
(qualification des colonnes) et redémarrer à nouveau jusqu'à un démarrage propre.

---

### Task 4: Tables locales PowerSync — caisse, retrait, paiement, stock

**Files:**
- Modify: `ah2-admin-web/src/powersync-client/AppSchema.js`

**Interfaces:**
- Consumes: colonnes exposées par les streams de la Tâche 3.
- Produces: tables locales `caisse`, `caisse_retrait`, `paiement_echelonne`,
  `pharmacy_stock` — consommées par la Tâche 5.

- [ ] **Step 1: Étendre `AppSchema.js`**

Ajouter ces 4 nouvelles définitions de table juste avant `export const AppSchema = new Schema({`,
et les ajouter à l'objet passé à `new Schema({...})` :

```javascript
const caisse = new Table(
  {
    server_id: column.integer,
    patient_id: column.integer,
    patient_label: column.text,
    // items : les lignes de facture ne sont JAMAIS creees/modifiees
    // independamment de leur transaction parente (aucun flux "ajouter une
    // ligne a une facture existante" dans l'API) - stockees ici en JSON
    // texte plutot que dans une table enfant separee. Plus simple ET plus
    // robuste qu'un caisse_item local : une seule ligne PowerSync a
    // ecrire/uploader par vente, pas de resolution parent->enfant a gerer.
    // LIMITE CONNUE (a verifier empiriquement en Tache 10, pas suppose) :
    // le stream secretariat_caisse (Tache 3) ne selectionne PAS cette
    // colonne (caisse_item vit dans une table serveur separee, jamais
    // synchronisee) - si le merge de lignes PowerSync remplace la ligne
    // locale entiere a chaque confirmation serveur, "items" pourrait
    // redevenir vide apres synchronisation complete d'une vente. Purement
    // cosmetique si constate (la vraie donnee reste intacte cote Postgres,
    // consultable en ligne) - documenter dans SUIVI-AVANCEMENT.md comme
    // limite connue si confirme, ne pas complexifier ce plan pour le
    // corriger a priori sans preuve du comportement reel.
    items: column.text,
    amount: column.text,
    advance_amount: column.text,
    paid_at: column.text,
    payment_method: column.text,
    transaction_type: column.text,
    note: column.text,
    status: column.text,
    // Garde-fou anti-perte-silencieuse (voir Tache 1/5) - jamais nul cote
    // serveur pour une ligne saine, rempli seulement si l'upload a
    // definitivement echoue.
    upload_error: column.text,
  },
  { indexes: { by_patient: ['patient_id'] } }
);

const caisse_retrait = new Table({
  server_id: column.integer,
  amount: column.text,
  justification: column.text,
  retrait_at: column.text,
  status: column.text,
  category: column.text,
  payment_method: column.text,
});

const paiement_echelonne = new Table(
  {
    server_id: column.integer,
    // transaction_id : entier server_id d'une transaction DEJA
    // synchronisee (paiement echelonne hors ligne desactive tant que la
    // transaction visee n'a pas de server_id, decision utilisateur
    // 2026-09-23 - jamais un uuid local ici, contrairement a
    // prescriptions.medical_record_id qui pouvait chainer 2 creations dans
    // le meme geste).
    transaction_id: column.integer,
    paid_amount: column.text,
    payment_date: column.text,
    payment_method: column.text,
    payment_type: column.text,
    note: column.text,
  },
  { indexes: { by_transaction: ['transaction_id'] } }
);

// Lecture seule - jamais d'ecriture locale (pas de PUT/PATCH pour
// pharmacy_stock dans DossierConnector.js). Stock affiche a titre
// informatif au moment de la vente hors ligne, jamais verifie/deduit cote
// client - decision utilisateur 2026-09-23.
const pharmacy_stock = new Table(
  {
    server_id: column.integer,
    drug_name: column.text,
    quantity: column.integer,
    threshold: column.integer,
    price: column.text,
    stock_status: column.text,
  },
);
```

Puis dans `export const AppSchema = new Schema({ ... })`, ajouter les 4 nouvelles tables après
`lab_results,` :

```javascript
export const AppSchema = new Schema({
  appointments,
  patients_lookup,
  doctors_lookup,
  patients,
  medical_records,
  prescriptions,
  lab_results,
  caisse,
  caisse_retrait,
  paiement_echelonne,
  pharmacy_stock,
});
```

- [ ] **Step 2: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 5: Connecteur — extension de `DossierConnector.js` + garde-fou anti-perte-silencieuse

**Files:**
- Modify: `ah2-admin-web/src/powersync-client/DossierConnector.js`

**Interfaces:**
- Consumes: tables locales de la Tâche 4, `CaisseGateway` (Tâche 7/8 — méthodes déjà existantes,
  inchangées : `createInvoice`, `addPayment`, `createRetrait`).
- Produces: cases `caisse:PUT`, `caisse_retrait:PUT`, `paiement_echelonne:PUT` dans
  `uploadData()`, plus le garde-fou `upload_error`.

- [ ] **Step 1: Ajouter les imports**

En tête de `DossierConnector.js`, ajouter :

```javascript
import { CaisseGateway } from '@/services/CaisseGateway';
```

- [ ] **Step 2: Ajouter les 3 nouveaux cases dans `uploadData()`**

Ajouter ces 3 cases au `switch (`${op.table}:${op.op}`)`, juste avant le `default:` existant
(après le case `'prescriptions:PUT'`) :

```javascript
          case 'caisse:PUT': {
            // items stocke en JSON texte localement (voir AppSchema.js,
            // Tache 4) - reconstruit en tableau avant l'appel gateway, qui
            // envoie exactement le meme payload que le formulaire en ligne
            // (CaisseInvoiceModal.vue) - toute la logique metier (stock,
            // paiement initial) reste geree cote serveur, jamais reproduite
            // ici.
            await CaisseGateway.createInvoice({
              patient_id: op.opData.patient_id,
              patient_label: op.opData.patient_label,
              amount: Number(op.opData.amount),
              advance_amount: Number(op.opData.advance_amount),
              payment_method: op.opData.payment_method,
              transaction_type: op.opData.transaction_type,
              note: op.opData.note,
              items: op.opData.items ? JSON.parse(op.opData.items) : [],
              uuid: op.id,
            });
            break;
          }
          case 'caisse_retrait:PUT': {
            await CaisseGateway.createRetrait({
              amount: Number(op.opData.amount),
              justification: op.opData.justification,
              category: op.opData.category,
              payment_method: op.opData.payment_method,
              uuid: op.id,
            });
            break;
          }
          case 'paiement_echelonne:PUT': {
            // Desactive cote UI tant que la transaction visee n'a pas de
            // server_id (Tache 9) - ce garde-fou existe aussi ici en
            // seconde ligne de defense, meme motif que la resolution
            // consultation->prescription du sous-projet 2.
            if (!op.opData.transaction_id) {
              console.warn(`Versement ${op.id} : aucune transaction_id associee, ignore pour cet upload.`);
              break;
            }
            await CaisseGateway.addPayment(op.opData.transaction_id, {
              paid_amount: Number(op.opData.paid_amount),
              payment_method: op.opData.payment_method,
              payment_type: op.opData.payment_type,
              note: op.opData.note,
              uuid: op.id,
            });
            break;
          }
```

- [ ] **Step 3: Garde-fou anti-perte-silencieuse pour `caisse`**

Remplacer le bloc `catch` de `uploadData()` (actuellement) :

```javascript
    } catch (error) {
      console.error('Erreur upload PowerSync:', lastOp, error);
      if (isFatalUploadError(error)) {
        console.error(`Operation ${lastOp?.op} sur ${lastOp?.table}/${lastOp?.id} abandonnee (erreur non recuperable) - retiree de la file.`);
        await transaction.complete();
      } else {
        // Erreur reseau/serveur transitoire - ne pas completer la
        // transaction, PowerSync retentera plus tard.
        throw error;
      }
    }
```

par :

```javascript
    } catch (error) {
      console.error('Erreur upload PowerSync:', lastOp, error);
      if (isFatalUploadError(error)) {
        console.error(`Operation ${lastOp?.op} sur ${lastOp?.table}/${lastOp?.id} abandonnee (erreur non recuperable) - retiree de la file.`);
        // Garde-fou (registre Important, sous-projet 3) : une vente caisse
        // ne doit JAMAIS disparaitre silencieusement (ex. stock insuffisant
        // au moment de l'upload, alors qu'elle a ete reellement encaissee
        // au guichet). Persiste un signal visible au lieu du simple log
        // console habituel pour les autres tables.
        if (lastOp?.table === 'caisse') {
          try {
            const detail = error?.response?.data?.detail || 'Echec de synchronisation - contacter un administrateur.';
            await database.execute('UPDATE caisse SET upload_error = ? WHERE id = ?', [detail, lastOp.id]);
          } catch (markError) {
            console.error('Impossible de marquer la transaction en echec de sync:', markError);
          }
        }
        await transaction.complete();
      } else {
        // Erreur reseau/serveur transitoire - ne pas completer la
        // transaction, PowerSync retentera plus tard.
        throw error;
      }
    }
```

- [ ] **Step 4: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 6: Souscription par rôle (`client.js`)

**Files:**
- Modify: `ah2-admin-web/src/powersync-client/client.js`

**Interfaces:**
- Consumes: streams de la Tâche 3.
- Produces: rien de nouveau consommé ailleurs.

- [ ] **Step 1: Étendre `openConnection(role)`**

Dans `ah2-admin-web/src/powersync-client/client.js`, après le bloc déjà existant pour
`medecin`/`nurse` (`if (role === 'medecin' || role === 'nurse') { ... }`), ajouter :

```javascript
    if (role === 'secretaire') {
      streamHandles.push(db.syncStream('secretariat_caisse'));
      streamHandles.push(db.syncStream('secretariat_retraits'));
      streamHandles.push(db.syncStream('secretariat_payments'));
      streamHandles.push(db.syncStream('secretariat_pharmacy_stock'));
    }
```

(Ce bloc vient juste avant `activeSubscriptions = await Promise.all(streamHandles.map((s) => s.subscribe()));`
— ne pas le placer après.)

- [ ] **Step 2: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 7: Écriture/lecture caisse — `caisseStore.js` + `CaisseGateway.js`

**Files:**
- Modify: `ah2-admin-web/src/stores/caisseStore.js`
- Modify: `ah2-admin-web/src/services/CaisseGateway.js`

**Interfaces:**
- Consumes: table locale `caisse` (Tâche 4), `authStore.hasRole(['secretaire'])`.
- Produces: `createInvoice(payload)`/`addPayment(transactionId, data)` inchangés dans leur
  signature. `fetchTransactions()` gagne un secours local sur échec réseau réel.
  `CaisseGateway.searchProducts` gagne un secours local sur échec réseau réel — consommé
  directement par `CaisseInvoiceModal.vue` sans changement de son propre code.

- [ ] **Step 1: Importer `db` et `useAuthStore` dans `caisseStore.js`**

```javascript
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';
```

- [ ] **Step 2: Local refresh après écriture (appliqué dès maintenant — leçon du registre
  Important I1 du sous-projet 2, pas après coup)**

Ajouter cette fonction juste après `fetchTransactions` :

```javascript
    // Rafraichit transactions/totalItems depuis la table locale (pas de
    // pagination/filtre serveur) - beneficie a TOUT ecran consommant ce
    // store, pas seulement celui qui a declenche l'ecriture (meme correctif
    // qu'applique en fix round au sous-projet 2, applique ici des la
    // conception). transaction_id/amount_paid/amount_due/patient_name
    // recalcules ici pour que CaisseList.vue (Tache 9, deja lu en entier)
    // continue de fonctionner sans modification de son template au-dela de
    // ce que la Tache 9 ajoute explicitement - ce sont normalement des
    // champs calcules cote serveur (normalize_caisse_data), reproduits
    // fidelement ici a partir des memes colonnes brutes. patient_name n'a
    // pas d'equivalent local exact (le nom vient d'une jointure Patient
    // cote serveur, jamais synchronisee) - patient_label sert de repli,
    // deja un champ saisi par la secretaire pour un patient sans dossier.
    async function refreshTransactionsLocal() {
        const rows = await db.getAll('SELECT * FROM caisse ORDER BY paid_at DESC');
        transactions.value = rows.map((r) => ({
            ...r,
            transaction_id: r.server_id,
            amount: Number(r.amount),
            advance_amount: Number(r.advance_amount),
            amount_paid: Number(r.advance_amount),
            amount_due: Number(r.amount) - Number(r.advance_amount),
            patient_name: r.patient_label,
            items: r.items ? JSON.parse(r.items) : [],
        }));
        totalItems.value = rows.length;
    }
```

- [ ] **Step 3: Brancher `createInvoice` sur l'écriture locale pour `secretaire`**

Remplacer entièrement :

```javascript
    async function createInvoice(payload) {
        const resp = await CaisseGateway.createInvoice(payload);
        await fetchTransactions();
        return resp.data;
    }
```

par :

```javascript
    // Ecriture locale (pas d'appel REST direct) pour secretaire - en ligne
    // comme hors ligne. items serialise en JSON texte (voir AppSchema.js,
    // Tache 4). Retourne un objet minimal { transaction_id: uuid } - le
    // uuid local tient lieu d'id en attendant confirmation serveur, aucun
    // ecran de ce chantier n'enchaine dessus (contrairement au sous-projet
    // 2, ou createMedicalRecord() devait retourner un id exploitable pour
    // la prescription liee).
    async function createInvoice(payload) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['secretaire'])) {
            const uuid = crypto.randomUUID();
            await db.execute(
                `INSERT INTO caisse (
                    id, patient_id, patient_label, items, amount, advance_amount,
                    paid_at, payment_method, transaction_type, note, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')`,
                [
                    uuid, payload.patient_id || null, payload.patient_label || null,
                    JSON.stringify(payload.items || []), String(payload.amount),
                    String(payload.advance_amount || 0), new Date().toISOString(),
                    payload.payment_method, payload.transaction_type, payload.note || null,
                ]
            );
            await refreshTransactionsLocal();
            return { transaction_id: uuid };
        }

        const resp = await CaisseGateway.createInvoice(payload);
        await fetchTransactions();
        return resp.data;
    }
```

- [ ] **Step 4: Brancher `addPayment` sur l'écriture locale pour `secretaire`**

Remplacer entièrement :

```javascript
    async function addPayment(transactionId, data) {
        const resp = await CaisseGateway.addPayment(transactionId, data);
        await fetchTransactions();
        return resp.data;
    }
```

par :

```javascript
    // transactionId doit toujours etre un server_id reel (entier) - le
    // bouton "verser un paiement" est desactive cote UI (Tache 9) tant que
    // la transaction visee n'a pas ete synchronisee, decision utilisateur
    // 2026-09-23 (contrairement au chainage consultation->prescription du
    // sous-projet 2, jamais un uuid local ici).
    async function addPayment(transactionId, data) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['secretaire'])) {
            const uuid = crypto.randomUUID();
            await db.execute(
                `INSERT INTO paiement_echelonne (
                    id, transaction_id, paid_amount, payment_date, payment_method, payment_type, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?)`,
                [
                    uuid, transactionId, String(data.paid_amount), new Date().toISOString(),
                    data.payment_method, data.payment_type || 'VERSEMENT_ECHEANCE', data.note || null,
                ]
            );
            await refreshTransactionsLocal();
            return { payment_id: uuid };
        }

        const resp = await CaisseGateway.addPayment(transactionId, data);
        await fetchTransactions();
        return resp.data;
    }
```

- [ ] **Step 5: Secours local sur échec réseau pour `fetchTransactions`**

Remplacer entièrement :

```javascript
    async function fetchTransactions() {
        isLoading.value = true;
        loadError.value = false;
        try {
            const resp = await CaisseGateway.fetchTransactions(filters.value);
            const body = resp.data;
            transactions.value = body.data || [];
            totalItems.value = body.total || 0;
            await updateKpis();
        } catch (err) {
            console.error('Erreur chargement des transactions caisse:', err);
            transactions.value = [];
            totalItems.value = 0;
            loadError.value = true;
            throw err;
        } finally {
            isLoading.value = false;
        }
    }
```

par :

```javascript
    async function fetchTransactions() {
        isLoading.value = true;
        loadError.value = false;
        try {
            const resp = await CaisseGateway.fetchTransactions(filters.value);
            const body = resp.data;
            transactions.value = body.data || [];
            totalItems.value = body.total || 0;
            await updateKpis();
        } catch (err) {
            const authStore = useAuthStore();
            // meme motif que patientDossierStore.fetchDossierComplete
            // (sous-projet 2) - !err.response signifie une vraie coupure
            // reseau, jamais une erreur applicative a masquer.
            if (!err.response && authStore.hasRole(['secretaire'])) {
                console.warn('Caisse hors ligne - secours sur la table locale PowerSync:', err);
                await refreshTransactionsLocal();
                loadError.value = false;
            } else {
                console.error('Erreur chargement des transactions caisse:', err);
                transactions.value = [];
                totalItems.value = 0;
                loadError.value = true;
                throw err;
            }
        } finally {
            isLoading.value = false;
        }
    }
```

- [ ] **Step 6: Secours local pour `CaisseGateway.searchProducts`**

Dans `ah2-admin-web/src/services/CaisseGateway.js`, ajouter l'import en tête :

```javascript
import { db } from '@/powersync-client/client';
```

Remplacer entièrement `searchProducts` :

```javascript
    async searchProducts(query) {
        if (!query || query.trim().length < 2) return { data: [] };
        try {
            const resp = await api.get('/pharmacy/', { params: { term: query.trim(), per_page: 8 } });
            return resp.data;
        } catch (err) {
            // Secours hors ligne (secretaire) - affichage informatif du
            // stock synchronise, jamais une verification/deduction reelle
            // (voir spec, decision utilisateur 2026-09-23). Pas de garde de
            // role ici : searchProducts() n'est appele que depuis
            // CaisseInvoiceModal.vue, deja accessible uniquement a
            // secretaire/admin cote routeur - admin utilise toujours le
            // chemin HTTP en pratique (jamais hors ligne pour ce role),
            // donc ce secours ne s'active jamais pour lui en pratique.
            if (!err.response) {
                const rows = await db.getAll(
                    "SELECT * FROM pharmacy_stock WHERE drug_name LIKE ? ORDER BY drug_name LIMIT 8",
                    [`%${query.trim()}%`]
                );
                return {
                    data: rows.map((r) => ({
                        medication_id: r.server_id,
                        drug_name: r.drug_name,
                        quantity: r.quantity,
                        price: Number(r.price),
                    })),
                };
            }
            throw err;
        }
    },
```

- [ ] **Step 7: Exposer `refreshTransactionsLocal` dans le `return` du store**

Ajouter `refreshTransactionsLocal,` dans le `return { ... }` final de `caisseStore.js` (après
`fetchTransactions,`).

- [ ] **Step 8: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 8: Écriture/lecture retrait — `retraitStore.js`

**Files:**
- Modify: `ah2-admin-web/src/stores/retraitStore.js`

**Interfaces:**
- Consumes: table locale `caisse_retrait` (Tâche 4), `authStore.hasRole(['secretaire'])`.
- Produces: `createRetrait(payload)` inchangé dans sa signature.

- [ ] **Step 1: Importer `db` et `useAuthStore`**

En tête de `ah2-admin-web/src/stores/retraitStore.js`, ajouter après les imports existants :

```javascript
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';
```

- [ ] **Step 2: Ajouter `refreshRetraitsLocal()`**

Ajouter cette fonction juste après `fetchRetraits` :

```javascript
    // Meme motif que caisseStore.refreshTransactionsLocal (Tache 7).
    async function refreshRetraitsLocal() {
        const rows = await db.getAll('SELECT * FROM caisse_retrait ORDER BY retrait_at DESC');
        retraits.value = rows.map((r) => ({ ...r, amount: Number(r.amount) }));
        totalItems.value = rows.length;
    }
```

- [ ] **Step 3: Brancher `createRetrait` sur l'écriture locale pour `secretaire`**

Remplacer entièrement :

```javascript
    async function createRetrait(payload) {
        const resp = await CaisseGateway.createRetrait(payload);
        await fetchRetraits();
        return resp.data;
    }
```

par :

```javascript
    async function createRetrait(payload) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['secretaire'])) {
            const uuid = crypto.randomUUID();
            await db.execute(
                `INSERT INTO caisse_retrait (
                    id, amount, justification, category, payment_method, retrait_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, 'active')`,
                [
                    uuid, String(payload.amount), payload.justification,
                    payload.category || null, payload.payment_method, new Date().toISOString(),
                ]
            );
            await refreshRetraitsLocal();
            return { retrait_id: uuid };
        }

        const resp = await CaisseGateway.createRetrait(payload);
        await fetchRetraits();
        return resp.data;
    }
```

- [ ] **Step 4: Secours local sur échec réseau pour `fetchRetraits`**

Remplacer entièrement :

```javascript
    async function fetchRetraits() {
        isLoading.value = true;
        loadError.value = false;
        try {
            const resp = await CaisseGateway.fetchRetraits(filters.value);
            const body = resp.data;
            retraits.value = body.data || [];
            totalItems.value = body.total || 0;
        } catch (err) {
            console.error('Erreur chargement des retraits:', err);
            retraits.value = [];
            totalItems.value = 0;
            loadError.value = true;
            throw err;
        } finally {
            isLoading.value = false;
        }
    }
```

par :

```javascript
    async function fetchRetraits() {
        isLoading.value = true;
        loadError.value = false;
        try {
            const resp = await CaisseGateway.fetchRetraits(filters.value);
            const body = resp.data;
            retraits.value = body.data || [];
            totalItems.value = body.total || 0;
        } catch (err) {
            const authStore = useAuthStore();
            if (!err.response && authStore.hasRole(['secretaire'])) {
                console.warn('Retraits hors ligne - secours sur la table locale PowerSync:', err);
                await refreshRetraitsLocal();
                loadError.value = false;
            } else {
                console.error('Erreur chargement des retraits:', err);
                retraits.value = [];
                totalItems.value = 0;
                loadError.value = true;
                throw err;
            }
        } finally {
            isLoading.value = false;
        }
    }
```

- [ ] **Step 5: `cancelRetrait` — ne pas toucher**

Laisser `cancelRetrait` strictement inchangé (reste HTTP uniquement — annulation impossible
avant synchronisation, décision utilisateur, cohérent avec `caisseStore.cancelTransaction` non
plus touché par la Tâche 7).

- [ ] **Step 6: Exposer `refreshRetraitsLocal` dans le `return` du store**

Remplacer :

```javascript
    return {
        retraits, isLoading, loadError, filters, pagination,
        fetchRetraits, setPage, setFilters, createRetrait, cancelRetrait,
    };
```

par :

```javascript
    return {
        retraits, isLoading, loadError, filters, pagination,
        fetchRetraits, refreshRetraitsLocal, setPage, setFilters, createRetrait, cancelRetrait,
    };
```

- [ ] **Step 7: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 9: Câblage écran — désactivation annulation/versement avant sync, badge échec de sync

**Files:**
- Modify: `ah2-admin-web/src/views/modules/finance/CaisseList.vue`

**Interfaces:**
- Consumes: `transactions[].server_id`/`transactions[].upload_error` (Tâche 7, désormais
  présents sur les lignes locales), `caisseStore.refreshTransactionsLocal` (Tâche 7).
- Produces: rien de nouveau consommé ailleurs — dernière tâche de câblage du plan.

Le tableau des transactions (déjà lu en entier pendant la rédaction de ce plan) est dans
`CaisseList.vue`, boucle `v-for="tx in caisseStore.transactions" :key="tx.transaction_id"`.
Les 3 boutons d'action concernés utilisent déjà une garde `v-if="tx.status === 'active' && ..."`.

- [ ] **Step 1: Désactiver "Verser un paiement"/"Solder"/"Annuler" tant que `server_id` est absent**

Remplacer les 3 boutons existants (actuellement) :

```html
                  <button v-if="tx.status === 'active' && Number(tx.amount_due) > 0" @click="openInstallmentModal(tx)"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-green-600 hover:bg-green-50 hover:border-green-200 transition shadow-sm"
                          :title="t('caisse.actions.add_payment')">
                    <CurrencyDollarIcon class="h-4 w-4" />
                  </button>
                  <button v-if="tx.status === 'active' && Number(tx.amount_due) > 0" @click="handleSettle(tx)"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-indigo-600 hover:bg-indigo-50 hover:border-indigo-200 transition shadow-sm"
                          :title="t('caisse.actions.settle')">
                    <CheckBadgeIcon class="h-4 w-4" />
                  </button>
                  <button v-if="tx.status === 'active'" @click="openCancelModal(tx)"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-red-500 hover:bg-red-50 hover:border-red-200 transition shadow-sm"
                          :title="t('caisse.actions.cancel')">
                    <XCircleIcon class="h-4 w-4" />
                  </button>
```

par (ajout de `:disabled="!tx.transaction_id"` et `disabled:opacity-40 disabled:cursor-not-allowed`
sur les 3 boutons — `tx.transaction_id` vaut `undefined` pour une ligne locale pas encore
synchronisée, grâce à l'alias `transaction_id: r.server_id` posé par
`refreshTransactionsLocal()`, Tâche 7 ; toujours renseigné pour une ligne venue de l'API) :

```html
                  <button v-if="tx.status === 'active' && Number(tx.amount_due) > 0" @click="openInstallmentModal(tx)"
                          :disabled="!tx.transaction_id"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-green-600 hover:bg-green-50 hover:border-green-200 transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                          :title="tx.transaction_id ? t('caisse.actions.add_payment') : 'En attente de synchronisation'">
                    <CurrencyDollarIcon class="h-4 w-4" />
                  </button>
                  <button v-if="tx.status === 'active' && Number(tx.amount_due) > 0" @click="handleSettle(tx)"
                          :disabled="!tx.transaction_id"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-indigo-600 hover:bg-indigo-50 hover:border-indigo-200 transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                          :title="tx.transaction_id ? t('caisse.actions.settle') : 'En attente de synchronisation'">
                    <CheckBadgeIcon class="h-4 w-4" />
                  </button>
                  <button v-if="tx.status === 'active'" @click="openCancelModal(tx)"
                          :disabled="!tx.transaction_id"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-red-500 hover:bg-red-50 hover:border-red-200 transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                          :title="tx.transaction_id ? t('caisse.actions.cancel') : 'En attente de synchronisation'">
                    <XCircleIcon class="h-4 w-4" />
                  </button>
```

- [ ] **Step 2: Afficher le badge "échec de synchronisation" quand `upload_error` est renseigné**

Remplacer le bloc de statut existant (actuellement) :

```html
              <td class="px-6 py-4">
                <span v-if="tx.status === 'active'" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                  {{ t('caisse.status.active') }}
                </span>
                <span v-else class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-600">
                  {{ t('caisse.status.cancelled') }}
                </span>
              </td>
```

par :

```html
              <td class="px-6 py-4">
                <span v-if="tx.status === 'active'" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                  {{ t('caisse.status.active') }}
                </span>
                <span v-else class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-600">
                  {{ t('caisse.status.cancelled') }}
                </span>
                <span v-if="tx.upload_error" :title="tx.upload_error"
                      class="ml-1 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                  Échec de synchronisation
                </span>
              </td>
```

- [ ] **Step 3: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 10: Vérification finale (hors tâches, à la charge du contrôleur)

Aucun outil de navigateur disponible dans cet environnement agentique.

- [ ] Relancer la suite complète (`python -m pytest tests/ -q`) et confirmer qu'aucun nouvel
  échec n'apparaît en dehors des 9 échecs pré-existants documentés dans
  `docs/superpowers/SUIVI-AVANCEMENT.md`.
- [ ] Build frontend complet (`cd ah2-admin-web && npx vite build --mode production`).
- [ ] Demander à l'utilisateur de rejouer le protocole de test avec une **vraie coupure
  réseau** : ouvrir l'écran caisse déjà synchronisé → couper le réseau → créer une vente
  (medicament + service) → vérifier que le stock affiché reflète la dernière synchronisation →
  créer un retrait → reconnecter → vérifier côté serveur (réouverture de l'écran) que la
  transaction ET le retrait apparaissent avec leurs vrais id. Vérifier aussi que le bouton
  "verser un paiement"/"annuler" restent désactivés sur une ligne pas encore synchronisée, et
  se réactivent une fois la synchronisation confirmée.
- [ ] Vérification explicite : tenter (si possible en environnement de test) de provoquer un
  rejet serveur au moment de l'upload (ex. stock ramené à 0 entre la vente hors ligne et la
  reconnexion) et confirmer que le badge "échec de synchronisation" apparaît bien au lieu d'une
  disparition silencieuse de la transaction.
- [ ] Vérification explicite de la limite connue notée à la Tâche 4 (`items`) : après une vente
  créée hors ligne puis reconnexion, rouvrir l'écran caisse et vérifier si les lignes de la
  facture (`items`) sont toujours affichées dans la liste locale une fois la transaction
  confirmée synchronisée (`server_id` renseigné), ou si elles disparaissent. Si elles
  disparaissent, documenter cette limite dans `SUIVI-AVANCEMENT.md` (cosmétique, la donnée
  réelle reste intacte côté serveur, consultable via `GET /caisse/{id}` en ligne) plutôt que de
  la corriger dans l'immédiat.
