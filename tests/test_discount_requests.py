# tests/test_discount_requests.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import date
from unittest.mock import MagicMock

from controller.caisse_controller import CaisseController
from controller.discount_request_controller import DiscountRequestController
from repositories.discount_request_repo import DiscountRequestRepository
from repositories.notification_repo import NotificationRepository
from repositories.caisse_repo import CaisseRepository
from repositories.audit_repo import AuditRepository
from tests.conftest import create_test_user

TEST_PASSWORD = "TestPass123!"


@pytest.fixture
def secretaire_user(db_session):
    user = create_test_user(db_session, "dr7_sec1", "secretaire", password=TEST_PASSWORD)
    user.PLAIN_PASSWORD = TEST_PASSWORD
    return user


@pytest.fixture
def manager_user(db_session):
    user = create_test_user(db_session, "dr7_mgr1", "admin", password=TEST_PASSWORD)
    user.PLAIN_PASSWORD = TEST_PASSWORD
    return user


@pytest.fixture
def caisse_repo_factory(db_session):
    def _factory():
        return CaisseRepository(db_session)
    return _factory


def _make_controller_with_pending_tx():
    repo = MagicMock()
    tx = MagicMock()
    tx.status = "pending_approval"
    repo.get_by_id.return_value = tx
    user = MagicMock()
    ctrl = CaisseController(repo=repo, current_user=user)
    return ctrl, repo


def test_update_transaction_blocked_when_pending_approval():
    ctrl, repo = _make_controller_with_pending_tx()

    with pytest.raises(ValueError, match="en attente de validation"):
        ctrl.update_transaction(1, {"note": "test"})

    repo.update_transaction.assert_not_called()


def test_cancel_transaction_blocked_when_pending_approval():
    ctrl, repo = _make_controller_with_pending_tx()

    with pytest.raises(ValueError, match="en attente de validation"):
        ctrl.cancel_transaction(1, "test annulation")

    repo.cancel_transaction.assert_not_called()


def test_add_installment_payment_blocked_when_pending_approval():
    ctrl, repo = _make_controller_with_pending_tx()

    with pytest.raises(ValueError, match="en attente de validation"):
        ctrl.add_installment_payment(1, {"paid_amount": 100, "payment_method": "Espèces", "payment_type": "VERSEMENT_ECHEANCE"})

    repo.add_payment_installment.assert_not_called()


def test_delete_transaction_blocked_when_pending_approval():
    ctrl, repo = _make_controller_with_pending_tx()

    with pytest.raises(ValueError, match="en attente de validation"):
        ctrl.delete_transaction(1)

    repo.delete_transaction.assert_not_called()


def test_settle_transaction_blocked_when_pending_approval():
    ctrl, repo = _make_controller_with_pending_tx()

    with pytest.raises(ValueError, match="en attente de validation"):
        ctrl.settle_transaction(1)

    repo.settle_transaction.assert_not_called()


def test_generate_invoice_pdf_blocked_when_pending_approval():
    ctrl, repo = _make_controller_with_pending_tx()

    with pytest.raises(ValueError, match="en attente de validation"):
        ctrl.generate_invoice_pdf(1)

    repo.generate_invoice_pdf_content.assert_not_called()


def test_create_request_locks_transaction(db_session):
    secretaire_user = create_test_user(db_session, "dr6_sec1", "secretaire")
    manager_user = create_test_user(db_session, "dr6_mgr1", "admin")
    caisse_repo = CaisseRepository(db_session)
    ctrl = DiscountRequestController(
        repo=DiscountRequestRepository(db_session),
        caisse_repo=caisse_repo,
        notification_repo=NotificationRepository(db_session),
        current_user=secretaire_user,
    )
    invoice_data = {
        "payment_method": "Espèces", "transaction_type": "Consultation",
        "amount": 5000, "advance_amount": 0,
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 5000, "quantity": 1, "line_total": 5000}],
    }
    req = ctrl.create_request(invoice_data, requested_to=manager_user.user_id)
    tx = caisse_repo.get_by_id(req.transaction_id)
    assert tx.status == "pending_approval"
    assert req.status == "pending"
    assert req.original_amount == 5000


def test_cancel_and_reassign_keeps_history(db_session):
    secretaire_user = create_test_user(db_session, "dr6_sec2", "secretaire")
    manager_user = create_test_user(db_session, "dr6_mgr2", "admin")
    manager2_user = create_test_user(db_session, "dr6_mgr3", "promoteur")
    ctrl = DiscountRequestController(
        repo=DiscountRequestRepository(db_session),
        caisse_repo=CaisseRepository(db_session),
        notification_repo=NotificationRepository(db_session),
        current_user=secretaire_user,
    )
    invoice_data = {
        "payment_method": "Espèces", "transaction_type": "Consultation",
        "amount": 3000, "advance_amount": 0,
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 3000, "quantity": 1, "line_total": 3000}],
    }
    first = ctrl.create_request(invoice_data, requested_to=manager_user.user_id)
    second = ctrl.cancel_and_reassign(first.id, manager2_user.user_id)

    db_session.refresh(first)
    assert first.status == "cancelled"
    assert second.status == "pending"
    assert second.requested_to == manager2_user.user_id
    assert second.transaction_id == first.transaction_id


def _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory, notification_repo=None):
    ctrl = DiscountRequestController(
        repo=DiscountRequestRepository(db_session),
        caisse_repo=caisse_repo_factory(),
        notification_repo=notification_repo or NotificationRepository(db_session),
        current_user=secretaire_user,
        audit_repo=AuditRepository(db_session),
    )
    invoice_data = {
        "payment_method": "Espèces", "transaction_type": "Consultation",
        "amount": 10000, "advance_amount": 0,
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 10000, "quantity": 1, "line_total": 10000}],
    }
    return ctrl.create_request(invoice_data, requested_to=manager_user.user_id), ctrl


def test_decide_wrong_password_rejected(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    with pytest.raises(PermissionError, match="Mot de passe incorrect"):
        ctrl.decide_request(req.id, password="mauvais_mdp", refuse=False, decision_percent=20)
    db_session.refresh(req)
    assert req.status == "pending"


def test_decide_approve_percent_updates_amount_and_audit(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False, decision_percent=20)

    db_session.refresh(req)
    assert req.status == "approved"
    assert req.decision_percent == 20

    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    assert tx.status == "active"
    assert float(tx.amount) == 8000.0  # 10000 * (1 - 0.20)


def test_decide_echelonne_only_does_not_change_amount(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False,
                         decision_echelonne_deadline=date(2026, 12, 31))

    db_session.refresh(req)
    assert req.status == "approved"
    assert req.decision_echelonne_deadline == date(2026, 12, 31)
    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    assert float(tx.amount) == 10000.0  # inchangé, pas de pourcentage


def test_decide_refuse_rejects_combined_percent(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    with pytest.raises(ValueError, match="refus ne peut pas"):
        ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=True, decision_percent=10)


def test_decide_refuse_success(db_session, secretaire_user, manager_user, caisse_repo_factory):
    """Cas manquant du spec original (registre residus, chantier notifications) :
    seul le refus INVALIDE (combine a un pourcentage) etait teste, jamais un
    refus simple reussi."""
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=True)

    db_session.refresh(req)
    assert req.status == "refused"
    assert req.decision_percent is None
    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    assert tx.status == "active"
    assert float(tx.amount) == 10000.0  # refus -> montant original, jamais reduit


def test_decide_approve_logs_audit_entry(db_session, secretaire_user, manager_user, caisse_repo_factory):
    """Cas manquant du spec original : aucun test ne verifiait que la
    decision est reellement journalisee dans audit_user_actions (le point
    central de la garantie anti-fraude - une decision non tracee ne vaut
    pas mieux que le papier remplace)."""
    from models.audit import AuditUserAction
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False, decision_percent=50)

    entry = (
        db_session.query(AuditUserAction)
        .filter(AuditUserAction.resource_type == "DiscountRequest", AuditUserAction.resource_id == req.id)
        .first()
    )
    assert entry is not None
    assert entry.action_performed == "APPROVE"
    assert entry.new_values["decision_percent"] == 50


def test_decide_refuse_logs_audit_entry(db_session, secretaire_user, manager_user, caisse_repo_factory):
    from models.audit import AuditUserAction
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=True)

    entry = (
        db_session.query(AuditUserAction)
        .filter(AuditUserAction.resource_type == "DiscountRequest", AuditUserAction.resource_id == req.id)
        .first()
    )
    assert entry is not None
    assert entry.action_performed == "REFUSE"


def test_notifications_sent_in_both_directions(db_session, secretaire_user, manager_user, caisse_repo_factory):
    """Cas manquant du spec original : jamais verifie que la notification
    part bien secretaire->manager a la creation ET manager->secretaire a la
    decision (les deux sens, pas un seul)."""
    from repositories.notification_repo import NotificationRepository
    notif_repo = NotificationRepository(db_session)
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory, notification_repo=notif_repo)

    manager_unread = notif_repo.list_unread(manager_user.user_id)
    assert len(manager_unread) == 1
    assert manager_unread[0].type == "discount_request"

    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False, decision_percent=10)

    secretaire_unread = notif_repo.list_unread(secretaire_user.user_id)
    assert len(secretaire_unread) == 1
    assert secretaire_unread[0].type == "discount_decided"
    assert secretaire_unread[0].payload["decision_percent"] == 10


def test_decide_approve_with_nothing_granted_rejected(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    with pytest.raises(ValueError, match="pourcentage et/ou une échéance"):
        ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False)
    db_session.refresh(req)
    assert req.status == "pending"


def test_decide_invalid_percent_rejected(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    with pytest.raises(ValueError, match="10, 20, 50 ou 100"):
        ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False, decision_percent=150)
    with pytest.raises(ValueError, match="10, 20, 50 ou 100"):
        ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False, decision_percent=-10)
    db_session.refresh(req)
    assert req.status == "pending"


def _secretaire_controller(db_session, secretaire_user, caisse_repo_factory):
    return DiscountRequestController(
        repo=DiscountRequestRepository(db_session), caisse_repo=caisse_repo_factory(),
        notification_repo=NotificationRepository(db_session), current_user=secretaire_user,
    )


def _invoice(advance_amount=0):
    return {
        "payment_method": "Espèces", "transaction_type": "Consultation",
        "amount": 5000, "advance_amount": advance_amount,
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 5000, "quantity": 1, "line_total": 5000}],
    }


def test_create_request_rejects_advance_amount(db_session, secretaire_user, manager_user, caisse_repo_factory):
    ctrl = _secretaire_controller(db_session, secretaire_user, caisse_repo_factory)
    ctrl.caisse_repo = MagicMock(wraps=ctrl.caisse_repo)
    with pytest.raises(ValueError, match="Aucune avance"):
        ctrl.create_request(_invoice(advance_amount=1000), requested_to=manager_user.user_id)
    ctrl.caisse_repo.create_transaction.assert_not_called()


def test_create_request_rejects_invalid_recipient(db_session, secretaire_user, caisse_repo_factory):
    ctrl = _secretaire_controller(db_session, secretaire_user, caisse_repo_factory)
    ctrl.caisse_repo = MagicMock(wraps=ctrl.caisse_repo)
    with pytest.raises(ValueError, match="destinataire"):
        ctrl.create_request(_invoice(), requested_to=999999)
    ctrl.caisse_repo.create_transaction.assert_not_called()


def test_create_request_rejects_non_manager_or_inactive_recipient(db_session, secretaire_user, caisse_repo_factory):
    other_secretaire = create_test_user(db_session, "dr9_sec_other", "secretaire")
    inactive_admin = create_test_user(db_session, "dr9_mgr_inactive", "admin", is_active=False)
    ctrl = _secretaire_controller(db_session, secretaire_user, caisse_repo_factory)
    ctrl.caisse_repo = MagicMock(wraps=ctrl.caisse_repo)
    for bad_id in (other_secretaire.user_id, inactive_admin.user_id):
        with pytest.raises(ValueError, match="destinataire"):
            ctrl.create_request(_invoice(), requested_to=bad_id)
    ctrl.caisse_repo.create_transaction.assert_not_called()


def test_cancel_and_reassign_rejects_invalid_recipient(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    with pytest.raises(ValueError, match="destinataire"):
        ctrl.cancel_and_reassign(req.id, 999999)
    db_session.refresh(req)
    assert req.status == "pending"  # l'ancienne demande n'a pas ete annulee


# Task 8: Endpoint integration tests
from api_backend.backend_app.routes.discount import discount_endpoints
from api_backend.backend_app.routes.auth import auth_endpoints
from conftest import auth_headers


def test_create_request_endpoint_forbidden_for_admin(api_client, db_session):
    client = api_client(auth_endpoints, discount_endpoints)
    create_test_user(db_session, "dr8_admin1", "admin", password=TEST_PASSWORD)
    headers = auth_headers(client, "dr8_admin1", TEST_PASSWORD)

    r = client.post("/discount-requests", json={"invoice_data": {}, "requested_to": 1}, headers=headers)
    assert r.status_code == 403


def test_list_pending_endpoint_forbidden_for_secretaire(api_client, db_session):
    client = api_client(auth_endpoints, discount_endpoints)
    create_test_user(db_session, "dr8_sec1", "secretaire", password=TEST_PASSWORD)
    headers = auth_headers(client, "dr8_sec1", TEST_PASSWORD)

    r = client.get("/discount-requests/pending", headers=headers)
    assert r.status_code == 403


def test_decide_endpoint_real_http_success(api_client, db_session):
    """Cas manquant du spec original : la decision n'avait jamais ete
    exercee via une vraie requete HTTP de bout en bout (client -> endpoint
    -> controller -> DB), seulement au niveau controller."""
    client = api_client(auth_endpoints, discount_endpoints)
    secretaire = create_test_user(db_session, "dr10_sec_http", "secretaire", password=TEST_PASSWORD)
    manager = create_test_user(db_session, "dr10_mgr_http", "admin", password=TEST_PASSWORD)
    sec_headers = auth_headers(client, "dr10_sec_http", TEST_PASSWORD)
    mgr_headers = auth_headers(client, "dr10_mgr_http", TEST_PASSWORD)

    invoice_data = {
        "payment_method": "Espèces", "transaction_type": "Consultation",
        "amount": 4000, "advance_amount": 0,
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 4000, "quantity": 1, "line_total": 4000}],
    }
    r = client.post("/discount-requests", json={"invoice_data": invoice_data, "requested_to": manager.user_id}, headers=sec_headers)
    assert r.status_code == 201
    request_id = r.json()["id"]

    r = client.post(
        f"/discount-requests/{request_id}/decide",
        json={"password": TEST_PASSWORD, "refuse": False, "decision_percent": 20},
        headers=mgr_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_decide_endpoint_is_rate_limited(api_client, db_session):
    """Anti-bruteforce sur les mots de passe INCORRECTS uniquement (residu
    corrige 2026-09-28 : l'ancien decorateur slowapi comptait aussi les
    decisions reussies, throttlant un manager occupe). Les 5 premiers essais
    au mauvais mot de passe -> 403 ("Mot de passe incorrect"), le 6e -> 403
    aussi mais avec le message de blocage temporaire (pas de 429 : le
    decorateur slowapi lui-meme est desormais tres permissif, 20/minute)."""
    client = api_client(auth_endpoints, discount_endpoints)
    create_test_user(db_session, "dr9_admin_rl", "admin", password=TEST_PASSWORD)
    headers = auth_headers(client, "dr9_admin_rl", TEST_PASSWORD)

    body = {"password": "mauvais_mdp", "refuse": True}
    responses = [client.post("/discount-requests/999999/decide", json=body, headers=headers) for _ in range(6)]
    codes = [r.status_code for r in responses]
    assert codes == [403] * 6
    assert "Mot de passe incorrect" in responses[4].json()["detail"]
    assert "Trop de tentatives" in responses[5].json()["detail"]


# --- Ecran "Historique des demandes de reduction" (brainstorming 2026-09-28) ---
# Decisions actees : secretaire voit UNIQUEMENT ses propres demandes (moindre
# privilege) ; admin/promoteur voient TOUTES les demandes (supervision) ;
# reduced_amount = original_amount * decision_percent/100, 0 si non approuve
# ou si aucun pourcentage n'a ete accorde (echeance seule).

def test_history_scoped_to_own_requests_for_secretaire(db_session, caisse_repo_factory):
    secretaire1 = create_test_user(db_session, "dh1_sec1", "secretaire")
    secretaire2 = create_test_user(db_session, "dh1_sec2", "secretaire")
    manager = create_test_user(db_session, "dh1_mgr", "admin")
    notif_repo = NotificationRepository(db_session)

    _make_pending_request(db_session, secretaire1, manager, caisse_repo_factory, notification_repo=notif_repo)
    _make_pending_request(db_session, secretaire2, manager, caisse_repo_factory, notification_repo=notif_repo)

    repo = DiscountRequestRepository(db_session)
    items, total = repo.list_history(requested_by=secretaire1.user_id)
    assert total == 1
    assert items[0].requested_by == secretaire1.user_id


def test_history_shows_all_requests_for_manager_scope(db_session, caisse_repo_factory):
    secretaire1 = create_test_user(db_session, "dh2_sec1", "secretaire")
    secretaire2 = create_test_user(db_session, "dh2_sec2", "secretaire")
    manager = create_test_user(db_session, "dh2_mgr", "admin")
    notif_repo = NotificationRepository(db_session)

    _make_pending_request(db_session, secretaire1, manager, caisse_repo_factory, notification_repo=notif_repo)
    _make_pending_request(db_session, secretaire2, manager, caisse_repo_factory, notification_repo=notif_repo)

    repo = DiscountRequestRepository(db_session)
    # requested_by=None -> pas de filtre demandeur, vue de supervision (admin/promoteur)
    items, total = repo.list_history(requested_by=None)
    assert total >= 2


def test_history_filters_by_status_and_date_range(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False, decision_percent=50)

    repo = DiscountRequestRepository(db_session)
    items, total = repo.list_history(requested_by=secretaire_user.user_id, status="approved")
    assert total == 1
    assert items[0].id == req.id

    items, total = repo.list_history(requested_by=secretaire_user.user_id, status="refused")
    assert total == 0

    future = date(2099, 1, 1)
    items, total = repo.list_history(requested_by=secretaire_user.user_id, date_from=future)
    assert total == 0


def test_kpi_counts_and_reduced_amount(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req1, ctrl1 = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl1.user = manager_user
    ctrl1.decide_request(req1.id, password=manager_user.PLAIN_PASSWORD, refuse=False, decision_percent=20)  # 10000 * 20% = 2000

    req2, ctrl2 = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl2.user = manager_user
    ctrl2.decide_request(req2.id, password=manager_user.PLAIN_PASSWORD, refuse=True)

    req3, _ = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)  # reste pending

    repo = DiscountRequestRepository(db_session)
    kpi = repo.kpi(requested_by=secretaire_user.user_id)
    assert kpi["approved_count"] == 1
    assert kpi["refused_count"] == 1
    assert kpi["pending_count"] == 1
    assert kpi["total_reduced_amount"] == 2000.0


def test_history_endpoint_scoping_via_real_http(api_client, db_session):
    """Verifie le scope de bout en bout (pas juste au niveau repo) : une
    secretaire ne voit que sa propre demande via /discount-requests/history,
    un admin voit les deux."""
    client = api_client(auth_endpoints, discount_endpoints)
    sec1 = create_test_user(db_session, "dh3_sec1", "secretaire", password=TEST_PASSWORD)
    sec2 = create_test_user(db_session, "dh3_sec2", "secretaire", password=TEST_PASSWORD)
    manager = create_test_user(db_session, "dh3_mgr", "admin", password=TEST_PASSWORD)
    sec1_headers = auth_headers(client, "dh3_sec1", TEST_PASSWORD)
    sec2_headers = auth_headers(client, "dh3_sec2", TEST_PASSWORD)
    mgr_headers = auth_headers(client, "dh3_mgr", TEST_PASSWORD)

    invoice_data = {
        "payment_method": "Espèces", "transaction_type": "Consultation",
        "amount": 2000, "advance_amount": 0,
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 2000, "quantity": 1, "line_total": 2000}],
    }
    r = client.post("/discount-requests", json={"invoice_data": invoice_data, "requested_to": manager.user_id}, headers=sec1_headers)
    assert r.status_code == 201

    r = client.get("/discount-requests/history", headers=sec1_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = client.get("/discount-requests/history", headers=sec2_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 0

    r = client.get("/discount-requests/history", headers=mgr_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    r = client.get("/discount-requests/kpi", headers=sec1_headers)
    assert r.status_code == 200
    assert r.json()["pending_count"] == 1


def test_get_approved_for_transaction_returns_none_when_no_decision(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    repo = DiscountRequestRepository(db_session)
    assert repo.get_approved_for_transaction(req.transaction_id) is None


def test_get_approved_for_transaction_returns_none_when_refused(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=True)

    repo = DiscountRequestRepository(db_session)
    assert repo.get_approved_for_transaction(req.transaction_id) is None


def test_get_approved_for_transaction_returns_decision_with_decider_name(db_session, secretaire_user, manager_user, caisse_repo_factory):
    req, ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    ctrl.user = manager_user
    ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False, decision_percent=20)

    repo = DiscountRequestRepository(db_session)
    approved = repo.get_approved_for_transaction(req.transaction_id)
    assert approved is not None
    assert approved.decision_percent == 20
    assert approved.decider is not None
    assert approved.decider.user_id == manager_user.user_id


# --- Task 5: CaisseController.build_ticket_data ---

def test_build_ticket_data_blocked_when_pending_approval():
    ctrl, repo = _make_controller_with_pending_tx()
    ctrl.discount_repo = MagicMock()
    with pytest.raises(ValueError, match="en attente de validation"):
        ctrl.build_ticket_data(1)


def test_build_ticket_data_includes_discount_block_when_approved(db_session, secretaire_user, manager_user, caisse_repo_factory):
    from controller.caisse_controller import CaisseController
    from repositories.audit_repo import AuditRepository

    req, discount_ctrl = _make_pending_request(db_session, secretaire_user, manager_user, caisse_repo_factory)
    discount_ctrl.user = manager_user
    discount_ctrl.decide_request(req.id, password=manager_user.PLAIN_PASSWORD, refuse=False, decision_percent=20)

    caisse_repo = caisse_repo_factory()
    caisse_ctrl = CaisseController(repo=caisse_repo, current_user=manager_user, discount_repo=DiscountRequestRepository(db_session))
    ticket = caisse_ctrl.build_ticket_data(req.transaction_id)

    assert ticket["discount"] is not None
    assert ticket["discount"]["decision_percent"] == 20
    assert ticket["discount"]["decided_by_name"]


def test_build_ticket_data_no_discount_block_for_plain_transaction(db_session, secretaire_user, caisse_repo_factory):
    """Une transaction active qui n'a JAMAIS eu de demande de reduction
    (le cas normal, immensement majoritaire) ne doit jamais chercher ni
    afficher de bloc reduction."""
    from controller.caisse_controller import CaisseController
    from tests.conftest import create_test_transaction

    caisse_repo = caisse_repo_factory()
    tx = create_test_transaction(db_session, secretaire_user)
    assert tx.status == "active"

    caisse_ctrl = CaisseController(repo=caisse_repo, current_user=secretaire_user, discount_repo=DiscountRequestRepository(db_session))
    ticket = caisse_ctrl.build_ticket_data(tx.transaction_id)
    assert ticket["discount"] is None
