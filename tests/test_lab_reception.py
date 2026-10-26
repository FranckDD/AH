# tests/test_lab_reception.py
"""
Reception au labo (defaut 6, guides 2026-10-26) : un examen facture a la caisse sans ordonnance est
propose comme element a importer ; un examen d'ordonnance deja recu/execute n'est plus propose ;
la meme ligne (ordonnance ou facture) ne se recoit qu'une fois, cote serveur (409).
"""
import uuid
from datetime import date, datetime

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from models.caisse import Caisse
from models.caisse_item import CaisseItem
from models.lab import Examen, LabResult
from models.prescription import Prescription
from tests.conftest import create_test_user, create_test_patient, create_test_transaction, auth_headers

PWD = "Correct123!"


def _exam(db, nom):
    ex = Examen(code=f"RC-{uuid.uuid4().hex[:8]}", nom=nom, categorie="Bio", prix=1500)
    db.add(ex)
    db.flush()
    return ex


def _lab_and_patient(db, tag):
    lab = create_test_user(db, f"rc_lab_{tag}", "laborantin", password=PWD)
    lab.postgres_role = "app_laborantin"   # contrainte chk_technician_role sur lab_results.technician_id
    db.flush()
    pid, _ = create_test_patient(db, lab, first_name=f"Recep{tag}", last_name=f"Zq{tag}")
    return lab, pid


def _invoice(db, lab, pid, exams, status="active"):
    tx = create_test_transaction(
        db, lab, patient_id=pid, transaction_type="Examen", amount=1500.0 * len(exams),
        items=[{"item_type": "Examen", "item_ref_id": e.id, "unit_price": 1500.0, "quantity": 1, "line_total": 1500.0} for e in exams])
    if status != "active":
        tx.status = status
        db.flush()
    return db.query(CaisseItem).filter_by(transaction_id=tx.transaction_id).order_by(CaisseItem.item_id).all()


def _prescription(db, pid, doctor, exams):
    p = Prescription(patient_id=pid, medication="Examens", dosage="-", frequency="-", duration="-", start_date=date.today(),
                     status="active", is_lab_order=True, lab_exams_list=[e.nom for e in exams],
                     prescribed_by=doctor.user_id, prescribed_by_name=doctor.full_name)
    db.add(p)
    db.flush()
    return p


def _received(db, pid, ex, status="pending", prescription=None, caisse_item=None):
    r = LabResult(patient_id=pid, test_type=ex.nom, status=status, examen_id=ex.id,
                  origin_prescription_id=prescription.prescription_id if prescription else None,
                  origin_caisse_item_id=caisse_item.item_id if caisse_item else None,
                  code_lab_patient=f"LAB-RC-{uuid.uuid4().hex[:8]}", test_date=datetime.now())
    db.add(r)
    db.flush()
    return r


def _client(api_client, username):
    from tests.conftest import auth_headers as ah
    client = api_client(auth_endpoints, lab_endpoints)
    return client, ah(client, username, PWD)


def _search(client, h, tag):
    resp = client.get("/labo/search-internal", headers=h, params={"q": f"Zq{tag}"})
    assert resp.status_code == 200, resp.text
    return resp.json()


# ------------------------------------------------------------------ (a) examens factures

def test_patient_facture_sans_ordonnance_est_propose_avec_ses_lignes_de_facture(db_session, api_client):
    lab, pid = _lab_and_patient(db_session, "a1")
    ex = _exam(db_session, "Acide urique a1")
    item = _invoice(db_session, lab, pid, [ex])[0]
    client, h = _client(api_client, lab.username)

    out = _search(client, h, "a1")
    assert len(out) == 1
    entry = out[0]
    assert entry["id"] == pid and entry["prescription_id"] is None and entry["exams_prescribed"] == []
    assert entry["invoiced_exams"] == [{"item_id": item.item_id, "examen_id": ex.id, "nom": ex.nom, "transaction_id": item.transaction_id}]


def test_ligne_de_facture_deja_recue_n_est_plus_proposee(db_session, api_client):
    lab, pid = _lab_and_patient(db_session, "a2")
    ex1, ex2 = _exam(db_session, "Glyc a2"), _exam(db_session, "Uree a2")
    items = _invoice(db_session, lab, pid, [ex1, ex2])
    _received(db_session, pid, ex1, caisse_item=items[0])
    client, h = _client(api_client, lab.username)

    entry = _search(client, h, "a2")[0]
    assert [i["examen_id"] for i in entry["invoiced_exams"]] == [ex2.id]
    _received(db_session, pid, ex2, status="completed", caisse_item=items[1])
    assert _search(client, h, "a2") == []


def test_facture_annulee_n_est_pas_proposee(db_session, api_client):
    lab, pid = _lab_and_patient(db_session, "a3")
    _invoice(db_session, lab, pid, [_exam(db_session, "Glyc a3")], status="cancelled")
    client, h = _client(api_client, lab.username)
    assert _search(client, h, "a3") == []


def test_un_patient_avec_ordonnance_et_facture_n_apparait_qu_une_fois(db_session, api_client):
    lab, pid = _lab_and_patient(db_session, "a4")
    doc = create_test_user(db_session, "rc_doc_a4", "medecin", password=PWD)
    ex_p, ex_i = _exam(db_session, "NFS a4"), _exam(db_session, "Uree a4")
    _prescription(db_session, pid, doc, [ex_p])
    _invoice(db_session, lab, pid, [ex_i])
    client, h = _client(api_client, lab.username)
    out = _search(client, h, "a4")
    assert len(out) == 1
    assert out[0]["exams_prescribed"] == [ex_p.nom] and [i["examen_id"] for i in out[0]["invoiced_exams"]] == [ex_i.id]


# ------------------------------------------------------------------ (b) ordonnance deja executee

def test_ordonnance_entierement_executee_n_est_plus_proposee(db_session, api_client):
    lab, pid = _lab_and_patient(db_session, "b1")
    doc = create_test_user(db_session, "rc_doc_b1", "medecin", password=PWD)
    e1, e2 = _exam(db_session, "NFS b1"), _exam(db_session, "Glyc b1")
    presc = _prescription(db_session, pid, doc, [e1, e2])
    client, h = _client(api_client, lab.username)
    assert _search(client, h, "b1")[0]["exams_prescribed"] == [e1.nom, e2.nom]

    _received(db_session, pid, e1, status="completed", prescription=presc)
    assert _search(client, h, "b1")[0]["exams_prescribed"] == [e2.nom]   # seule la ligne restante
    _received(db_session, pid, e2, status="completed", prescription=presc)
    assert _search(client, h, "b1") == []


def test_ordonnance_recue_mais_pas_terminee_n_est_pas_re_proposee(db_session, api_client):
    lab, pid = _lab_and_patient(db_session, "b2")
    doc = create_test_user(db_session, "rc_doc_b2", "medecin", password=PWD)
    e1 = _exam(db_session, "NFS b2")
    presc = _prescription(db_session, pid, doc, [e1])
    _received(db_session, pid, e1, status="pending", prescription=presc)
    client, h = _client(api_client, lab.username)
    assert _search(client, h, "b2") == []


# ------------------------------------------------------------------ (c) pas deux fois, cote serveur

def _batch(client, h, pid, items, prescription=None):
    return client.post("/labo/results/batch", headers=h, json={
        "patient_id": pid, "prescribed_by_name": "Dr X",
        "origin_prescription_id": prescription.prescription_id if prescription else None,
        "results": items})


def test_meme_ligne_de_facture_recue_deux_fois_donne_409(db_session, api_client):
    lab, pid = _lab_and_patient(db_session, "c1")
    ex = _exam(db_session, "Glyc c1")
    item = _invoice(db_session, lab, pid, [ex])[0]
    client, h = _client(api_client, lab.username)
    line = lambda: {"examen_id": ex.id, "uuid": str(uuid.uuid4()), "origin_caisse_item_id": item.item_id}

    assert _batch(client, h, pid, [line()]).status_code == 201
    assert _batch(client, h, pid, [line()]).status_code == 409
    assert db_session.query(LabResult).filter_by(origin_caisse_item_id=item.item_id).count() == 1


def test_rejeu_du_meme_uuid_reste_idempotent(db_session, api_client):
    lab, pid = _lab_and_patient(db_session, "c2")
    ex = _exam(db_session, "Glyc c2")
    item = _invoice(db_session, lab, pid, [ex])[0]
    client, h = _client(api_client, lab.username)
    same = {"examen_id": ex.id, "uuid": str(uuid.uuid4()), "origin_caisse_item_id": item.item_id}
    assert _batch(client, h, pid, [same]).status_code == 201
    assert _batch(client, h, pid, [same]).status_code == 201     # rejeu connecteur : pas d'erreur, pas de doublon
    assert db_session.query(LabResult).filter_by(origin_caisse_item_id=item.item_id).count() == 1


def test_meme_examen_de_la_meme_ordonnance_recu_deux_fois_donne_409(db_session, api_client):
    lab, pid = _lab_and_patient(db_session, "c3")
    doc = create_test_user(db_session, "rc_doc_c3", "medecin", password=PWD)
    e1, e2 = _exam(db_session, "NFS c3"), _exam(db_session, "Glyc c3")
    presc = _prescription(db_session, pid, doc, [e1, e2])
    client, h = _client(api_client, lab.username)

    assert _batch(client, h, pid, [{"examen_id": e1.id, "uuid": str(uuid.uuid4())}], presc).status_code == 201
    assert _batch(client, h, pid, [{"examen_id": e1.id, "uuid": str(uuid.uuid4())}], presc).status_code == 409
    # une autre ligne de la meme ordonnance reste recevable
    assert _batch(client, h, pid, [{"examen_id": e2.id, "uuid": str(uuid.uuid4())}], presc).status_code == 201
    assert db_session.query(LabResult).filter_by(origin_prescription_id=presc.prescription_id).count() == 2


def test_lot_refuse_en_entier_si_une_ligne_est_un_doublon(db_session, api_client):
    lab, pid = _lab_and_patient(db_session, "c4")
    doc = create_test_user(db_session, "rc_doc_c4", "medecin", password=PWD)
    e1, e2 = _exam(db_session, "NFS c4"), _exam(db_session, "Glyc c4")
    presc = _prescription(db_session, pid, doc, [e1, e2])
    _received(db_session, pid, e1, prescription=presc)
    client, h = _client(api_client, lab.username)
    resp = _batch(client, h, pid, [{"examen_id": e2.id, "uuid": str(uuid.uuid4())}, {"examen_id": e1.id, "uuid": str(uuid.uuid4())}], presc)
    assert resp.status_code == 409
    assert db_session.query(LabResult).filter_by(origin_prescription_id=presc.prescription_id).count() == 1
