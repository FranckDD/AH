# tests/test_lab_amend.py
"""
Resultat labo valide = lecture seule pour le technicien (defaut 5, guides 2026-10-26).
Toute modification passe par la correction : motif obligatoire, valeurs d'avant conservees,
resultat marque « corrige », medecin prescripteur notifie.
"""
import uuid
from datetime import datetime

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from models.lab import Examen, LabResult, LabResultAmendment, LabResultDetail, Parametre
from models.notification import Notification
from tests.conftest import create_test_user, create_test_patient, auth_headers

PWD = "Correct123!"


def _completed(db, tag, prescriber=None):
    lab = create_test_user(db, f"am_lab_{tag}", "laborantin", password=PWD)
    pid, _ = create_test_patient(db, lab, first_name=f"Amend{tag}", gender="F")
    ex = Examen(code=f"AM-{uuid.uuid4().hex[:8]}", nom=f"Glyc {tag}", categorie="Bio", prix=1000)
    db.add(ex)
    db.flush()
    p = Parametre(examen_id=ex.id, nom_parametre="Glycemie", unite="g/L", type_valeur="numeric", input_type="numeric")
    db.add(p)
    db.flush()
    r = LabResult(patient_id=pid, test_type=ex.nom, status="completed", examen_id=ex.id, note="RAS",
                  prescribed_by=prescriber.user_id if prescriber else None,
                  code_lab_patient=f"LAB-AM-{uuid.uuid4().hex[:8]}", test_date=datetime.now())
    db.add(r)
    db.flush()
    d = LabResultDetail(result_id=r.result_id, parametre_id=p.id, valeur_text="0.9", valeur_num=0.9, flagged=False, interpretation="Normal")
    db.add(d)
    db.flush()
    return lab, r, d


def _client(api_client, username):
    client = api_client(auth_endpoints, lab_endpoints)
    return client, auth_headers(client, username, PWD)


def _put(client, headers, r, d, valeur, completed=False, note=None):
    return client.put(f"/labo/results/{r.result_id}/values", headers=headers,
                      json={"values": {str(d.detail_id): {"valeur": valeur}}, "completed": completed, "note": note})


# ------------------------------------------------------------------ lecture seule

def test_modifier_un_resultat_valide_est_refuse_et_ne_change_rien(db_session, api_client):
    lab, r, d = _completed(db_session, "a1")
    client, h = _client(api_client, lab.username)
    resp = _put(client, h, r, d, 2.5, completed=True)
    assert resp.status_code == 409, resp.text
    db_session.expire_all()
    assert float(db_session.get(LabResultDetail, d.detail_id).valeur_num) == 0.9
    assert db_session.get(LabResult, r.result_id).status == "completed"


def test_brouillon_sur_un_resultat_valide_ne_le_rouvre_pas(db_session, api_client):
    lab, r, d = _completed(db_session, "a2")
    client, h = _client(api_client, lab.username)
    resp = _put(client, h, r, d, 2.5, completed=False)
    assert resp.status_code == 409, resp.text
    db_session.expire_all()
    assert db_session.get(LabResult, r.result_id).status == "completed"


def test_rejeu_identique_d_une_operation_deja_appliquee_reste_sans_effet(db_session, api_client):
    lab, r, d = _completed(db_session, "a3")
    client, h = _client(api_client, lab.username)
    assert _put(client, h, r, d, 0.9, completed=True).status_code == 200
    resp = client.put(f"/labo/results/{r.result_id}/values", headers=h, json={"values": {}, "completed": True, "note": "RAS"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "completed"


def test_modifier_la_note_d_un_resultat_valide_est_refuse(db_session, api_client):
    lab, r, d = _completed(db_session, "a4")
    client, h = _client(api_client, lab.username)
    resp = client.put(f"/labo/results/{r.result_id}/values", headers=h, json={"values": {}, "completed": False, "note": "Autre"})
    assert resp.status_code == 409


# ------------------------------------------------------------------ correction

def _amend(client, headers, r, d, valeur, reason="Erreur de saisie", note=None):
    body = {"values": {str(d.detail_id): {"valeur": valeur}}, "reason": reason}
    if note is not None:
        body["note"] = note
    return client.post(f"/labo/results/{r.result_id}/amend", headers=headers, json=body)


def test_correction_sans_motif_est_refusee(db_session, api_client):
    lab, r, d = _completed(db_session, "b1")
    client, h = _client(api_client, lab.username)
    assert _amend(client, h, r, d, 1.4, reason="").status_code == 422
    assert _amend(client, h, r, d, 1.4, reason="   ").status_code == 422
    db_session.expire_all()
    assert float(db_session.get(LabResultDetail, d.detail_id).valeur_num) == 0.9


def test_correction_d_un_resultat_non_valide_est_refusee(db_session, api_client):
    lab, r, d = _completed(db_session, "b2")
    r.status = "partial"
    db_session.flush()
    client, h = _client(api_client, lab.username)
    assert _amend(client, h, r, d, 1.4).status_code == 409


def test_correction_garde_l_ancien_contenu_marque_corrige_et_previent_le_medecin(db_session, api_client):
    doc = create_test_user(db_session, "am_doc_b3", "medecin", password=PWD)
    lab, r, d = _completed(db_session, "b3", prescriber=doc)
    client, h = _client(api_client, lab.username)

    resp = _amend(client, h, r, d, 1.4, reason="Mauvaise lecture de l'appareil", note="Hyperglycemie")
    assert resp.status_code == 200, resp.text

    db_session.expire_all()
    res = db_session.get(LabResult, r.result_id)
    assert res.status == "completed" and res.corrected is True and res.corrected_at is not None
    assert res.note == "Hyperglycemie"
    det = db_session.get(LabResultDetail, d.detail_id)
    assert float(det.valeur_num) == 1.4 and det.flagged is False  # pas de plage definie ici

    rows = db_session.query(LabResultAmendment).filter_by(result_id=r.result_id).all()
    assert len(rows) == 1
    a = rows[0]
    assert a.reason == "Mauvaise lecture de l'appareil"
    assert a.previous_note == "RAS"
    assert a.amended_by == lab.user_id
    assert a.previous_values[0]["valeur_num"] == 0.9 and a.previous_values[0]["interpretation"] == "Normal"

    notifs = db_session.query(Notification).filter_by(recipient_user_id=doc.user_id, type="lab_result_corrected").all()
    assert len(notifs) == 1
    assert notifs[0].payload["result_id"] == r.result_id
    assert notifs[0].payload["reason"] == "Mauvaise lecture de l'appareil"


def test_deux_corrections_gardent_chacune_leur_avant(db_session, api_client):
    lab, r, d = _completed(db_session, "b4")
    client, h = _client(api_client, lab.username)
    assert _amend(client, h, r, d, 1.1, reason="Premiere").status_code == 200
    assert _amend(client, h, r, d, 1.2, reason="Seconde").status_code == 200
    db_session.expire_all()
    rows = db_session.query(LabResultAmendment).filter_by(result_id=r.result_id).order_by(LabResultAmendment.amendment_id).all()
    assert [a.previous_values[0]["valeur_num"] for a in rows] == [0.9, 1.1]


def test_correction_interdite_au_medecin(db_session, api_client):
    doc = create_test_user(db_session, "am_doc_b5", "medecin", password=PWD)
    lab, r, d = _completed(db_session, "b5", prescriber=doc)
    client, h = _client(api_client, doc.username)
    assert _amend(client, h, r, d, 1.4).status_code == 403


def test_detail_et_historique_exposent_le_marquage_corrige(db_session, api_client):
    lab, r, d = _completed(db_session, "b6")
    client, h = _client(api_client, lab.username)
    assert client.get(f"/labo/results/{r.result_id}", headers=h).json()["corrected"] is False
    assert _amend(client, h, r, d, 1.4, reason="Erreur").status_code == 200

    detail = client.get(f"/labo/results/{r.result_id}", headers=h).json()
    assert detail["corrected"] is True
    assert detail["amendments"][0]["reason"] == "Erreur"
    assert detail["amendments"][0]["amended_by_name"]

    hist = client.get("/labo/history/paginated", headers=h, params={"search": r.code_lab_patient}).json()
    assert [i["corrected"] for i in hist["items"]] == [True]
