# tests/test_caisse_price_lock.py
"""Prix unitaire verrouille au catalogue pour la secretaire (2026-10-24).

Tout passe par HTTP (get_caisse_controller / get_discount_controller reels),
pour couvrir le cablage du notification_repo dans la fabrique."""
import sys
import os
import uuid as uuidlib
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from api_backend.backend_app.routes.discount import discount_endpoints
from models.pharmacy import Pharmacy
from models.lab import Examen
from models.consultation_spirituelle import ConsultationSpirituel
from models.notification import Notification
from models.audit import AuditUserAction
from models.caisse import Caisse
from tests.conftest import create_test_user, create_test_patient, auth_headers

PWD = "Correct123!"
UNDEFINED = "Prix non défini, contactez l'administrateur."


@pytest.fixture
def catalog(db_session):
    sec = create_test_user(db_session, "pl_sec", "secretaire", password=PWD)
    med = Pharmacy(drug_name="PL Paracetamol", quantity=50, threshold=1, medication_type="comprime",
                   price=250)
    med0 = Pharmacy(drug_name="PL Sans prix", quantity=50, threshold=1, medication_type="comprime",
                    price=0)
    ex = Examen(code=f"PL-{uuidlib.uuid4().hex[:8]}", nom="PL Glycemie", categorie="Bio", prix=1500)
    ex_null = Examen(code=f"PLN-{uuidlib.uuid4().hex[:8]}", nom="PL Sans prix", categorie="Bio", prix=None)
    db_session.add_all([med, med0, ex, ex_null])
    db_session.flush()
    patient_id, _ = create_test_patient(db_session, sec, first_name="Prixlock")
    db_session.flush()
    fr = ConsultationSpirituel(patient_id=patient_id, created_by=sec.user_id, created_by_name=sec.username,
                               type_consultation="FamilyRestoration", fr_registered_at=datetime(2026, 10, 1),
                               fr_appointment_at=datetime(2026, 10, 2), fr_amount_paid=5000)
    sp = ConsultationSpirituel(patient_id=patient_id, created_by=sec.user_id, created_by_name=sec.username,
                               type_consultation="Spiritual")
    db_session.add_all([fr, sp])
    db_session.flush()
    return {"sec": sec, "med": med, "med0": med0, "ex": ex, "ex_null": ex_null, "fr": fr, "sp": sp,
            "patient_id": patient_id}


def _line(item_type, ref, price, qty=1):
    return {"item_type": item_type, "item_ref_id": ref, "unit_price": price, "quantity": qty,
            "line_total": price * qty}


def _invoice(lines, **extra):
    total = sum(l["line_total"] for l in lines)
    return {"payment_method": "Especes", "transaction_type": "Vente", "amount": total,
            "advance_amount": total, "items": lines, **extra}


def _client(api_client, catalog, username="pl_sec"):
    client = api_client(auth_endpoints, caisse_endpoints, discount_endpoints)
    return client, auth_headers(client, username, PWD)


def _mismatch_notifs(db_session, tx_id):
    return [n for n in db_session.query(Notification).filter(Notification.type == "price_mismatch").all()
            if (n.payload or {}).get("transaction_id") == tx_id]


# ---------- secretaire en ligne ----------

@pytest.mark.parametrize("kind", ["med", "ex", "fr"])
def test_secretaire_prix_catalogue_exact_accepte(db_session, api_client, catalog, kind):
    client, h = _client(api_client, catalog)
    line = {
        "med": _line("Médicament", catalog["med"].medication_id, 250.0, qty=2),
        "ex": _line("Examen", catalog["ex"].id, 1500.0),
        "fr": _line("Consultation", catalog["fr"].consultation_id, 5000.0),
    }[kind]
    r = client.post("/caisse/", json=_invoice([line]), headers=h)
    assert r.status_code == 201, r.text


@pytest.mark.parametrize("kind", ["med", "ex", "fr"])
def test_secretaire_prix_different_refuse_422(db_session, api_client, catalog, kind):
    client, h = _client(api_client, catalog)
    line = {
        "med": _line("Médicament", catalog["med"].medication_id, 200.0),
        "ex": _line("Examen", catalog["ex"].id, 1000.0),
        "fr": _line("Consultation", catalog["fr"].consultation_id, 4000.0),
    }[kind]
    r = client.post("/caisse/", json=_invoice([line]), headers=h)
    assert r.status_code == 422, r.text
    assert "demande de réduction" in r.json()["detail"]


def test_secretaire_line_total_incoherent_refuse_422(db_session, api_client, catalog):
    client, h = _client(api_client, catalog)
    line = _line("Médicament", catalog["med"].medication_id, 250.0, qty=2)
    line["line_total"] = 100.0
    r = client.post("/caisse/", json=_invoice([line]), headers=h)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("kind", ["med0", "ex_null"])
def test_secretaire_prix_catalogue_non_defini_refuse_422(db_session, api_client, catalog, kind):
    client, h = _client(api_client, catalog)
    line = (_line("Médicament", catalog["med0"].medication_id, 100.0) if kind == "med0"
            else _line("Examen", catalog["ex_null"].id, 100.0))
    r = client.post("/caisse/", json=_invoice([line]), headers=h)
    assert r.status_code == 422, r.text
    assert r.json()["detail"] == UNDEFINED


def test_secretaire_types_libres_tout_prix(db_session, api_client, catalog):
    client, h = _client(api_client, catalog)
    lines = [_line("Service", 0, 1234.0), _line("Consultation", catalog["sp"].consultation_id, 777.0)]
    r = client.post("/caisse/", json=_invoice(lines), headers=h)
    assert r.status_code == 201, r.text


def test_admin_prix_libre_partout(db_session, api_client, catalog):
    create_test_user(db_session, "pl_admin", "admin", password=PWD)
    client, h = _client(api_client, catalog, "pl_admin")
    lines = [_line("Médicament", catalog["med"].medication_id, 1.0),
             _line("Médicament", catalog["med0"].medication_id, 10.0),
             _line("Examen", catalog["ex"].id, 99.0),
             _line("Consultation", catalog["fr"].consultation_id, 1.0)]
    r = client.post("/caisse/", json=_invoice(lines), headers=h)
    assert r.status_code == 201, r.text


def test_promoteur_na_pas_acces_a_la_caisse(db_session, api_client, catalog):
    """Le promoteur n'atteint pas POST /caisse (routeur secretaire+admin) :
    l'exemption est dans la regle, la route reste fermee."""
    create_test_user(db_session, "pl_promo", "promoteur", password=PWD)
    client, h = _client(api_client, catalog, "pl_promo")
    r = client.post("/caisse/", json=_invoice([_line("Service", 0, 10.0)]), headers=h)
    assert r.status_code == 403


def test_secretaire_put_items_meme_verrou(db_session, api_client, catalog):
    client, h = _client(api_client, catalog)
    r = client.post("/caisse/", json=_invoice([_line("Service", 0, 100.0)], advance_amount=0), headers=h)
    assert r.status_code == 201, r.text
    tx_id = r.json()["transaction_id"]
    bad = [_line("Examen", catalog["ex"].id, 10.0)]
    r = client.put(f"/caisse/{tx_id}", json={"items": bad, "amount": 10.0}, headers=h)
    assert r.status_code == 422, r.text


# ---------- rejeu hors ligne ----------

def test_rejeu_ecart_accepte_trace_et_notifie(db_session, api_client, catalog):
    admin = create_test_user(db_session, "pl_admin2", "admin", password=PWD)
    promo = create_test_user(db_session, "pl_promo2", "promoteur", password=PWD)
    client, h = _client(api_client, catalog)
    op_uuid = str(uuidlib.uuid4())
    line = _line("Médicament", catalog["med"].medication_id, 200.0, qty=2)
    r = client.post("/caisse/", json=_invoice([line], uuid=op_uuid), headers=h)
    assert r.status_code == 201, r.text
    tx_id = r.json()["transaction_id"]

    tx = db_session.get(Caisse, tx_id)
    assert float(tx.items[0].unit_price) == 200.0  # enregistre tel qu'envoye

    audits = db_session.query(AuditUserAction).filter(
        AuditUserAction.action_performed == "PRICE_MISMATCH",
        AuditUserAction.resource_id == tx_id).all()
    assert len(audits) == 1
    assert audits[0].new_values["lines"][0]["catalog_price"] == 250.0

    notifs = _mismatch_notifs(db_session, tx_id)
    recipients = {n.recipient_user_id for n in notifs}
    assert admin.user_id in recipients and promo.user_id in recipients
    assert catalog["sec"].user_id not in recipients
    p = notifs[0].payload
    assert p["item_type"] == "Médicament"
    assert p["sent_price"] == 200.0
    assert p["catalog_price"] == 250.0
    assert p["author_name"] == catalog["sec"].full_name


def test_rejeu_prix_non_defini_accepte_et_notifie(db_session, api_client, catalog):
    create_test_user(db_session, "pl_admin3", "admin", password=PWD)
    client, h = _client(api_client, catalog)
    line = _line("Examen", catalog["ex_null"].id, 300.0)
    r = client.post("/caisse/", json=_invoice([line], uuid=str(uuidlib.uuid4())), headers=h)
    assert r.status_code == 201, r.text
    notifs = _mismatch_notifs(db_session, r.json()["transaction_id"])
    assert notifs and notifs[0].payload["catalog_price"] in (None, 0.0)  # le modele Examen met 0 par defaut


def test_rejeu_prix_exact_aucune_notification(db_session, api_client, catalog):
    create_test_user(db_session, "pl_admin4", "admin", password=PWD)
    client, h = _client(api_client, catalog)
    line = _line("Examen", catalog["ex"].id, 1500.0)
    r = client.post("/caisse/", json=_invoice([line], uuid=str(uuidlib.uuid4())), headers=h)
    assert r.status_code == 201, r.text
    tx_id = r.json()["transaction_id"]
    assert _mismatch_notifs(db_session, tx_id) == []
    assert db_session.query(AuditUserAction).filter(
        AuditUserAction.action_performed == "PRICE_MISMATCH",
        AuditUserAction.resource_id == tx_id).count() == 0


# ---------- demande de reduction (cree aussi une vente) ----------

def test_demande_reduction_meme_verrou(db_session, api_client, catalog):
    manager = create_test_user(db_session, "pl_mgr", "admin", password=PWD)
    client, h = _client(api_client, catalog)
    bad = _invoice([_line("Examen", catalog["ex"].id, 1000.0)], advance_amount=0)
    r = client.post("/discount-requests", json={"invoice_data": bad, "requested_to": manager.user_id}, headers=h)
    assert r.status_code == 422, r.text
    ok = _invoice([_line("Examen", catalog["ex"].id, 1500.0)], advance_amount=0)
    r = client.post("/discount-requests", json={"invoice_data": ok, "requested_to": manager.user_id}, headers=h)
    assert r.status_code == 201, r.text


# ---------- chaine d'edition du prix par l'admin (verification du "bug") ----------

def test_admin_modifie_prix_produit_puis_secretaire_vend_au_nouveau_prix(db_session, api_client, catalog):
    from api_backend.backend_app.routes.pharmacy import pharmacy_endpoints
    create_test_user(db_session, "pl_admin_px", "admin", password=PWD)
    client = api_client(auth_endpoints, caisse_endpoints, pharmacy_endpoints)
    ha = auth_headers(client, "pl_admin_px", PWD)
    med_id = catalog["med"].medication_id
    r = client.put(f"/pharmacy/{med_id}", json={"price": 320.0}, headers=ha)
    assert r.status_code == 200, r.text
    assert r.json()["price"] == 320.0
    db_session.expire_all()
    assert float(db_session.get(Pharmacy, med_id).price) == 320.0
    hs = auth_headers(client, "pl_sec", PWD)
    assert client.post("/caisse/", json=_invoice([_line("Médicament", med_id, 250.0)]), headers=hs).status_code == 422
    assert client.post("/caisse/", json=_invoice([_line("Médicament", med_id, 320.0)]), headers=hs).status_code == 201


def test_admin_modifie_prix_examen_puis_secretaire_vend_au_nouveau_prix(db_session, api_client, catalog):
    from api_backend.backend_app.routes.labo import lab_endpoints
    create_test_user(db_session, "pl_admin_ex", "admin", password=PWD)
    client = api_client(auth_endpoints, caisse_endpoints, lab_endpoints)
    ha = auth_headers(client, "pl_admin_ex", PWD)
    ex_id = catalog["ex"].id
    r = client.put(f"/labo/exams/{ex_id}", json={"prix": 1800}, headers=ha)
    assert r.status_code == 200, r.text
    db_session.expire_all()
    assert float(db_session.get(Examen, ex_id).prix) == 1800.0
    hs = auth_headers(client, "pl_sec", PWD)
    assert client.post("/caisse/", json=_invoice([_line("Examen", ex_id, 1800.0)]), headers=hs).status_code == 201


# ---------- fix round 1 : quantites / prix / totaux pour toutes les lignes ----------

BAD_QTY = [0.5, 0, -1, 10**9, "2"]


def _svc(qty, price=100.0, total=None):
    return {"item_type": "Service", "item_ref_id": 0, "unit_price": price, "quantity": qty,
            "line_total": total if total is not None else (price * qty if isinstance(qty, (int, float)) else price)}


def _admin_client(api_client, db_session, name):
    create_test_user(db_session, name, "admin", password=PWD)
    client = api_client(auth_endpoints, caisse_endpoints, discount_endpoints)
    return client, auth_headers(client, name, PWD)


@pytest.mark.parametrize("qty", BAD_QTY)
@pytest.mark.parametrize("replay", [False, True])
def test_create_quantite_invalide_422_meme_admin_et_rejeu(db_session, api_client, catalog, qty, replay):
    client, h = _admin_client(api_client, db_session, "pl_q_adm")
    extra = {"uuid": str(uuidlib.uuid4())} if replay else {}
    r = client.post("/caisse/", json=_invoice([_svc(qty)], **extra), headers=h)
    assert r.status_code == 422, r.text


def test_create_quantite_negative_ne_rend_pas_de_stock(db_session, api_client, catalog):
    client, h = _admin_client(api_client, db_session, "pl_q_neg")
    med = catalog["med"]
    before = med.quantity
    r = client.post("/caisse/", json=_invoice([_line("Médicament", med.medication_id, 250.0, qty=-2)]), headers=h)
    assert r.status_code == 422, r.text
    db_session.expire_all()
    assert db_session.get(Pharmacy, med.medication_id).quantity == before


def test_create_quantite_flottante_entiere_acceptee(db_session, api_client, catalog):
    client, h = _client(api_client, catalog)
    r = client.post("/caisse/", json=_invoice([_line("Médicament", catalog["med"].medication_id, 250.0, qty=2.0)]),
                    headers=h)
    assert r.status_code == 201, r.text
    tx = db_session.get(Caisse, r.json()["transaction_id"])
    assert tx.items[0].quantity == 2


@pytest.mark.parametrize("line", [
    _svc(1, price=-5.0, total=-5.0),          # prix negatif
    _svc(2, price=100.0, total=150.0),        # total incoherent (ligne libre)
])
def test_create_ligne_libre_incoherente_422(db_session, api_client, catalog, line):
    client, h = _client(api_client, catalog)
    r = client.post("/caisse/", json=_invoice([line]), headers=h)
    assert r.status_code == 422, r.text


def test_create_consultation_spirituelle_total_incoherent_422(db_session, api_client, catalog):
    client, h = _client(api_client, catalog)
    line = {"item_type": "Consultation", "item_ref_id": catalog["sp"].consultation_id, "unit_price": 500.0,
            "quantity": 1, "line_total": 400.0}
    r = client.post("/caisse/", json=_invoice([line]), headers=h)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("qty", BAD_QTY)
def test_put_quantite_invalide_422(db_session, api_client, catalog, qty):
    client, h = _client(api_client, catalog)
    r = client.post("/caisse/", json=_invoice([_svc(1)], advance_amount=0), headers=h)
    assert r.status_code == 201, r.text
    tx_id = r.json()["transaction_id"]
    r = client.put(f"/caisse/{tx_id}", json={"items": [_svc(qty)], "amount": 100.0}, headers=h)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("qty", BAD_QTY)
def test_demande_reduction_quantite_invalide_422(db_session, api_client, catalog, qty):
    manager = create_test_user(db_session, "pl_mgr_q", "admin", password=PWD)
    client, h = _client(api_client, catalog)
    inv = _invoice([_svc(qty)], advance_amount=0)
    r = client.post("/discount-requests", json={"invoice_data": inv, "requested_to": manager.user_id}, headers=h)
    assert r.status_code == 422, r.text


def test_demande_reduction_uuid_nest_pas_un_rejeu(db_session, api_client, catalog):
    manager = create_test_user(db_session, "pl_mgr_u", "admin", password=PWD)
    client, h = _client(api_client, catalog)
    inv = _invoice([_line("Examen", catalog["ex"].id, 1000.0)], advance_amount=0, uuid=str(uuidlib.uuid4()))
    r = client.post("/discount-requests", json={"invoice_data": inv, "requested_to": manager.user_id}, headers=h)
    assert r.status_code == 422, r.text


def test_put_avec_uuid_reste_refuse(db_session, api_client, catalog):
    client, h = _client(api_client, catalog)
    r = client.post("/caisse/", json=_invoice([_svc(1)], advance_amount=0), headers=h)
    tx_id = r.json()["transaction_id"]
    bad = [_line("Examen", catalog["ex"].id, 10.0)]
    r = client.put(f"/caisse/{tx_id}", json={"items": bad, "amount": 10.0, "uuid": str(uuidlib.uuid4())}, headers=h)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("item_type", ["MEDICAMENT", "medicament", "Médicaments"])
def test_variantes_de_type_medicament_verrouillees(db_session, api_client, catalog, item_type):
    client, h = _client(api_client, catalog)
    mid = catalog["med"].medication_id
    assert client.post("/caisse/", json=_invoice([_line(item_type, mid, 1.0)]), headers=h).status_code == 422
    assert client.post("/caisse/", json=_invoice([_line(item_type, mid, 250.0)]), headers=h).status_code == 201


@pytest.mark.parametrize("item_type", ["Examens", "EXAMEN"])
def test_variantes_de_type_examen_verrouillees(db_session, api_client, catalog, item_type):
    client, h = _client(api_client, catalog)
    eid = catalog["ex"].id
    assert client.post("/caisse/", json=_invoice([_line(item_type, eid, 1.0)]), headers=h).status_code == 422
    assert client.post("/caisse/", json=_invoice([_line(item_type, eid, 1500.0)]), headers=h).status_code == 201


@pytest.mark.parametrize("kind", ["Médicament", "Examen"])
def test_reference_inconnue_refusee(db_session, api_client, catalog, kind):
    client, h = _client(api_client, catalog)
    r = client.post("/caisse/", json=_invoice([_line(kind, 999999999, 100.0)]), headers=h)
    assert r.status_code == 422, r.text
    assert "introuvable" in r.json()["detail"]


def test_notification_en_echec_garde_audit_et_vente(db_session, api_client, catalog, monkeypatch):
    from repositories.notification_repo import NotificationRepository

    def boom(self, *a, **k):
        raise RuntimeError("notification en panne")
    monkeypatch.setattr(NotificationRepository, "create", boom)
    create_test_user(db_session, "pl_admin_nf", "admin", password=PWD)
    client, h = _client(api_client, catalog)
    line = _line("Médicament", catalog["med"].medication_id, 200.0)
    r = client.post("/caisse/", json=_invoice([line], uuid=str(uuidlib.uuid4())), headers=h)
    assert r.status_code == 201, r.text
    tx_id = r.json()["transaction_id"]
    db_session.expire_all()
    assert db_session.get(Caisse, tx_id) is not None
    assert db_session.query(AuditUserAction).filter(
        AuditUserAction.action_performed == "PRICE_MISMATCH",
        AuditUserAction.resource_id == tx_id).count() == 1
    assert _mismatch_notifs(db_session, tx_id) == []
