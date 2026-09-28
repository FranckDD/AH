# Chantier 7b — Caisse & Retrait Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the web app to the caisse/retrait back-end that already exists (multi-line invoices, versements, solde, annulation, PDF, retraits) — closing registre `L3b`/`L3e` — and fix the six real bugs (registre `F`) found in the exact code this UI exposes.

**Architecture:** Backend-first: fix `F1-F6` and add a cancellation-justification column pair to `caisse` (mirroring the existing `caisse_retrait` columns), then build two new operational screens under `/secretariat` (`CaisseList.vue` for invoices, `RetraitList.vue` for withdrawals) on top of a new `CaisseGateway.js`/`caisseStore.js`/`retraitStore.js` data layer, reusing patterns already established by `PatientList.vue`/`PatientModal.vue` (chantier 7a) and `ToxicoAdmissionModal.vue` (chantier 6, patient search-or-free-text).

**Tech Stack:** FastAPI + SQLAlchemy + PostgreSQL (Alembic migrations), Vue 3 (`<script setup>`, Pinia setup stores), vue-i18n, Tailwind, Heroicons.

**Spec:** `docs/superpowers/specs/2026-09-21-chantier-7b-caisse-retrait-design.md`

## Global Constraints

- `/dashboard/finance` (admin) is untouched — `FinancialList.vue` and `FinanceModal.vue` are not modified by this plan.
- Backend role guard on `/caisse/*` and `/retrait/*` stays `role_required("secretaire", "admin")` — unchanged.
- New web routes (`/secretariat/caisse`, `/secretariat/retrait`) stay `roles: [ROLES.SECRETAIRE]`, matching the existing pattern on this layout.
- The migration in Task 2 touches the real local AH2 database — apply it only after the user explicitly confirms at execution time (same rule as every prior chantier's migrations).
- `item_ref_id` for a "Service libre" invoice line is always `0` (never a real `Pharmacy`/`ConsultationSpirituel` id) — mirrors the fixture already on `HEAD` (`tests/conftest.py::create_test_transaction`, `item_type="Service"`).
- No frontend test framework exists in this repo (`ah2-admin-web/package.json` has no test script) — frontend verification is `npm run build` plus a manual QA checklist at the end of the plan (consistent with chantiers 6/7a/7c).

---

## Task 1: Backend fixes F1, F2, F3, F4

**Files:**
- Modify: `api_backend/backend_app/routes/caisse/mapping.py:36-39`
- Modify: `api_backend/backend_app/routes/caisse/caisse_endpoints.py` (imports, `delete_transaction`, `add_payment`)
- Modify: `repositories/caisse_repo.py:757-784` (`get_total_remaining_due`)
- Test: `tests/test_caisse.py`

**Interfaces:**
- Consumes: none (independent bug fixes on existing, already-deployed endpoints).
- Produces: correct `amount_due`/`amount_paid` fields in every `GET`/`POST` response that goes through `normalize_caisse_data` — Tasks 5, 8, 10 (frontend) rely on `amount_due` being `amount - advance_amount`.

- [ ] **Step 1: Update the two existing tests that currently document F1/F6 as bugs to instead assert correct behavior**

`tests/test_caisse.py` currently has `test_create_transaction_partial_payment_amount_due_bug` (lines 41-77) asserting the wrong values. Replace it:

```python
def test_create_transaction_partial_payment_computes_amount_due_and_paid_correctly(db_session, api_client):
    """
    Registre F1, corrige : amount_due = amount - advance_amount,
    amount_paid = advance_amount (mapping.py::normalize_caisse_data).
    """
    user = create_test_user(db_session, "test_caisse_secretaire_partial", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_partial", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "amount": 100.0,
        "advance_amount": 30.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
        ],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["amount"] == "100.00"
    assert body["advance_amount"] == "30.00"
    assert body["amount_due"] == "70.00"
    assert body["amount_paid"] == "30.00"
```

Rename the test function in place (find-and-replace the old function body with the one above, same location in the file).

- [ ] **Step 2: Run the updated test to verify it fails against current code**

Run: `pytest tests/test_caisse.py::test_create_transaction_partial_payment_computes_amount_due_and_paid_correctly -v`
Expected: FAIL — `amount_due` is `"130.00"` instead of `"70.00"`.

- [ ] **Step 3: Fix F1 in `mapping.py`**

In `api_backend/backend_app/routes/caisse/mapping.py`, replace lines 36-39:

```python
        # Montants (Correction critique ici)
        "amount": lambda r: parse_decimal(get_field(r, "amount")), # <--- C'est ce que le frontend attend
        "advance_amount": lambda r: parse_decimal(get_field(r, "advance_amount")),
        "amount_due": lambda r: parse_decimal(get_field(r, "amount") + get_field(r, "advance_amount")),
        "amount_paid": lambda r: parse_decimal(get_field(r, "amount")),
```

with:

```python
        # Montants
        "amount": lambda r: parse_decimal(get_field(r, "amount")),
        "advance_amount": lambda r: parse_decimal(get_field(r, "advance_amount")),
        "amount_due": lambda r: parse_decimal(get_field(r, "amount") - get_field(r, "advance_amount")),
        "amount_paid": lambda r: parse_decimal(get_field(r, "advance_amount")),
```

- [ ] **Step 4: Run the test again to verify it passes**

Run: `pytest tests/test_caisse.py::test_create_transaction_partial_payment_computes_amount_due_and_paid_correctly -v`
Expected: PASS

- [ ] **Step 5: Write a failing test for F2 (delete on a nonexistent id should 404)**

`tests/test_caisse.py` currently has `test_delete_transaction_nonexistent_returns_204_not_404` (lines 342-359) documenting the bug. Replace it with:

```python
def test_delete_transaction_nonexistent_returns_404(db_session, api_client):
    """Registre F2, corrige : DELETE sur un id inexistant renvoie 404."""
    create_test_user(db_session, "test_caisse_secretaire_delete404", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_delete404", TEST_PASSWORD)

    resp = client.delete("/caisse/999999999", headers=headers)

    assert resp.status_code == 404
```

- [ ] **Step 6: Run it to verify it fails**

Run: `pytest tests/test_caisse.py::test_delete_transaction_nonexistent_returns_404 -v`
Expected: FAIL — got 204 instead of 404.

- [ ] **Step 7: Fix F2 in `caisse_endpoints.py`**

In `api_backend/backend_app/routes/caisse/caisse_endpoints.py`, replace the `delete_transaction` endpoint (currently):

```python
@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    try:
        caisse_ctrl.delete_transaction(transaction_id)
        return None
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
```

with:

```python
@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    try:
        deleted = caisse_ctrl.delete_transaction(transaction_id)
        if deleted is None:
            raise HTTPException(status_code=404, detail=f"Aucune transaction trouvée pour l'ID = {transaction_id}")
        return None
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
```

- [ ] **Step 8: Run the F2 test again to verify it passes, then run the full delete-success test to make sure it still passes**

Run: `pytest tests/test_caisse.py::test_delete_transaction_nonexistent_returns_404 tests/test_caisse.py::test_delete_transaction_success -v`
Expected: both PASS

- [ ] **Step 9: Write a failing test for F3 (payment endpoint should return a real body)**

`tests/test_caisse.py` currently has `test_add_installment_payment_success` (lines 361-384) asserting `resp.json() == {}`. Replace the assertion:

```python
def test_add_installment_payment_success(db_session, api_client):
    """Registre F3, corrige : POST /caisse/{id}/payment renvoie le versement cree, pas {}."""
    user = create_test_user(db_session, "test_caisse_secretaire_payment", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=30.0)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_payment", TEST_PASSWORD)

    resp = client.post(
        f"/caisse/{tx.transaction_id}/payment",
        json={"paid_amount": 20.0, "payment_method": "Especes"},
        headers=headers,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["transaction_id"] == tx.transaction_id
    assert body["paid_amount"] == 20.0
    assert body["payment_method"] == "Especes"
    assert body["payment_id"]

    get_resp = client.get(f"/caisse/{tx.transaction_id}", headers=headers)
    assert get_resp.json()["advance_amount"] == "50.00"
```

- [ ] **Step 10: Run it to verify it fails**

Run: `pytest tests/test_caisse.py::test_add_installment_payment_success -v`
Expected: FAIL — `body == {}`, `KeyError: 'transaction_id'`.

- [ ] **Step 11: Fix F3 in `caisse_endpoints.py`**

Add `PaymentEchelonneOut` to the import block at the top of `api_backend/backend_app/routes/caisse/caisse_endpoints.py` (currently imports `FinancialKpiSchema, UnpaidTransactionSchema, PaymentDistributionSchema, PaymentDistributionItem, InstallmentPaymentIn`):

```python
from ..caisse.caisse_schemas import (
    FinancialKpiSchema, 
    UnpaidTransactionSchema, 
    PaymentDistributionSchema, 
    PaymentDistributionItem,
    InstallmentPaymentIn,
    PaymentEchelonneOut,
)
```

Then change the `add_payment` decorator from:

```python
@router.post("/{transaction_id}/payment", status_code=status.HTTP_201_CREATED)
```

to:

```python
@router.post("/{transaction_id}/payment", response_model=PaymentEchelonneOut, status_code=status.HTTP_201_CREATED)
```

- [ ] **Step 12: Run the F3 test again to verify it passes**

Run: `pytest tests/test_caisse.py::test_add_installment_payment_success -v`
Expected: PASS

- [ ] **Step 13: Write a failing test for F4 (remaining-due total should not implicitly filter by status when none is given)**

Add to `tests/test_caisse.py`:

```python
def test_total_remaining_due_without_status_includes_all_statuses(db_session, api_client):
    """
    Registre F4, corrige : sans parametre status explicite,
    get_total_remaining_due() ne doit plus filtrer implicitement
    status='active', comme ses deux voisins (total, total_payments).
    """
    user = create_test_user(db_session, "test_caisse_secretaire_remaining_nofilter", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_remaining_nofilter", TEST_PASSWORD)

    before = client.get("/caisse/total_remaining_due", headers=headers).json()
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=40.0)
    cancel_resp = client.post(f"/caisse/{tx.transaction_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200

    after = client.get("/caisse/total_remaining_due", headers=headers).json()
    assert after == before + 60.0
```

- [ ] **Step 14: Run it to verify it fails**

Run: `pytest tests/test_caisse.py::test_total_remaining_due_without_status_includes_all_statuses -v`
Expected: FAIL — the cancelled transaction's remaining due is excluded, `after == before`.

- [ ] **Step 15: Fix F4 in `repositories/caisse_repo.py`**

In `get_total_remaining_due` (currently around line 774), replace:

```python
        # IMPORTANT : On ne veut que les transactions actives (ou à votre convenance)
        query = query.filter(Caisse.status == (status or 'active'))
```

with:

```python
        # Comme get_total_transactions/get_total_payments : ne filtrer par
        # statut que si explicitement demande (registre F4).
        if status:
            query = query.filter(Caisse.status == status)
```

- [ ] **Step 16: Run the F4 test again, plus the pre-existing filtered test, to verify both pass**

Run: `pytest tests/test_caisse.py::test_total_remaining_due_without_status_includes_all_statuses tests/test_caisse.py::test_total_remaining_due_default_filters_active_status -v`

`test_total_remaining_due_default_filters_active_status` (existing test, lines 495-518) currently asserts the *old* implicit-active-filter behavior — it must be updated to pass an explicit `status=active` query param now that the default no longer filters:

Replace its two `client.get` calls:
```python
    before = client.get("/caisse/total_remaining_due?status=active", headers=headers).json()
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=40.0)
    after_active = client.get("/caisse/total_remaining_due?status=active", headers=headers).json()
    assert after_active == before + 60.0

    cancel_resp = client.post(f"/caisse/{tx.transaction_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    after_cancel = client.get("/caisse/total_remaining_due?status=active", headers=headers).json()
    assert after_cancel == before
```

Expected after this edit: both tests PASS.

- [ ] **Step 17: Run the whole caisse test file to catch any regression**

Run: `pytest tests/test_caisse.py -v`
Expected: all PASS

- [ ] **Step 18: Commit**

```bash
git add api_backend/backend_app/routes/caisse/mapping.py api_backend/backend_app/routes/caisse/caisse_endpoints.py repositories/caisse_repo.py tests/test_caisse.py
git commit -m "fix: correct caisse amount_due/amount_paid, delete 404, payment response, remaining-due filter (registre F1-F4)"
```

---

## Task 2: Migration — cancellation columns on `caisse`

**Files:**
- Create: `alembic/versions/006_caisse_cancel_justification.py`
- Modify: `models/caisse.py`
- Modify: `ci/schema_only.sql` (regenerated, not hand-edited)

**Interfaces:**
- Consumes: none.
- Produces: `Caisse.cancelled_by` (int, nullable), `Caisse.cancelled_at` (datetime, nullable), `Caisse.cancel_justification` (text, nullable) — consumed by Task 3.

- [ ] **Step 1: Write the migration**

Create `alembic/versions/006_caisse_cancel_justification.py`:

```python
"""add caisse cancellation columns (chantier 7b)

Revision ID: 006_caisse_cancel_justification
Revises: 005_medrec_appointment_id
Create Date: 2026-09-21 00:00:00.000000

Chantier 7b (docs/superpowers/SUIVI-AVANCEMENT.md, registre L3b) : ajoute
a la table caisse les 3 colonnes deja presentes sur caisse_retrait
(cancelled_by, cancelled_at, cancel_justification), pour que l'annulation
d'une transaction Caisse exige et enregistre une justification, comme le
fait deja l'annulation d'un retrait.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_caisse_cancel_justification'
down_revision: Union[str, Sequence[str], None] = '005_medrec_appointment_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        ALTER TABLE public.caisse
            ADD COLUMN IF NOT EXISTS cancelled_by integer
                REFERENCES public.users(user_id),
            ADD COLUMN IF NOT EXISTS cancelled_at timestamp without time zone,
            ADD COLUMN IF NOT EXISTS cancel_justification text;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        ALTER TABLE public.caisse
            DROP COLUMN IF EXISTS cancelled_by,
            DROP COLUMN IF EXISTS cancelled_at,
            DROP COLUMN IF EXISTS cancel_justification;
    """)
```

(`revision` string is 31 characters — under the 32-char `alembic_version.version_num` limit discovered in chantier 7c; verified before writing this file.)

- [ ] **Step 2: Update `models/caisse.py` to declare the new columns**

In `models/caisse.py`, add `DateTime` is already imported; add the three columns after `status`:

```python
    status          = Column(String, nullable=False, default='active')
    cancelled_by         = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    cancelled_at         = Column(DateTime, nullable=True)
    cancel_justification = Column(Text, nullable=True)
```

(`Text` is already imported at the top of `models/caisse.py`.)

- [ ] **Step 3: Ask the user for explicit confirmation before applying the migration to the real local AH2 database**

This is a real schema change against production-shaped local data — do not run `alembic upgrade head` without the user's explicit go-ahead at this point in execution (same rule followed for migrations 003/005).

- [ ] **Step 4: Apply the migration (only after confirmation)**

Run: `alembic upgrade head`
Expected: migration `006_caisse_cancel_justification` applied, no errors.

- [ ] **Step 5: Verify the columns exist**

Run a quick check via `psql` or the project's usual verification method that `public.caisse` now has `cancelled_by`, `cancelled_at`, `cancel_justification`.

- [ ] **Step 6: Regenerate `ci/schema_only.sql`**

Run: `pg_dump --schema-only --no-owner --no-privileges -h localhost -p 5432 -U postgres -d AH2 > ci/schema_only.sql`
(Use whatever connection parameters the project's existing dump command already uses — see `ci/schema_only.sql`'s own history from chantier 7c for the exact invocation used there.)

Diff the result to confirm the only changes are the 3 new columns on `caisse` (plus the routine pg_dump timestamp/version comment lines).

- [ ] **Step 7: Commit**

```bash
git add alembic/versions/006_caisse_cancel_justification.py models/caisse.py ci/schema_only.sql
git commit -m "feat: add cancellation columns to caisse table (migration 006)"
```

---

## Task 3: Backend — F5, F6, and cancellation with justification

**Files:**
- Modify: `repositories/caisse_repo.py` (`update_transaction`, `cancel_transaction`)
- Modify: `controller/caisse_controller.py` (`cancel_transaction`)
- Modify: `api_backend/backend_app/routes/caisse/caisse_endpoints.py` (`cancel_transaction`)
- Modify: `api_backend/backend_app/routes/caisse/mapping.py` (add cancellation fields)
- Test: `tests/test_caisse.py`

**Interfaces:**
- Consumes: `Caisse.cancelled_by`/`cancelled_at`/`cancel_justification` columns from Task 2.
- Produces: `POST /caisse/{id}/cancel` now requires `{"cancel_justification": "..."}` in the body (breaking change from the old no-body contract) — Task 5 (`CaisseCancelModal.vue`) and Task 10 (`CaisseList.vue`) build against this new contract. `normalize_caisse_data` now includes `cancelled_by`, `cancelled_at`, `cancel_justification` in every response.

- [ ] **Step 1: Write a failing test for F6 (partial PUT must not drop items)**

`tests/test_caisse.py` currently has `test_update_transaction_partial_payload_drops_all_items` (lines 270-301) documenting the bug. Replace it:

```python
def test_update_transaction_partial_payload_keeps_existing_items(db_session, api_client):
    """
    Registre F6, corrige : un PUT partiel qui omet "items" ne touche plus
    aux lignes existantes ni au stock. "items" absent = inchange ;
    "items": [] explicite = vide intentionnellement.
    """
    user = create_test_user(db_session, "test_caisse_secretaire_keepitems", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=0.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
    ])
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_keepitems", TEST_PASSWORD)

    resp = client.put(f"/caisse/{tx.transaction_id}", json={"note": "Partial update"}, headers=headers)

    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1
    assert resp.json()["note"] == "Partial update"

    get_resp = client.get(f"/caisse/{tx.transaction_id}", headers=headers)
    assert len(get_resp.json()["items"]) == 1


def test_update_transaction_explicit_empty_items_clears_lines(db_session, api_client):
    """Registre F6 : "items": [] explicite reste un vidage intentionnel."""
    user = create_test_user(db_session, "test_caisse_secretaire_clearitems", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=100.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
    ])
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_clearitems", TEST_PASSWORD)

    resp = client.put(f"/caisse/{tx.transaction_id}", json={"items": [], "advance_amount": 100.0}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["items"] == []
```

- [ ] **Step 2: Run both to verify they fail**

Run: `pytest tests/test_caisse.py::test_update_transaction_partial_payload_keeps_existing_items tests/test_caisse.py::test_update_transaction_explicit_empty_items_clears_lines -v`
Expected: the first FAILS (`len(items) == 0` instead of 1); the second PASSES already (documents existing behavior for the explicit-empty case, kept as a regression guard).

- [ ] **Step 3: Fix F6 in `repositories/caisse_repo.py::update_transaction`**

Currently (lines 354-366 and 388-420), the stock-restore-and-delete block and the reinsert block both run unconditionally. Wrap both in a single `if "items" in data:` gate. Replace the whole body from the comment `# 2) Rétablir d'abord le stock des anciennes lignes (avant MAJ)` through the end of the reinsert loop (currently ending right before `# 5) Commit final`) with:

```python
        # 2) Items : ne toucher aux lignes existantes et au stock QUE si
        # "items" est explicitement present dans le payload (registre F6).
        # Absent = ne pas toucher ; present (meme []) = remplacer.
        if "items" in data:
            existing_items = list(tx.items)
            for old_item in existing_items:
                if old_item.item_type.lower() in ("médicament", "medication", "carnet", "booklet"):
                    med = self.session.get(Pharmacy, old_item.item_ref_id)
                    if med:
                        med.quantity += old_item.quantity
                        med.update_stock_status()
                        self.session.add(med)
            for old_item in existing_items:
                self.session.delete(old_item)
            self.session.flush()

            new_items = data.get("items", [])
            for line in new_items:
                item_type = line["item_type"]
                ref_id    = line["item_ref_id"]
                unit_price= line["unit_price"]
                qty       = line["quantity"]
                line_tot  = line["line_total"]
                item_note = line.get("note")

                if item_type.lower() in ("médicament", "medication", "carnet", "booklet"):
                    med = self.session.get(Pharmacy, ref_id)
                    if not med:
                        raise ValueError(f"Produit introuvable pour ID={ref_id}")
                    if med.quantity < qty:
                        raise ValueError(
                            f"Stock insuffisant pour produit ID={ref_id}. "
                            f"Demandé={qty}, disponible={med.quantity}"
                        )
                    med.quantity -= qty
                    med.update_stock_status()
                    self.session.add(med)

                new_item = CaisseItem(
                    transaction_id = transaction_id,
                    item_type      = item_type,
                    item_ref_id    = ref_id,
                    unit_price     = unit_price,
                    quantity       = qty,
                    line_total     = line_tot,
                    note           = item_note,
                    status         = 'active'
                )
                self.session.add(new_item)
```

Everything else in `update_transaction` (the header field updates, steps 1 and 3, and the final commit) stays exactly as-is.

- [ ] **Step 4: Run both F6 tests again to verify they pass**

Run: `pytest tests/test_caisse.py::test_update_transaction_partial_payload_keeps_existing_items tests/test_caisse.py::test_update_transaction_explicit_empty_items_clears_lines -v`
Expected: both PASS

- [ ] **Step 5: Write a failing test for F5 (double-cancel should be refused, mirroring retrait)**

`tests/test_caisse.py` currently has `test_cancel_transaction_already_cancelled_is_idempotent` (lines 430-449) documenting the old behavior. Replace it:

```python
def test_cancel_transaction_already_cancelled_returns_400(db_session, api_client):
    """
    Registre F5, corrige : annuler une transaction caisse deja annulee
    est maintenant refusee (400), comme pour un retrait
    (test_cancel_retrait_already_cancelled_returns_400, tests/test_retrait.py).
    """
    user = create_test_user(db_session, "test_caisse_secretaire_doublecancel", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_doublecancel", TEST_PASSWORD)

    first = client.post(f"/caisse/{tx.transaction_id}/cancel", json={"cancel_justification": "Premiere annulation"}, headers=headers)
    assert first.status_code == 200

    second = client.post(f"/caisse/{tx.transaction_id}/cancel", json={"cancel_justification": "Deuxieme annulation"}, headers=headers)
    assert second.status_code == 400
    assert "déjà annulée" in second.json()["detail"]
```

Also update the pre-existing `test_cancel_transaction_success` (lines 415-427) to send the now-required body:

```python
def test_cancel_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_cancel", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_cancel", TEST_PASSWORD)

    resp = client.post(f"/caisse/{tx.transaction_id}/cancel", json={"cancel_justification": "Erreur de saisie"}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["detail"] == "Annulé"

    get_resp = client.get(f"/caisse/{tx.transaction_id}", headers=headers)
    assert get_resp.json()["status"] == "cancelled"
    assert get_resp.json()["cancel_justification"] == "Erreur de saisie"
```

- [ ] **Step 6: Run both to verify they fail**

Run: `pytest tests/test_caisse.py::test_cancel_transaction_success tests/test_caisse.py::test_cancel_transaction_already_cancelled_returns_400 -v`
Expected: FAIL — `cancel_transaction` doesn't accept a justification yet, the endpoint doesn't read a body, and double-cancel still returns 200.

- [ ] **Step 7: Extend `cancel_transaction` in `repositories/caisse_repo.py`**

Replace the current `cancel_transaction` method (currently starting `def cancel_transaction(self, transaction_id: int, current_user) -> Caisse:` and printing debug lines) with:

```python
    def cancel_transaction(self, transaction_id: int, current_user, justification: str) -> Caisse:
        """
        Annule la transaction, restaure le stock, et enregistre qui/quand/
        pourquoi (registre F5 : refuse desormais une transaction deja
        annulee, comme caisse_retrait_repo.py::cancel_with_justification).
        """
        tx = self.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID={transaction_id}")

        if tx.status == 'cancelled':
            raise ValueError("Cette transaction est déjà annulée.")

        for item in tx.items:
            t_type = str(item.item_type).lower().strip()
            keywords = ["médicament", "medicament", "carnet", "booklet"]
            if any(k in t_type for k in keywords):
                med = self.session.get(Pharmacy, item.item_ref_id)
                if med:
                    med.quantity += item.quantity
                    if med.threshold and med.quantity <= med.threshold:
                        med.stock_status = 'bas'
                    elif med.quantity == 0:
                        med.stock_status = 'rupture'
                    else:
                        med.stock_status = 'normal'
                    self.session.add(med)

                    movement = StockMovement(
                        medication_id = med.medication_id,
                        change_qty    = item.quantity,
                        movement_type = "ANNULATION_VENTE",
                        created_by    = getattr(current_user, "username", "System"),
                        note          = f"Annul. Tx #{tx.transaction_id}"
                    )
                    self.session.add(movement)

        tx.status = 'cancelled'
        tx.cancelled_by = getattr(current_user, "user_id", None)
        tx.cancelled_at = datetime.utcnow()
        tx.cancel_justification = justification
        self.session.add(tx)

        for item in tx.items:
            item.status = 'cancelled'
            self.session.add(item)

        self.session.commit()
        return tx
```

`datetime` is already imported at the top of `repositories/caisse_repo.py` (`from datetime import datetime, date`).

- [ ] **Step 8: Update `controller/caisse_controller.py::cancel_transaction` to pass the justification through**

Replace:

```python
    def cancel_transaction(self, transaction_id: int) -> Caisse:
        tx = self.repo.cancel_transaction(transaction_id, self.user)
        
        # --- AUDIT ---
        if self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="Transaction",
                    action_performed="CANCEL",
                    resource_id=transaction_id,
                    details="Annulation transaction financière"
                )
            except Exception:
                logger.exception("Échec de l'écriture d'audit")
```

with:

```python
    def cancel_transaction(self, transaction_id: int, justification: str) -> Caisse:
        tx = self.repo.cancel_transaction(transaction_id, self.user, justification)
        
        # --- AUDIT ---
        if self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="Transaction",
                    action_performed="CANCEL",
                    resource_id=transaction_id,
                    details=f"Annulation transaction financière : {justification}"
                )
            except Exception:
                logger.exception("Échec de l'écriture d'audit")
```

(the rest of the method — cache invalidation and `return tx` — stays unchanged)

- [ ] **Step 9: Update `caisse_endpoints.py::cancel_transaction` to require the justification in the body**

Replace:

```python
@router.post("/{transaction_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_transaction(transaction_id: int, caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    try:
        caisse_ctrl.cancel_transaction(transaction_id)
        return {"detail": "Annulé"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
```

with:

```python
@router.post("/{transaction_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_transaction(
    transaction_id: int,
    cancel_justification: str = Body(..., embed=True),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    try:
        caisse_ctrl.cancel_transaction(transaction_id, cancel_justification)
        return {"detail": "Annulé"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
```

(`Body` is already imported at the top of `caisse_endpoints.py`.)

- [ ] **Step 10: Add the cancellation fields to `normalize_caisse_data`**

In `api_backend/backend_app/routes/caisse/mapping.py`, add after the `"status": "status",` line:

```python
        "status": "status",
        "cancelled_by": "cancelled_by",
        "cancelled_at": lambda r: parse_datetime(get_field(r, "cancelled_at")),
        "cancel_justification": "cancel_justification",
```

- [ ] **Step 11: Run the F5 tests again to verify they pass, then run the whole caisse test file**

Run: `pytest tests/test_caisse.py -v`
Expected: all PASS

- [ ] **Step 12: Commit**

```bash
git add repositories/caisse_repo.py controller/caisse_controller.py api_backend/backend_app/routes/caisse/caisse_endpoints.py api_backend/backend_app/routes/caisse/mapping.py tests/test_caisse.py
git commit -m "fix: require justification on caisse cancellation, refuse double-cancel, stop F6 item-wipe on partial PUT (registre F5-F6)"
```

---

## Task 4: Frontend data layer — `CaisseGateway.js`, `caisseStore.js`, `retraitStore.js`

**Files:**
- Create: `ah2-admin-web/src/services/CaisseGateway.js`
- Create: `ah2-admin-web/src/stores/caisseStore.js`
- Create: `ah2-admin-web/src/stores/retraitStore.js`

**Interfaces:**
- Consumes: `api` default export from `ah2-admin-web/src/services/api.js` (axios instance with auth interceptor already wired).
- Produces (consumed by Tasks 5-10):
  - `CaisseGateway.searchPatients(query)`, `.searchProducts(query)`, `.searchConsultations(query)`, `.fetchTransactions(params)`, `.createInvoice(payload)`, `.addPayment(transactionId, data)`, `.settleTransaction(transactionId)`, `.cancelTransaction(transactionId, justification)`, `.downloadInvoiceUrl(transactionId)`, `.fetchKpis(params)`, `.fetchRetraits(params)`, `.createRetrait(payload)`, `.cancelRetrait(retraitId, justification)`.
  - `useCaisseStore()`: state `transactions`, `isLoading`, `loadError`, `kpi`, `kpiError`, `filters`, `pagination`; actions `fetchTransactions()`, `setPage(page)`, `setFilters(newFilters)`, `createInvoice(payload)`, `addPayment(transactionId, data)`, `settleTransaction(transactionId)`, `cancelTransaction(transactionId, justification)`.
  - `useRetraitStore()`: state `retraits`, `isLoading`, `loadError`, `filters`, `pagination`; actions `fetchRetraits()`, `setPage(page)`, `setFilters(newFilters)`, `createRetrait(payload)`, `cancelRetrait(retraitId, justification)`.

- [ ] **Step 1: Create `CaisseGateway.js`**

```javascript
import api from '@/services/api';

const cleanParams = (params) => {
    const cleaned = {};
    for (const key in params) {
        const value = params[key];
        if (value !== null && value !== undefined && value !== '') {
            cleaned[key] = value;
        }
    }
    return cleaned;
};

export const CaisseGateway = {

    // --- RECHERCHE (pour la construction d'une facture) ---

    async searchPatients(query) {
        if (!query || query.trim().length < 2) return { data: [] };
        const resp = await api.get('/patients/', { params: { search: query.trim(), per_page: 8 } });
        return resp.data;
    },

    async searchProducts(query) {
        if (!query || query.trim().length < 2) return { data: [] };
        const resp = await api.get('/pharmacy/', { params: { term: query.trim(), per_page: 8 } });
        return resp.data;
    },

    async searchConsultations(query) {
        if (!query || query.trim().length < 2) return { data: [] };
        const resp = await api.get('/cs/', { params: { search: query.trim(), per_page: 8 } });
        return resp.data;
    },

    // --- CAISSE ---

    async fetchTransactions(params) {
        const query = {
            page: params.page || 1,
            per_page: params.per_page || 20,
            term: params.searchQuery,
            status: params.status,
            date_from: params.startDate,
            date_to: params.endDate,
        };
        return api.get('/caisse/', { params: cleanParams(query) });
    },

    async fetchKpis(params) {
        const query = {
            date_from: params.startDate,
            date_to: params.endDate,
        };
        return api.get('/caisse/dashboard/caisse/kpis', { params: cleanParams(query) });
    },

    async getTransaction(transactionId) {
        return api.get(`/caisse/${transactionId}`);
    },

    async createInvoice(payload) {
        return api.post('/caisse/', payload);
    },

    async addPayment(transactionId, data) {
        return api.post(`/caisse/${transactionId}/payment`, data);
    },

    async settleTransaction(transactionId) {
        return api.post(`/caisse/${transactionId}/settle`);
    },

    async cancelTransaction(transactionId, justification) {
        return api.post(`/caisse/${transactionId}/cancel`, { cancel_justification: justification });
    },

    downloadInvoiceUrl(transactionId) {
        return `${api.defaults.baseURL}/caisse/${transactionId}/invoice/download`;
    },

    // --- RETRAIT ---

    async fetchRetraits(params) {
        const query = {
            page: params.page || 1,
            per_page: params.per_page || 20,
            term: params.searchQuery,
            status: params.status,
            date_from: params.startDate,
            date_to: params.endDate,
        };
        return api.get('/retrait/search', { params: cleanParams(query) });
    },

    async createRetrait(payload) {
        return api.post('/retrait/', payload);
    },

    async cancelRetrait(retraitId, justification) {
        return api.post(`/retrait/${retraitId}/cancel`, { cancel_justification: justification });
    },
};
```

`downloadInvoiceUrl` builds a plain URL (not an axios call) because the caller opens it directly as a download link — the endpoint requires an `Authorization` header, so Task 10 fetches the PDF via `api.get(..., {responseType: 'blob'})` rather than a bare `<a href>`; this method is kept only as a documented fallback for a same-tab open if ever needed, and is not otherwise used by Task 10 (see Task 10 Step for the actual blob-based download).

- [ ] **Step 2: Create `caisseStore.js`**

```javascript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { CaisseGateway } from '@/services/CaisseGateway';

export const useCaisseStore = defineStore('caisse', () => {

    const transactions = ref([]);
    const isLoading = ref(false);
    const loadError = ref(false);
    const totalItems = ref(0);

    const kpi = ref({ total_paid: 0, total_factured: 0, remaining_due: 0, recouvrement_rate: 0, total_transactions: 0 });
    const kpiError = ref(false);

    const filters = ref({
        page: 1,
        per_page: 20,
        searchQuery: '',
        status: 'active',
        startDate: '',
        endDate: '',
    });

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

    async function updateKpis() {
        kpiError.value = false;
        try {
            const resp = await CaisseGateway.fetchKpis({
                startDate: filters.value.startDate || new Date().toISOString().slice(0, 10),
                endDate: filters.value.endDate || new Date().toISOString().slice(0, 10),
            });
            kpi.value = resp.data;
        } catch (err) {
            console.error('Erreur KPI caisse:', err);
            kpiError.value = true;
        }
    }

    function setPage(page) {
        filters.value.page = page;
        fetchTransactions();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters, page: 1 };
        fetchTransactions();
    }

    async function createInvoice(payload) {
        const resp = await CaisseGateway.createInvoice(payload);
        await fetchTransactions();
        return resp.data;
    }

    async function addPayment(transactionId, data) {
        const resp = await CaisseGateway.addPayment(transactionId, data);
        await fetchTransactions();
        return resp.data;
    }

    async function settleTransaction(transactionId) {
        await CaisseGateway.settleTransaction(transactionId);
        await fetchTransactions();
    }

    async function cancelTransaction(transactionId, justification) {
        await CaisseGateway.cancelTransaction(transactionId, justification);
        await fetchTransactions();
    }

    const pagination = computed(() => ({
        page: filters.value.page,
        per_page: filters.value.per_page,
        total: totalItems.value,
        total_pages: Math.ceil(totalItems.value / filters.value.per_page) || 1,
    }));

    return {
        transactions, isLoading, loadError, kpi, kpiError, filters, pagination,
        fetchTransactions, setPage, setFilters,
        createInvoice, addPayment, settleTransaction, cancelTransaction,
    };
});
```

- [ ] **Step 3: Create `retraitStore.js`**

```javascript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { CaisseGateway } from '@/services/CaisseGateway';

export const useRetraitStore = defineStore('retrait', () => {

    const retraits = ref([]);
    const isLoading = ref(false);
    const loadError = ref(false);
    const totalItems = ref(0);

    const filters = ref({
        page: 1,
        per_page: 20,
        searchQuery: '',
        status: '',
        startDate: '',
        endDate: '',
    });

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

    function setPage(page) {
        filters.value.page = page;
        fetchRetraits();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters, page: 1 };
        fetchRetraits();
    }

    async function createRetrait(payload) {
        const resp = await CaisseGateway.createRetrait(payload);
        await fetchRetraits();
        return resp.data;
    }

    async function cancelRetrait(retraitId, justification) {
        await CaisseGateway.cancelRetrait(retraitId, justification);
        await fetchRetraits();
    }

    const pagination = computed(() => ({
        page: filters.value.page,
        per_page: filters.value.per_page,
        total: totalItems.value,
        total_pages: Math.ceil(totalItems.value / filters.value.per_page) || 1,
    }));

    return {
        retraits, isLoading, loadError, filters, pagination,
        fetchRetraits, setPage, setFilters, createRetrait, cancelRetrait,
    };
});
```

- [ ] **Step 4: Verify the build succeeds**

Run: `cd ah2-admin-web && npm run build`
Expected: build succeeds, no import/syntax errors on the 3 new files (they aren't imported anywhere yet, so this only catches syntax errors — full wiring is verified in later tasks).

- [ ] **Step 5: Commit**

```bash
git add ah2-admin-web/src/services/CaisseGateway.js ah2-admin-web/src/stores/caisseStore.js ah2-admin-web/src/stores/retraitStore.js
git commit -m "feat: add CaisseGateway and caisse/retrait Pinia stores"
```

---

## Task 5: `CaisseCancelModal.vue` (shared cancellation-with-justification modal)

**Files:**
- Create: `ah2-admin-web/src/components/caisse/CaisseCancelModal.vue`
- Modify: `ah2-admin-web/src/i18n.js` (add `caisse.cancel_modal.*` keys, fr + en)

**Interfaces:**
- Consumes: none (pure presentational component).
- Produces: emits `close` and `confirm(justification: string)` — consumed by Tasks 7 and 10.

- [ ] **Step 1: Create `CaisseCancelModal.vue`**

```vue
<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-sm">
    <div class="relative mx-auto w-full max-w-md bg-white shadow-xl rounded-2xl border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-100 bg-red-600 rounded-t-2xl flex justify-between items-center">
        <h3 class="text-lg font-bold text-white flex items-center">
          <ExclamationTriangleIcon class="h-6 w-6 mr-2" />
          {{ t('caisse.cancel_modal.title') }}
        </h3>
        <button @click="$emit('close')" class="text-red-100 hover:text-white transition">
          <span class="text-2xl font-bold">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
        <p class="text-sm text-gray-600">{{ label }}</p>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            {{ t('caisse.cancel_modal.justification') }} <span class="text-red-500">*</span>
          </label>
          <textarea
            v-model="justification"
            rows="3"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500"
            :placeholder="t('caisse.cancel_modal.justification_placeholder')"
          ></textarea>
        </div>

        <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-3 rounded text-sm text-red-700">
          {{ errorMessage }}
        </div>

        <div class="flex justify-end space-x-3 pt-2">
          <button type="button" @click="$emit('close')" :disabled="isSaving"
                  class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition disabled:opacity-50">
            {{ t('caisse.cancel_modal.cancel') }}
          </button>
          <button type="submit" :disabled="isSaving || !justification.trim()"
                  class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium shadow-sm transition disabled:opacity-50">
            {{ isSaving ? t('caisse.cancel_modal.saving') : t('caisse.cancel_modal.confirm') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline';

const props = defineProps({
  label: { type: String, default: '' },
  isSaving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
});
const emit = defineEmits(['close', 'confirm']);

const { t } = useI18n();
const justification = ref('');

const handleSubmit = () => {
  if (!justification.value.trim()) return;
  emit('confirm', justification.value.trim());
};
</script>
```

- [ ] **Step 2: Add i18n keys**

In `ah2-admin-web/src/i18n.js`, inside the `fr` block's `finance: { ... }` (starting line 358), add a sibling `caisse` key right after the `finance` block closes (after line 407's `},`):

```javascript
    caisse: {
      title: "Caisse",
      new_invoice: "Nouvelle facture",
      search_placeholder: "Rechercher une transaction...",
      table: {
        date: "Date",
        patient: "Patient",
        type: "Type",
        total: "Total",
        paid: "Payé",
        due: "Reste dû",
        status: "Statut",
        actions: "Actions",
      },
      status: {
        active: "Active",
        cancelled: "Annulée",
      },
      actions: {
        view: "Voir le détail",
        add_payment: "Ajouter un versement",
        settle: "Solder",
        cancel: "Annuler",
        download: "Télécharger la facture",
      },
      cancel_modal: {
        title: "Annuler la transaction",
        justification: "Justification",
        justification_placeholder: "Motif de l'annulation...",
        cancel: "Retour",
        confirm: "Confirmer l'annulation",
        saving: "Annulation...",
      },
    },
```

Add the same block, with English copy, into the `en` locale's own `finance: { ... }` sibling position (the `en` block mirrors `fr`'s structure at the file's second `finance:` occurrence, around line 1112):

```javascript
    caisse: {
      title: "Cash Desk",
      new_invoice: "New Invoice",
      search_placeholder: "Search a transaction...",
      table: {
        date: "Date",
        patient: "Patient",
        type: "Type",
        total: "Total",
        paid: "Paid",
        due: "Balance Due",
        status: "Status",
        actions: "Actions",
      },
      status: {
        active: "Active",
        cancelled: "Cancelled",
      },
      actions: {
        view: "View Details",
        add_payment: "Add Payment",
        settle: "Settle",
        cancel: "Cancel",
        download: "Download Invoice",
      },
      cancel_modal: {
        title: "Cancel Transaction",
        justification: "Justification",
        justification_placeholder: "Reason for cancellation...",
        cancel: "Back",
        confirm: "Confirm Cancellation",
        saving: "Cancelling...",
      },
    },
```

- [ ] **Step 3: Verify the build succeeds**

Run: `cd ah2-admin-web && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add ah2-admin-web/src/components/caisse/CaisseCancelModal.vue ah2-admin-web/src/i18n.js
git commit -m "feat: add shared cancellation-with-justification modal for caisse/retrait"
```

---

## Task 6: `RetraitModal.vue` (create a withdrawal)

**Files:**
- Create: `ah2-admin-web/src/components/caisse/RetraitModal.vue`
- Modify: `ah2-admin-web/src/i18n.js` (add `retrait.modal.*` keys, fr + en)

**Interfaces:**
- Consumes: none.
- Produces: emits `close` and `save(payload)` where `payload = { amount: number, justification: string, category: string|null, payment_method: string }` — consumed by Task 7.

- [ ] **Step 1: Create `RetraitModal.vue`**

```vue
<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
    <div class="relative mx-auto p-6 border w-full max-w-md shadow-xl rounded-2xl bg-white">
      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold text-gray-900">{{ t('retrait.modal.title') }}</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-5">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('retrait.modal.amount') }}</label>
          <div class="relative rounded-md shadow-sm">
            <input v-model.number="form.amount" type="number" min="1" step="0.01" required
                   class="block w-full pl-3 pr-12 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 sm:text-sm"
                   placeholder="0" />
            <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <span class="text-gray-500 sm:text-sm">FCFA</span>
            </div>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('retrait.modal.category') }}</label>
          <select v-model="form.category" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500 sm:text-sm">
            <option value="">-- {{ t('retrait.modal.category') }} --</option>
            <option value="SUPPLIES">{{ t('finance.categories.supplies') }}</option>
            <option value="SALARY">{{ t('finance.categories.salary') }}</option>
            <option value="MAINTENANCE">{{ t('finance.categories.maintenance') }}</option>
            <option value="BILLS">{{ t('finance.categories.bills') }}</option>
            <option value="OTHER">{{ t('finance.categories.other') }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.method') }}</label>
          <select v-model="form.paymentMethod" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500 sm:text-sm">
            <option value="Espèces">{{ t('finance.payment_methods.cash') }}</option>
            <option value="Mobile Money">{{ t('finance.payment_methods.mobile') }}</option>
            <option value="Virement">{{ t('finance.payment_methods.transfer') }}</option>
            <option value="Chèque">{{ t('finance.payment_methods.check') }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('retrait.modal.justification') }}</label>
          <textarea v-model="form.justification" rows="2" required
                    :placeholder="t('retrait.modal.justification_placeholder')"
                    class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500 sm:text-sm"></textarea>
        </div>

        <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-3 rounded text-sm text-red-700">
          {{ errorMessage }}
        </div>

        <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-100">
          <button type="button" @click="$emit('close')" :disabled="isSaving"
                  class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition shadow-sm disabled:opacity-50">
            {{ t('finance.modal.cancel') }}
          </button>
          <button type="submit" :disabled="isSaving || !isFormValid"
                  class="px-4 py-2 text-white rounded-lg shadow-md font-medium transition flex items-center bg-red-600 hover:bg-red-700 disabled:opacity-50">
            {{ isSaving ? t('caisse.cancel_modal.saving') : t('finance.modal.save') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  isSaving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
});
const emit = defineEmits(['close', 'save']);
const { t } = useI18n();

const form = reactive({
  amount: '',
  category: '',
  paymentMethod: 'Espèces',
  justification: '',
});

const isFormValid = computed(() => Number(form.amount) > 0 && form.justification.trim().length > 0);

const handleSubmit = () => {
  if (!isFormValid.value) return;
  emit('save', {
    amount: Number(form.amount),
    justification: form.justification.trim(),
    category: form.category || null,
    payment_method: form.paymentMethod,
  });
};
</script>
```

- [ ] **Step 2: Add i18n keys**

In `ah2-admin-web/src/i18n.js`, add to the `fr` block right after the `caisse: { ... }` block added in Task 5:

```javascript
    retrait: {
      title: "Retraits de caisse",
      new_retrait: "Nouveau retrait",
      search_placeholder: "Rechercher un retrait...",
      table: {
        date: "Date",
        amount: "Montant",
        justification: "Justification",
        category: "Catégorie",
        method: "Moyen de paiement",
        status: "Statut",
        actions: "Actions",
      },
      modal: {
        title: "Nouveau retrait",
        amount: "Montant (FCFA)",
        category: "Catégorie",
        justification: "Justification",
        justification_placeholder: "Motif du retrait...",
      },
    },
```

And the English mirror in the `en` block:

```javascript
    retrait: {
      title: "Cash Withdrawals",
      new_retrait: "New Withdrawal",
      search_placeholder: "Search a withdrawal...",
      table: {
        date: "Date",
        amount: "Amount",
        justification: "Justification",
        category: "Category",
        method: "Payment Method",
        status: "Status",
        actions: "Actions",
      },
      modal: {
        title: "New Withdrawal",
        amount: "Amount (FCFA)",
        category: "Category",
        justification: "Justification",
        justification_placeholder: "Reason for withdrawal...",
      },
    },
```

- [ ] **Step 3: Verify the build succeeds**

Run: `cd ah2-admin-web && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add ah2-admin-web/src/components/caisse/RetraitModal.vue ah2-admin-web/src/i18n.js
git commit -m "feat: add RetraitModal (withdrawal creation form)"
```

---

## Task 7: `RetraitList.vue`, route, and menu entry

**Files:**
- Create: `ah2-admin-web/src/views/modules/finance/RetraitList.vue`
- Modify: `ah2-admin-web/src/router/index.js` (new route)
- Modify: `ah2-admin-web/src/components/layout/SecretaireLayout.vue` (new menu entry)

**Interfaces:**
- Consumes: `useRetraitStore()` (Task 4), `RetraitModal.vue` (Task 6), `CaisseCancelModal.vue` (Task 5).
- Produces: closes registre `L3e` — the retrait screen is reachable at `/secretariat/retrait`.

- [ ] **Step 1: Create `RetraitList.vue`**

```vue
<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('retrait.title') }}</h1>
        <p class="text-sm text-gray-500">{{ retraitStore.pagination.total }} retraits</p>
      </div>
      <button @click="showCreateModal = true"
              class="flex items-center px-6 py-2.5 bg-red-600 text-white rounded-xl hover:bg-red-700 shadow-md shadow-red-200 transition font-semibold">
        <PlusCircleIcon class="h-5 w-5 mr-2" />
        {{ t('retrait.new_retrait') }}
      </button>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-wrap gap-4 items-end">
      <div class="flex-1 min-w-[200px]">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Recherche</label>
        <input v-model="searchQuery" type="text" :placeholder="t('retrait.search_placeholder')"
               class="block w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-red-500 focus:border-red-500 sm:text-sm" />
      </div>
      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Du</label>
        <input v-model="startDate" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500 sm:text-sm" />
      </div>
      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Au</label>
        <input v-model="endDate" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500 sm:text-sm" />
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div v-if="retraitStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></span>
      </div>
      <div v-else-if="retraitStore.loadError" class="p-10 text-center text-red-500">Erreur de chargement</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('retrait.table.date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('retrait.table.justification') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('retrait.table.category') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('retrait.table.amount') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('retrait.table.status') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('retrait.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="r in retraitStore.retraits" :key="r.retrait_id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ formatDate(r.retrait_at) }}</td>
              <td class="px-6 py-4 text-sm text-gray-900">{{ r.justification }}</td>
              <td class="px-6 py-4">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">
                  {{ r.category }}
                </span>
              </td>
              <td class="px-6 py-4 text-right font-bold text-sm text-red-600">- {{ formatCurrency(r.amount) }}</td>
              <td class="px-6 py-4">
                <span v-if="r.status === 'active'" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                  {{ t('caisse.status.active') }}
                </span>
                <span v-else class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-600">
                  {{ t('caisse.status.cancelled') }}
                </span>
              </td>
              <td class="px-6 py-4 text-right">
                <button v-if="r.status === 'active'" @click="openCancelModal(r)"
                        class="p-2 bg-white border border-gray-200 rounded-lg text-red-500 hover:bg-red-50 hover:border-red-200 transition shadow-sm"
                        :title="t('caisse.actions.cancel')">
                  <XCircleIcon class="h-4 w-4" />
                </button>
              </td>
            </tr>
            <tr v-if="retraitStore.retraits.length === 0">
              <td colspan="6" class="px-6 py-8 text-center text-gray-500 italic">Aucun retrait trouvé.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="retraitStore.pagination.total_pages > 1" class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
        <p class="text-sm text-gray-700">Page {{ retraitStore.pagination.page }} sur {{ retraitStore.pagination.total_pages }}</p>
        <div class="flex space-x-2">
          <button @click="goToPage(retraitStore.pagination.page - 1)" :disabled="retraitStore.pagination.page === 1" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronLeftIcon class="h-5 w-5" />
          </button>
          <button @click="goToPage(retraitStore.pagination.page + 1)" :disabled="retraitStore.pagination.page === retraitStore.pagination.total_pages" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronRightIcon class="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>

    <RetraitModal v-if="showCreateModal" :isSaving="isSavingCreate" :errorMessage="createError"
                  @close="showCreateModal = false" @save="handleCreate" />

    <CaisseCancelModal v-if="cancellingRetrait" :isSaving="isCancelling" :errorMessage="cancelError"
                        :label="`Retrait de ${formatCurrency(cancellingRetrait.amount)} du ${formatDate(cancellingRetrait.retrait_at)}`"
                        @close="cancellingRetrait = null" @confirm="handleCancel" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRetraitStore } from '@/stores/retraitStore';
import RetraitModal from '@/components/caisse/RetraitModal.vue';
import CaisseCancelModal from '@/components/caisse/CaisseCancelModal.vue';
import {
  PlusCircleIcon, ChevronLeftIcon, ChevronRightIcon, XCircleIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const retraitStore = useRetraitStore();

onMounted(() => {
  retraitStore.fetchRetraits();
});

const searchQuery = computed({
  get: () => retraitStore.filters.searchQuery,
  set: (val) => retraitStore.setFilters({ searchQuery: val }),
});
const startDate = computed({
  get: () => retraitStore.filters.startDate,
  set: (val) => retraitStore.setFilters({ startDate: val }),
});
const endDate = computed({
  get: () => retraitStore.filters.endDate,
  set: (val) => retraitStore.setFilters({ endDate: val }),
});

const goToPage = (page) => retraitStore.setPage(page);

const formatCurrency = (value) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value).replace('XOF', 'FCFA');
const formatDate = (iso) => (iso ? String(iso).split('T')[0] : '');

const showCreateModal = ref(false);
const isSavingCreate = ref(false);
const createError = ref('');

const mapErrorToMessage = (err) => {
  if (err.response) {
    const status = err.response.status;
    const detail = err.response.data?.detail;
    if (status === 422) return "Données invalides.";
    if (status === 400) return detail || "Requête invalide.";
    return `Erreur serveur (${status}) : ${detail || 'veuillez réessayer'}`;
  }
  if (err.request) return "Erreur réseau. Veuillez vérifier votre connexion.";
  return err.message || "Une erreur inattendue est survenue.";
};

const handleCreate = async (payload) => {
  isSavingCreate.value = true;
  createError.value = '';
  try {
    await retraitStore.createRetrait(payload);
    showCreateModal.value = false;
  } catch (err) {
    createError.value = mapErrorToMessage(err);
  } finally {
    isSavingCreate.value = false;
  }
};

const cancellingRetrait = ref(null);
const isCancelling = ref(false);
const cancelError = ref('');

const openCancelModal = (r) => {
  cancellingRetrait.value = r;
  cancelError.value = '';
};

const handleCancel = async (justification) => {
  isCancelling.value = true;
  cancelError.value = '';
  try {
    await retraitStore.cancelRetrait(cancellingRetrait.value.retrait_id, justification);
    cancellingRetrait.value = null;
  } catch (err) {
    cancelError.value = mapErrorToMessage(err);
  } finally {
    isCancelling.value = false;
  }
};
</script>
```

- [ ] **Step 2: Add the route**

In `ah2-admin-web/src/router/index.js`, in the `/secretariat` children array, after the `caisse` route (currently lines 320-328), add:

```javascript
      {
        path: 'retrait',
        name: 'secretariat-retrait',
        component: () => import('@/views/modules/finance/RetraitList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
```

- [ ] **Step 3: Add the menu entry**

In `ah2-admin-web/src/components/layout/SecretaireLayout.vue`, add `ArrowUpTrayIcon` to the heroicons import (currently `UserGroupIcon, CubeIcon, BanknotesIcon, SparklesIcon, Bars3Icon, Bars3CenterLeftIcon, HomeIcon`):

```javascript
import {
  UserGroupIcon,
  CubeIcon,
  BanknotesIcon,
  ArrowUpTrayIcon,
  SparklesIcon,
  Bars3Icon,
  Bars3CenterLeftIcon,
  HomeIcon
} from '@heroicons/vue/24/outline';
```

Then add a menu item after the `caisse` entry in `menuItems` (currently lines 147-151):

```javascript
  {
    path: '/secretariat/retrait',
    labelKey: 'secretariat.nav.retrait',
    icon: ArrowUpTrayIcon,
  },
```

Add the `secretariat.nav.retrait` i18n key next to the existing `secretariat.nav.caisse` key in both `fr` and `en` blocks of `ah2-admin-web/src/i18n.js` (search for `nav: {` under `secretariat:` in each locale block — add `retrait: "Retraits"` in `fr`, `retrait: "Withdrawals"` in `en`, alongside the existing `caisse` key there).

- [ ] **Step 4: Verify the build succeeds**

Run: `cd ah2-admin-web && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add ah2-admin-web/src/views/modules/finance/RetraitList.vue ah2-admin-web/src/router/index.js ah2-admin-web/src/components/layout/SecretaireLayout.vue ah2-admin-web/src/i18n.js
git commit -m "feat: add dedicated Retrait screen, route, and nav entry (closes L3e)"
```

---

## Task 8: `CaisseInvoiceModal.vue` (multi-line invoice creation)

**Files:**
- Create: `ah2-admin-web/src/components/caisse/CaisseInvoiceModal.vue`
- Modify: `ah2-admin-web/src/i18n.js` (add `caisse.invoice_modal.*` keys, fr + en)

**Interfaces:**
- Consumes: `CaisseGateway.searchPatients/searchProducts/searchConsultations` (Task 4).
- Produces: emits `close` and `save(payload)` where `payload` matches `CaisseController.create_transaction`'s contract: `{ patient_id, patient_label, amount, advance_amount, payment_method, transaction_type, note, items: [{item_type, item_ref_id, unit_price, quantity, line_total}] }` — consumed by Task 10.

- [ ] **Step 1: Create `CaisseInvoiceModal.vue`**

```vue
<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-sm">
    <div class="relative mx-auto w-full max-w-3xl bg-white shadow-xl rounded-2xl border border-gray-200 flex flex-col max-h-[90vh]">
      <div class="px-6 py-4 border-b border-gray-100 bg-green-600 rounded-t-2xl flex justify-between items-center flex-shrink-0">
        <h3 class="text-lg font-bold text-white">{{ t('caisse.invoice_modal.title') }}</h3>
        <button @click="$emit('close')" class="text-green-100 hover:text-white transition">
          <span class="text-2xl font-bold">&times;</span>
        </button>
      </div>

      <div class="p-6 overflow-y-auto space-y-6">
        <!-- PATIENT -->
        <div class="bg-gray-50 p-4 rounded-xl border border-gray-200">
          <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">{{ t('caisse.invoice_modal.section_patient') }}</h4>

          <div v-if="!selectedPatient" class="space-y-2">
            <input v-model="patientSearchQuery" @input="onPatientSearchInput" type="text"
                   :placeholder="t('caisse.invoice_modal.patient_search_placeholder')"
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500" />
            <ul v-if="patientResults.length" class="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-40 overflow-y-auto">
              <li v-for="p in patientResults" :key="p.patient_id" @click="selectPatient(p)"
                  class="px-3 py-2 hover:bg-green-50 cursor-pointer text-sm">
                <span class="font-medium">{{ p.first_name }} {{ p.last_name }}</span>
                <span class="text-gray-500 ml-2">{{ p.code_patient }}</span>
              </li>
            </ul>
            <div class="flex items-center gap-2 pt-1">
              <span class="text-xs text-gray-400">{{ t('caisse.invoice_modal.or') }}</span>
              <input v-model="patientLabel" type="text" :placeholder="t('caisse.invoice_modal.patient_label_placeholder')"
                     class="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-green-500 focus:border-green-500" />
            </div>
          </div>

          <div v-else class="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg px-3 py-2">
            <span class="text-sm font-medium text-green-900">
              {{ selectedPatient.first_name }} {{ selectedPatient.last_name }} ({{ selectedPatient.code_patient }})
            </span>
            <button type="button" @click="selectedPatient = null" class="text-xs text-green-700 hover:underline">
              {{ t('caisse.invoice_modal.change_patient') }}
            </button>
          </div>
        </div>

        <!-- LIGNES -->
        <div class="bg-gray-50 p-4 rounded-xl border border-gray-200">
          <div class="flex justify-between items-center mb-3">
            <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider">{{ t('caisse.invoice_modal.section_items') }}</h4>
            <div class="flex gap-2">
              <button type="button" @click="addLine('Médicament')" class="text-xs px-2 py-1 bg-white border border-gray-300 rounded hover:bg-gray-100">
                + {{ t('caisse.invoice_modal.line_type_pharmacy') }}
              </button>
              <button type="button" @click="addLine('Consultation')" class="text-xs px-2 py-1 bg-white border border-gray-300 rounded hover:bg-gray-100">
                + {{ t('caisse.invoice_modal.line_type_consultation') }}
              </button>
              <button type="button" @click="addLine('Service')" class="text-xs px-2 py-1 bg-white border border-gray-300 rounded hover:bg-gray-100">
                + {{ t('caisse.invoice_modal.line_type_service') }}
              </button>
            </div>
          </div>

          <div v-if="lines.length === 0" class="text-sm text-gray-400 italic py-2">
            {{ t('caisse.invoice_modal.no_lines') }}
          </div>

          <div v-for="(line, idx) in lines" :key="line.key" class="bg-white border border-gray-200 rounded-lg p-3 mb-2 space-y-2">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold uppercase text-gray-500">
                {{ line.itemType === 'Médicament' ? t('caisse.invoice_modal.line_type_pharmacy')
                   : line.itemType === 'Consultation' ? t('caisse.invoice_modal.line_type_consultation')
                   : t('caisse.invoice_modal.line_type_service') }}
              </span>
              <button type="button" @click="removeLine(idx)" class="text-red-500 hover:text-red-700">
                <TrashIcon class="h-4 w-4" />
              </button>
            </div>

            <!-- Pharmacie -->
            <div v-if="line.itemType === 'Médicament'">
              <div v-if="!line.refLabel" class="space-y-1">
                <input v-model="line.searchQuery" @input="onLineSearchInput(line, 'product')" type="text"
                       :placeholder="t('caisse.invoice_modal.search_product_placeholder')"
                       class="w-full px-3 py-1.5 border border-gray-300 rounded text-sm" />
                <ul v-if="line.searchResults.length" class="border border-gray-200 rounded divide-y divide-gray-100 max-h-32 overflow-y-auto">
                  <li v-for="prod in line.searchResults" :key="prod.medication_id" @click="selectProductLine(line, prod)"
                      class="px-2 py-1 hover:bg-green-50 cursor-pointer text-sm flex justify-between">
                    <span>{{ prod.drug_name }}</span>
                    <span class="text-gray-500">{{ prod.quantity }} {{ t('caisse.invoice_modal.in_stock') }}</span>
                  </li>
                </ul>
              </div>
              <div v-else class="text-sm font-medium text-gray-800">{{ line.refLabel }}</div>
            </div>

            <!-- Consultation -->
            <div v-if="line.itemType === 'Consultation'">
              <div v-if="!line.refLabel" class="space-y-1">
                <input v-model="line.searchQuery" @input="onLineSearchInput(line, 'consultation')" type="text"
                       :placeholder="t('caisse.invoice_modal.search_consultation_placeholder')"
                       class="w-full px-3 py-1.5 border border-gray-300 rounded text-sm" />
                <ul v-if="line.searchResults.length" class="border border-gray-200 rounded divide-y divide-gray-100 max-h-32 overflow-y-auto">
                  <li v-for="cons in line.searchResults" :key="cons.consultation_id" @click="selectConsultationLine(line, cons)"
                      class="px-2 py-1 hover:bg-green-50 cursor-pointer text-sm">
                    #{{ cons.consultation_id }} — {{ cons.type_consultation || t('caisse.invoice_modal.line_type_consultation') }}
                  </li>
                </ul>
              </div>
              <div v-else class="text-sm font-medium text-gray-800">{{ line.refLabel }}</div>
            </div>

            <!-- Service libre -->
            <div v-if="line.itemType === 'Service'">
              <input v-model="line.label" type="text" :placeholder="t('caisse.invoice_modal.service_label_placeholder')"
                     class="w-full px-3 py-1.5 border border-gray-300 rounded text-sm" />
            </div>

            <div class="grid grid-cols-3 gap-2">
              <div>
                <label class="text-xs text-gray-500">{{ t('caisse.invoice_modal.quantity') }}</label>
                <input v-model.number="line.quantity" type="number" min="1"
                       :disabled="line.itemType === 'Consultation'"
                       class="w-full px-2 py-1 border border-gray-300 rounded text-sm disabled:bg-gray-100" />
              </div>
              <div>
                <label class="text-xs text-gray-500">{{ t('caisse.invoice_modal.unit_price') }}</label>
                <input v-model.number="line.unitPrice" type="number" min="0" step="0.01"
                       class="w-full px-2 py-1 border border-gray-300 rounded text-sm" />
              </div>
              <div>
                <label class="text-xs text-gray-500">{{ t('caisse.invoice_modal.line_total') }}</label>
                <div class="px-2 py-1 text-sm font-semibold">{{ formatCurrency(lineTotal(line)) }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- PAIEMENT -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.category') }}</label>
            <select v-model="transactionType" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm">
              <option value="CONSULTATION">{{ t('finance.categories.consultation') }}</option>
              <option value="PHARMACY">{{ t('finance.categories.pharmacy') }}</option>
              <option value="HOSPITALIZATION">{{ t('finance.categories.hospitalization') }}</option>
              <option value="LAB">{{ t('finance.categories.lab') }}</option>
              <option value="DETOX">{{ t('finance.categories.detox') }}</option>
              <option value="OTHER">{{ t('finance.categories.other') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.method') }}</label>
            <select v-model="paymentMethod" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm">
              <option value="Espèces">{{ t('finance.payment_methods.cash') }}</option>
              <option value="Mobile Money">{{ t('finance.payment_methods.mobile') }}</option>
              <option value="Virement">{{ t('finance.payment_methods.transfer') }}</option>
              <option value="Chèque">{{ t('finance.payment_methods.check') }}</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('caisse.invoice_modal.advance_amount') }}</label>
            <input v-model.number="advanceAmount" type="number" min="0" :max="totalAmount" step="0.01"
                   class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm" />
          </div>
          <div class="flex flex-col justify-end">
            <span class="text-xs text-gray-500 uppercase font-bold">{{ t('caisse.invoice_modal.total') }}</span>
            <span class="text-2xl font-bold text-gray-900">{{ formatCurrency(totalAmount) }}</span>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.desc') }}</label>
          <textarea v-model="note" rows="2" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm"></textarea>
        </div>

        <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-3 rounded text-sm text-red-700">
          {{ errorMessage }}
        </div>
      </div>

      <div class="px-6 py-4 border-t border-gray-100 flex justify-end space-x-3 flex-shrink-0">
        <button type="button" @click="$emit('close')" :disabled="isSaving"
                class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition disabled:opacity-50">
          {{ t('finance.modal.cancel') }}
        </button>
        <button type="button" @click="handleSubmit" :disabled="isSaving || !isFormValid"
                class="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium shadow-md transition disabled:opacity-50">
          {{ isSaving ? t('caisse.cancel_modal.saving') : t('finance.modal.save') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { CaisseGateway } from '@/services/CaisseGateway';
import { TrashIcon } from '@heroicons/vue/24/outline';

const props = defineProps({
  isSaving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
});
const emit = defineEmits(['close', 'save']);
const { t } = useI18n();

const formatCurrency = (value) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value || 0).replace('XOF', 'FCFA');

// --- Patient ---
const patientSearchQuery = ref('');
const patientResults = ref([]);
const selectedPatient = ref(null);
const patientLabel = ref('');
let patientSearchTimeout = null;
const onPatientSearchInput = () => {
  clearTimeout(patientSearchTimeout);
  patientSearchTimeout = setTimeout(async () => {
    const body = await CaisseGateway.searchPatients(patientSearchQuery.value);
    patientResults.value = body.data || [];
  }, 300);
};
const selectPatient = (p) => {
  selectedPatient.value = p;
  patientResults.value = [];
  patientSearchQuery.value = '';
};

// --- Lignes ---
let lineKeySeq = 0;
const lines = ref([]);
const addLine = (itemType) => {
  lines.value.push(reactive({
    key: ++lineKeySeq,
    itemType,
    refId: itemType === 'Service' ? 0 : null,
    refLabel: '',
    label: '',
    searchQuery: '',
    searchResults: [],
    quantity: 1,
    unitPrice: 0,
  }));
};
const removeLine = (idx) => lines.value.splice(idx, 1);

let lineSearchTimeout = null;
const onLineSearchInput = (line, kind) => {
  clearTimeout(lineSearchTimeout);
  lineSearchTimeout = setTimeout(async () => {
    if (kind === 'product') {
      const body = await CaisseGateway.searchProducts(line.searchQuery);
      line.searchResults = body.data || [];
    } else {
      const body = await CaisseGateway.searchConsultations(line.searchQuery);
      line.searchResults = body.data || [];
    }
  }, 300);
};

const selectProductLine = (line, product) => {
  line.refId = product.medication_id;
  line.refLabel = product.drug_name;
  line.unitPrice = Number(product.price) || 0;
  line.searchResults = [];
};

const selectConsultationLine = (line, consultation) => {
  line.refId = consultation.consultation_id;
  line.refLabel = `#${consultation.consultation_id} — ${consultation.type_consultation || ''}`.trim();
  line.quantity = 1;
  line.unitPrice = Number(consultation.fr_amount_paid) || 0;
  line.searchResults = [];
};

const lineTotal = (line) => (Number(line.quantity) || 0) * (Number(line.unitPrice) || 0);
const totalAmount = computed(() => lines.value.reduce((sum, l) => sum + lineTotal(l), 0));

// --- Paiement ---
const transactionType = ref('CONSULTATION');
const paymentMethod = ref('Espèces');
const advanceAmount = ref(0);
const note = ref('');

const isLineComplete = (line) => {
  if (line.itemType === 'Service') return line.label.trim().length > 0 && lineTotal(line) > 0;
  return line.refId !== null && lineTotal(line) > 0;
};

const isFormValid = computed(() => {
  const patientOk = selectedPatient.value || patientLabel.value.trim().length > 0;
  const linesOk = lines.value.length > 0 && lines.value.every(isLineComplete);
  const advanceOk = Number(advanceAmount.value) >= 0 && Number(advanceAmount.value) <= totalAmount.value;
  return patientOk && linesOk && totalAmount.value > 0 && advanceOk;
});

const handleSubmit = () => {
  if (!isFormValid.value) return;

  const payload = {
    amount: totalAmount.value,
    advance_amount: Number(advanceAmount.value) || 0,
    payment_method: paymentMethod.value,
    transaction_type: transactionType.value,
    note: note.value?.trim() || null,
    items: lines.value.map((l) => ({
      item_type: l.itemType,
      item_ref_id: l.itemType === 'Service' ? 0 : l.refId,
      unit_price: Number(l.unitPrice) || 0,
      quantity: Number(l.quantity) || 1,
      line_total: lineTotal(l),
      note: l.itemType === 'Service' ? l.label.trim() : null,
    })),
  };

  if (selectedPatient.value) {
    payload.patient_id = selectedPatient.value.patient_id;
    payload.patient_label = null;
  } else {
    payload.patient_id = null;
    payload.patient_label = patientLabel.value.trim();
  }

  emit('save', payload);
};
</script>
```

- [ ] **Step 2: Add i18n keys**

In `ah2-admin-web/src/i18n.js`, add to the `fr` `caisse: { ... }` block (from Task 5), a sibling `invoice_modal` key:

```javascript
      invoice_modal: {
        title: "Nouvelle facture",
        section_patient: "Patient",
        section_items: "Lignes de facture",
        patient_search_placeholder: "Rechercher un patient existant...",
        or: "ou",
        patient_label_placeholder: "Nom du patient de passage (sans dossier)...",
        change_patient: "Changer",
        line_type_pharmacy: "Pharmacie",
        line_type_consultation: "Consultation spirituelle",
        line_type_service: "Service libre",
        no_lines: "Aucune ligne ajoutée. Utilisez les boutons ci-dessus.",
        search_product_placeholder: "Rechercher un médicament ou carnet...",
        search_consultation_placeholder: "Rechercher une consultation...",
        in_stock: "en stock",
        service_label_placeholder: "Description du service (ex: Hospitalisation 3 jours)...",
        quantity: "Quantité",
        unit_price: "Prix unitaire",
        line_total: "Total ligne",
        advance_amount: "Avance initiale",
        total: "Total facture",
      },
```

And the English mirror in the `en` `caisse: { ... }` block:

```javascript
      invoice_modal: {
        title: "New Invoice",
        section_patient: "Patient",
        section_items: "Invoice Lines",
        patient_search_placeholder: "Search an existing patient...",
        or: "or",
        patient_label_placeholder: "Walk-in patient name (no file)...",
        change_patient: "Change",
        line_type_pharmacy: "Pharmacy",
        line_type_consultation: "Spiritual Consultation",
        line_type_service: "Free-form Service",
        no_lines: "No line added yet. Use the buttons above.",
        search_product_placeholder: "Search a medication or booklet...",
        search_consultation_placeholder: "Search a consultation...",
        in_stock: "in stock",
        service_label_placeholder: "Service description (e.g. 3-day hospitalization)...",
        quantity: "Quantity",
        unit_price: "Unit Price",
        line_total: "Line Total",
        advance_amount: "Initial Advance",
        total: "Invoice Total",
      },
```

- [ ] **Step 3: Verify the build succeeds**

Run: `cd ah2-admin-web && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add ah2-admin-web/src/components/caisse/CaisseInvoiceModal.vue ah2-admin-web/src/i18n.js
git commit -m "feat: add multi-line invoice creation modal (CaisseInvoiceModal)"
```

---

## Task 9: `CaisseInstallmentModal.vue` (add a payment installment)

**Files:**
- Create: `ah2-admin-web/src/components/caisse/CaisseInstallmentModal.vue`
- Modify: `ah2-admin-web/src/i18n.js` (add `caisse.installment_modal.*` keys, fr + en)

**Interfaces:**
- Consumes: none.
- Produces: emits `close` and `confirm(data)` where `data = { paid_amount: number, payment_method: string, note: string|null }` — consumed by Task 10.

- [ ] **Step 1: Create `CaisseInstallmentModal.vue`**

```vue
<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
    <div class="relative mx-auto p-6 border w-full max-w-sm shadow-xl rounded-2xl bg-white">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold text-gray-900">{{ t('caisse.installment_modal.title') }}</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 transition">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <p class="text-sm text-gray-600 mb-4">
        {{ t('caisse.installment_modal.remaining_due') }}: <span class="font-bold">{{ formatCurrency(remainingDue) }}</span>
      </p>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('caisse.invoice_modal.unit_price') === '' ? '' : t('finance.modal.amount') }}</label>
          <input v-model.number="paidAmount" type="number" min="0.01" :max="remainingDue" step="0.01" required
                 class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('finance.modal.method') }}</label>
          <select v-model="paymentMethod" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm">
            <option value="Espèces">{{ t('finance.payment_methods.cash') }}</option>
            <option value="Mobile Money">{{ t('finance.payment_methods.mobile') }}</option>
            <option value="Virement">{{ t('finance.payment_methods.transfer') }}</option>
            <option value="Chèque">{{ t('finance.payment_methods.check') }}</option>
          </select>
        </div>

        <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-3 rounded text-sm text-red-700">
          {{ errorMessage }}
        </div>

        <div class="flex justify-end space-x-3 pt-2">
          <button type="button" @click="$emit('close')" :disabled="isSaving"
                  class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition disabled:opacity-50">
            {{ t('finance.modal.cancel') }}
          </button>
          <button type="submit" :disabled="isSaving || !(paidAmount > 0)"
                  class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium shadow-sm transition disabled:opacity-50">
            {{ isSaving ? t('caisse.cancel_modal.saving') : t('finance.modal.save') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  remainingDue: { type: Number, required: true },
  isSaving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
});
const emit = defineEmits(['close', 'confirm']);
const { t } = useI18n();

const paidAmount = ref(props.remainingDue);
const paymentMethod = ref('Espèces');

const formatCurrency = (value) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value || 0).replace('XOF', 'FCFA');

const handleSubmit = () => {
  if (!(paidAmount.value > 0)) return;
  emit('confirm', { paid_amount: Number(paidAmount.value), payment_method: paymentMethod.value, note: null });
};
</script>
```

- [ ] **Step 2: Add i18n keys**

In `ah2-admin-web/src/i18n.js`, add to the `fr` `caisse: { ... }` block:

```javascript
      installment_modal: {
        title: "Ajouter un versement",
        remaining_due: "Reste dû",
      },
```

And the English mirror:

```javascript
      installment_modal: {
        title: "Add a Payment",
        remaining_due: "Balance Due",
      },
```

- [ ] **Step 3: Verify the build succeeds**

Run: `cd ah2-admin-web && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add ah2-admin-web/src/components/caisse/CaisseInstallmentModal.vue ah2-admin-web/src/i18n.js
git commit -m "feat: add payment installment modal (CaisseInstallmentModal)"
```

---

## Task 10: `CaisseList.vue` (operational screen, replaces `/secretariat/caisse`)

**Files:**
- Create: `ah2-admin-web/src/views/modules/finance/CaisseList.vue`
- Modify: `ah2-admin-web/src/router/index.js` (repoint `/secretariat/caisse`)

**Interfaces:**
- Consumes: `useCaisseStore()` (Task 4), `CaisseInvoiceModal.vue` (Task 8), `CaisseInstallmentModal.vue` (Task 9), `CaisseCancelModal.vue` (Task 5), `CaisseGateway` (Task 4, for the PDF download).
- Produces: closes registre `L3b` — `/secretariat/caisse` becomes the operational cash-desk screen.

- [ ] **Step 1: Create `CaisseList.vue`**

```vue
<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('caisse.title') }}</h1>
        <p class="text-sm text-gray-500">{{ caisseStore.pagination.total }} transactions</p>
      </div>
      <button @click="showInvoiceModal = true"
              class="flex items-center px-6 py-2.5 bg-green-600 text-white rounded-xl hover:bg-green-700 shadow-md shadow-green-200 transition font-semibold">
        <PlusCircleIcon class="h-5 w-5 mr-2" />
        {{ t('caisse.new_invoice') }}
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center">
        <div class="p-3 bg-green-50 rounded-full mr-4"><ArrowTrendingUpIcon class="h-8 w-8 text-green-600" /></div>
        <div>
          <p class="text-sm text-gray-500 font-medium uppercase">{{ t('finance.income') }}</p>
          <p class="text-2xl font-bold text-gray-900">{{ kpiAffiche(formatCurrency(caisseStore.kpi.total_paid)) }}</p>
        </div>
      </div>
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center">
        <div class="p-3 bg-amber-50 rounded-full mr-4"><ClockIcon class="h-8 w-8 text-amber-600" /></div>
        <div>
          <p class="text-sm text-gray-500 font-medium uppercase">{{ t('caisse.table.due') }}</p>
          <p class="text-2xl font-bold text-gray-900">{{ kpiAffiche(formatCurrency(caisseStore.kpi.remaining_due)) }}</p>
        </div>
      </div>
      <div class="bg-gradient-to-r from-gray-800 to-gray-900 p-6 rounded-2xl shadow-lg text-white flex items-center justify-between">
        <div>
          <p class="text-sm text-gray-400 font-medium uppercase">Transactions</p>
          <p class="text-3xl font-bold text-white">{{ kpiAffiche(caisseStore.kpi.total_transactions) }}</p>
        </div>
        <BanknotesIcon class="h-10 w-10 text-gray-500 opacity-50" />
      </div>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-wrap gap-4 items-end">
      <div class="flex-1 min-w-[200px]">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Recherche</label>
        <input v-model="searchQuery" type="text" :placeholder="t('caisse.search_placeholder')"
               class="block w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-green-500 focus:border-green-500 sm:text-sm" />
      </div>
      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Du</label>
        <input v-model="startDate" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm" />
      </div>
      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Au</label>
        <input v-model="endDate" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm" />
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div v-if="caisseStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></span>
      </div>
      <div v-else-if="caisseStore.loadError" class="p-10 text-center text-red-500">Erreur de chargement</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('caisse.table.date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('caisse.table.patient') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('caisse.table.type') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('caisse.table.total') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('caisse.table.paid') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('caisse.table.due') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('caisse.table.status') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('caisse.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="tx in caisseStore.transactions" :key="tx.transaction_id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ formatDate(tx.paid_at) }}</td>
              <td class="px-6 py-4 text-sm text-gray-900">{{ tx.patient_name || '—' }}</td>
              <td class="px-6 py-4">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">
                  {{ tx.transaction_type }}
                </span>
              </td>
              <td class="px-6 py-4 text-right font-bold text-sm">{{ formatCurrency(tx.amount) }}</td>
              <td class="px-6 py-4 text-right text-sm text-green-700">{{ formatCurrency(tx.amount_paid) }}</td>
              <td class="px-6 py-4 text-right text-sm" :class="Number(tx.amount_due) > 0 ? 'text-red-600 font-semibold' : 'text-gray-400'">
                {{ formatCurrency(tx.amount_due) }}
              </td>
              <td class="px-6 py-4">
                <span v-if="tx.status === 'active'" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                  {{ t('caisse.status.active') }}
                </span>
                <span v-else class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-600">
                  {{ t('caisse.status.cancelled') }}
                </span>
              </td>
              <td class="px-6 py-4">
                <div class="flex items-center justify-end gap-1.5">
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
                  <button @click="downloadInvoice(tx)"
                          class="p-2 bg-white border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-100 transition shadow-sm"
                          :title="t('caisse.actions.download')">
                    <ArrowDownTrayIcon class="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="caisseStore.transactions.length === 0">
              <td colspan="8" class="px-6 py-8 text-center text-gray-500 italic">Aucune transaction trouvée.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="caisseStore.pagination.total_pages > 1" class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
        <p class="text-sm text-gray-700">Page {{ caisseStore.pagination.page }} sur {{ caisseStore.pagination.total_pages }}</p>
        <div class="flex space-x-2">
          <button @click="goToPage(caisseStore.pagination.page - 1)" :disabled="caisseStore.pagination.page === 1" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronLeftIcon class="h-5 w-5" />
          </button>
          <button @click="goToPage(caisseStore.pagination.page + 1)" :disabled="caisseStore.pagination.page === caisseStore.pagination.total_pages" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronRightIcon class="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>

    <div v-if="actionError" class="bg-red-50 border-l-4 border-red-500 p-4 rounded-xl">
      <p class="text-sm text-red-700">{{ actionError }}</p>
    </div>

    <CaisseInvoiceModal v-if="showInvoiceModal" :isSaving="isSavingInvoice" :errorMessage="invoiceError"
                         @close="showInvoiceModal = false" @save="handleCreateInvoice" />

    <CaisseInstallmentModal v-if="installmentTx" :remainingDue="Number(installmentTx.amount_due)"
                             :isSaving="isSavingInstallment" :errorMessage="installmentError"
                             @close="installmentTx = null" @confirm="handleAddPayment" />

    <CaisseCancelModal v-if="cancellingTx" :isSaving="isCancelling" :errorMessage="cancelError"
                        :label="`Facture ${cancellingTx.transaction_id} — ${formatCurrency(cancellingTx.amount)}`"
                        @close="cancellingTx = null" @confirm="handleCancel" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useCaisseStore } from '@/stores/caisseStore';
import { CaisseGateway } from '@/services/CaisseGateway';
import api from '@/services/api';
import CaisseInvoiceModal from '@/components/caisse/CaisseInvoiceModal.vue';
import CaisseInstallmentModal from '@/components/caisse/CaisseInstallmentModal.vue';
import CaisseCancelModal from '@/components/caisse/CaisseCancelModal.vue';
import {
  PlusCircleIcon, ArrowTrendingUpIcon, ClockIcon, BanknotesIcon,
  ChevronLeftIcon, ChevronRightIcon, CurrencyDollarIcon, CheckBadgeIcon,
  XCircleIcon, ArrowDownTrayIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const caisseStore = useCaisseStore();

onMounted(() => {
  caisseStore.fetchTransactions();
});

const searchQuery = computed({
  get: () => caisseStore.filters.searchQuery,
  set: (val) => caisseStore.setFilters({ searchQuery: val }),
});
const startDate = computed({
  get: () => caisseStore.filters.startDate,
  set: (val) => caisseStore.setFilters({ startDate: val }),
});
const endDate = computed({
  get: () => caisseStore.filters.endDate,
  set: (val) => caisseStore.setFilters({ endDate: val }),
});

const goToPage = (page) => caisseStore.setPage(page);

const formatCurrency = (value) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value || 0).replace('XOF', 'FCFA');
const formatDate = (iso) => (iso ? String(iso).split('T')[0] : '');
const kpiAffiche = (value) => (caisseStore.kpiError ? 'Indisponible' : value);

const actionError = ref('');
const mapErrorToMessage = (err) => {
  if (err.response) {
    const status = err.response.status;
    const detail = err.response.data?.detail;
    if (status === 422) return "Données invalides.";
    if (status === 400) return detail || "Requête invalide.";
    return `Erreur serveur (${status}) : ${detail || 'veuillez réessayer'}`;
  }
  if (err.request) return "Erreur réseau. Veuillez vérifier votre connexion.";
  return err.message || "Une erreur inattendue est survenue.";
};

// --- Creation facture ---
const showInvoiceModal = ref(false);
const isSavingInvoice = ref(false);
const invoiceError = ref('');

const handleCreateInvoice = async (payload) => {
  isSavingInvoice.value = true;
  invoiceError.value = '';
  try {
    await caisseStore.createInvoice(payload);
    showInvoiceModal.value = false;
  } catch (err) {
    invoiceError.value = mapErrorToMessage(err);
  } finally {
    isSavingInvoice.value = false;
  }
};

// --- Versement ---
const installmentTx = ref(null);
const isSavingInstallment = ref(false);
const installmentError = ref('');

const openInstallmentModal = (tx) => {
  installmentTx.value = tx;
  installmentError.value = '';
};

const handleAddPayment = async (data) => {
  isSavingInstallment.value = true;
  installmentError.value = '';
  try {
    await caisseStore.addPayment(installmentTx.value.transaction_id, data);
    installmentTx.value = null;
  } catch (err) {
    installmentError.value = mapErrorToMessage(err);
  } finally {
    isSavingInstallment.value = false;
  }
};

// --- Solde ---
const handleSettle = async (tx) => {
  actionError.value = '';
  try {
    await caisseStore.settleTransaction(tx.transaction_id);
  } catch (err) {
    actionError.value = mapErrorToMessage(err);
  }
};

// --- Annulation ---
const cancellingTx = ref(null);
const isCancelling = ref(false);
const cancelError = ref('');

const openCancelModal = (tx) => {
  cancellingTx.value = tx;
  cancelError.value = '';
};

const handleCancel = async (justification) => {
  isCancelling.value = true;
  cancelError.value = '';
  try {
    await caisseStore.cancelTransaction(cancellingTx.value.transaction_id, justification);
    cancellingTx.value = null;
  } catch (err) {
    cancelError.value = mapErrorToMessage(err);
  } finally {
    isCancelling.value = false;
  }
};

// --- Téléchargement facture ---
const downloadInvoice = async (tx) => {
  actionError.value = '';
  try {
    const resp = await api.get(`/caisse/${tx.transaction_id}/invoice/download`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([resp.data], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `facture_${tx.transaction_id}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    actionError.value = "Impossible de télécharger la facture.";
  }
};
</script>
```

`CaisseGateway` is imported but its only remaining direct use in this file is none beyond what `caisseStore` already wraps — remove the unused `CaisseGateway` import from the script block above before committing (the download uses `api` directly, per the gateway's own documented note in Task 4 Step 1).

- [ ] **Step 2: Repoint the `/secretariat/caisse` route**

In `ah2-admin-web/src/router/index.js`, change the `caisse` child route's component (currently lines 320-328):

```javascript
      {
        path: 'caisse',
        name: 'secretariat-caisse',
        component: () => import('@/views/modules/finance/FinancialList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
```

to:

```javascript
      {
        path: 'caisse',
        name: 'secretariat-caisse',
        component: () => import('@/views/modules/finance/CaisseList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
```

- [ ] **Step 3: Verify the build succeeds**

Run: `cd ah2-admin-web && npm run build`
Expected: build succeeds, no unused-import warnings treated as errors (if the build fails specifically on the unused `CaisseGateway` import, remove it — see the note at the end of Step 1).

- [ ] **Step 4: Commit**

```bash
git add ah2-admin-web/src/views/modules/finance/CaisseList.vue ah2-admin-web/src/router/index.js
git commit -m "feat: add operational Caisse screen, repoint /secretariat/caisse (closes L3b)"
```

---

## Manual QA checklist (not executable in this environment — no browser tool)

Record in the ledger as unexecuted, same as chantiers 6/7a/7c:

1. Login as `secretaire` → `/secretariat/caisse` shows the new operational list (not the old single-amount modal).
2. "Nouvelle facture" → search an existing patient, add one Pharmacie line (verify stock number shown), add one Service libre line, set an advance below the total → submit → transaction appears with correct `amount_paid`/`amount_due`.
3. On that transaction: "Ajouter un versement" for the remaining due → `amount_due` reaches 0.
4. Create a second invoice, click "Solder" → `amount_due` immediately reaches 0.
5. Click "Annuler" on an active transaction without typing a justification → button stays disabled; type one → transaction moves to "Annulée", stock restored for any Pharmacie line (verify in `/secretariat/stock`).
6. Click "Télécharger la facture" → a PDF downloads with the correct total/paid/due.
7. `/secretariat/retrait` → "Nouveau retrait" with a justification → appears in the list; "Annuler" requires a justification too.
8. `/dashboard/finance` (admin) still shows the old unified read-only journal with the old single-amount modal, unchanged.

## Self-review

- **Spec coverage:** §3 (F1-F6) → Tasks 1, 3. §4 (cancellation justification) → Tasks 2, 3. §5 (Caisse screen + invoice creation) → Tasks 4, 5, 8, 9, 10. §6 (Retrait screen) → Tasks 4, 5, 6, 7. §7 (file list) → matches every Create/Modify line above. §8 (roles) → no route/dependency touched. §9 (error cases) → handled inline by each modal's validation plus `mapErrorToMessage` passthrough of backend 400s.
- **Placeholder scan:** no TBD/TODO; every step has complete, real code including full Vue SFCs.
- **Type consistency:** `caisseStore.createInvoice/addPayment/settleTransaction/cancelTransaction` signatures (Task 4) match exactly what `CaisseList.vue` (Task 10) calls. `CaisseInvoiceModal`'s `save` payload (Task 8) matches `CaisseController.create_transaction`'s real contract (verified against `repositories/caisse_repo.py::create_transaction` during spec research). `CaisseCancelModal`'s `confirm(justification)` (Task 5) matches both call sites in Tasks 7 and 10.
