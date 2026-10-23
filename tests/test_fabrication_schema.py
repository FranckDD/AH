# tests/test_fabrication_schema.py
"""Fabrication, tache 1 : role ProductionManager, tables fab_* et leurs CHECK, gardes negatives."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from api_backend.backend_app.routes.admin import users_endpoint
from api_backend.backend_app.routes.appointment import appointment_endpoints
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from api_backend.backend_app.routes.notifications import notification_endpoints
from api_backend.backend_app.security.role_map import PRODUCTIONMANAGER, normalize_role_name
from models import (
    ApplicationRole, FabBatch, FabConsumption, FabIntrant, FabIntrantPurchase, FabSettings,
    Pharmacy,
)
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
MODULES = (auth_endpoints, users_endpoint, appointment_endpoints, lab_endpoints, notification_endpoints)


def test_role_production_manager_exists_and_normalizes(db_session):
    assert db_session.query(ApplicationRole).filter_by(role_name="ProductionManager").count() == 1
    assert PRODUCTIONMANAGER == "productionmanager"
    for alias in ("ProductionManager", "production_manager", "responsable_production"):
        assert normalize_role_name(alias) == "productionmanager"


def _product(db):
    p = Pharmacy(drug_name="t_fab_schema_prod", quantity=0, threshold=0,
                 medication_type="pharmaceutique", forme="Autre")
    db.add(p)
    db.flush()
    return p.medication_id


def _new_purchase(db, user, **kw):
    intrant = FabIntrant(name="intrant_schema_test", unit="u")
    db.add(intrant)
    db.flush()
    vals = dict(intrant_id=intrant.id, purchase_date=date.today(), quantity=Decimal("5"),
                unit_cost=Decimal("1.00"), remaining_qty=Decimal("5"), created_by=user.user_id)
    vals.update(kw)
    return FabIntrantPurchase(**vals)


def test_tables_exist_with_checks(db_session):
    user = create_test_user(db_session, "t_fab_schema", "admin")
    # quantite d'achat a zero
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(_new_purchase(db_session, user, quantity=Decimal("0"),
                                         remaining_qty=Decimal("0")))
            db_session.flush()
    # consommation negative
    purchase = _new_purchase(db_session, user)
    db_session.add(purchase)
    pid = _product(db_session)
    batch = FabBatch(batch_number="FAB-T-0001", product_id=pid, production_date=date.today(),
                     created_by=user.user_id)
    db_session.add(batch)
    db_session.flush()
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(FabConsumption(batch_id=batch.id, purchase_id=purchase.id,
                                           quantity=Decimal("-1")))
            db_session.flush()
    # statut de lot inconnu
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(FabBatch(batch_number="FAB-T-0002", product_id=pid,
                                    production_date=date.today(), created_by=user.user_id,
                                    status="inconnu"))
            db_session.flush()


def test_settings_row_defaults(db_session):
    row = db_session.get(FabSettings, 1)
    assert row is not None
    assert row.tolerance_pct == Decimal("2.00")
    assert row.stale_days == 7


def test_production_manager_denied_where_stockcontroller_is(db_session, api_client):
    create_test_user(db_session, "t_deny_prod", "ProductionManager", password=PWD)
    client = api_client(*MODULES)
    h = auth_headers(client, "t_deny_prod", PWD)
    for path in ("/appointments/", "/users/roles", "/users/specialties", "/users/doctors",
                 "/users/managers", "/labo/exams/1/params"):
        r = client.get(path, headers=h)
        assert r.status_code == 403, (path, r.status_code, r.text)
    # perimetre conserve
    assert client.get("/auth/me", headers=h).status_code == 200
    assert client.get("/notifications", headers=h).status_code == 200
