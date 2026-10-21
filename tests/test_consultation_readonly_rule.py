# tests/test_consultation_readonly_rule.py
"""Regle « consultation passee = lecture seule » (2026-10-21).

Des qu'un patient a une consultation plus recente, les precedentes ne sont
plus modifiables et ne recoivent plus de prescription (409). Ordre :
consultation_date DESC NULLS LAST, record_id DESC (repositories/consultation_lock.py).

NB : dans une meme transaction de test, LOCALTIMESTAMP (utilise par la
procedure create_medical_record) est constant - deux consultations creees
dans le meme test ont donc la meme date et l'egalite est departagee par
record_id (la plus recemment creee gagne), exactement la regle voulue.
"""
import sys
import os
from datetime import date, datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import text

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.medical_records import medical_records_endpoint
from api_backend.backend_app.routes.prescription import prescriptions_endpoints
from repositories.consultation_lock import (
    LOCKED_MESSAGE, ConsultationLockedError, assert_consultation_writable, is_latest_consultation,
)
from tests.conftest import create_test_user, create_test_patient, create_test_medical_record, auth_headers

PW = "TestPass123!"


def _client(api_client):
    return api_client(auth_endpoints, medical_records_endpoint, prescriptions_endpoints)


def _new_record(session, user, patient_id):
    create_test_medical_record(session, user, patient_id)
    return session.execute(
        text("SELECT max(record_id) FROM medical_records WHERE patient_id = :p"), {"p": patient_id}
    ).scalar()


def _new_prescription(session, patient_id, record_id, user):
    session.execute(
        text(
            "INSERT INTO prescriptions (patient_id, medical_record_id, medication, dosage, frequency, duration, start_date, status, prescribed_by) "
            "VALUES (:p, :r, 'Paracetamol', '500mg', '3x/j', '5 jours', :d, 'active', :u)"
        ),
        {"p": patient_id, "r": record_id, "d": date.today(), "u": user.user_id},
    )
    session.commit()  # sinon le rollback de l'endpoint (409) annulerait l'insertion de test
    return session.execute(
        text("SELECT max(prescription_id) FROM prescriptions WHERE medical_record_id = :r"), {"r": record_id}
    ).scalar()


MR_FIELDS = ("marital_status", "bp", "temperature", "weight", "height", "medical_history",
             "allergies", "symptoms", "treatment", "severity", "notes")


def _mr(**kw):
    """Payload complet (le vrai client envoie toujours tous les champs ;
    la procedure update_medical_record exige chaque parametre)."""
    return {**{k: None for k in MR_FIELDS}, "motif_code": "consultation", "diagnosis": "modif", **kw}


def _pu(patient_id, record_id, **kw):
    return {**_presc_payload(patient_id, record_id), **kw}


def _presc_payload(patient_id, record_id):
    return {
        "patient_id": patient_id, "medical_record_id": record_id, "medication": "Amoxicilline",
        "dosage": "500mg", "frequency": "2x/jour", "duration": "7 jours", "start_date": str(date.today()),
    }


@pytest.fixture
def setup(db_session, api_client):
    med = create_test_user(db_session, "ro_rule_medecin", "medecin", password=PW)
    patient_id, _ = create_test_patient(db_session, med)
    old_id = _new_record(db_session, med, patient_id)
    new_id = _new_record(db_session, med, patient_id)
    client = _client(api_client)
    headers = auth_headers(client, "ro_rule_medecin", PW)
    return dict(session=db_session, med=med, patient_id=patient_id, old=old_id, new=new_id, client=client, h=headers)


# ---------- consultations ----------

def test_old_consultation_update_refused_newest_allowed(setup):
    c, h = setup["client"], setup["h"]
    r = c.put(f"/medical_records/{setup['old']}", json=_mr(), headers=h)
    assert r.status_code == 409
    assert r.json()["detail"] == LOCKED_MESSAGE
    r = c.put(f"/medical_records/{setup['new']}", json=_mr(), headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["is_editable"] is True


def test_old_consultation_delete_refused(setup):
    r = setup["client"].delete(f"/medical_records/{setup['old']}", headers=setup["h"])
    assert r.status_code == 409


def test_unknown_consultation_is_404_not_409(setup):
    c, h = setup["client"], setup["h"]
    assert c.put("/medical_records/999999999", json=_mr(), headers=h).status_code == 404
    assert c.delete("/medical_records/999999999", headers=h).status_code == 404


def test_creating_new_consultation_flips_previous_to_readonly(setup):
    s, c, h = setup["session"], setup["client"], setup["h"]
    assert is_latest_consultation(s, setup["new"]) is True
    third = _new_record(s, setup["med"], setup["patient_id"])
    assert is_latest_consultation(s, setup["new"]) is False
    assert is_latest_consultation(s, third) is True
    assert c.put(f"/medical_records/{setup['new']}", json=_mr(), headers=h).status_code == 409


def test_retroactive_dated_consultation_is_the_older_one(setup):
    """Une consultation datee AVANT (meme si creee apres) est l'ancienne :
    seule la date compte, l'id ne sert qu'a departager une egalite."""
    s = setup["session"]
    late_entry = _new_record(s, setup["med"], setup["patient_id"])
    s.execute(text("UPDATE medical_records SET consultation_date = :d WHERE record_id = :r"),
              {"d": datetime(2000, 1, 1), "r": late_entry})
    assert is_latest_consultation(s, late_entry) is False
    assert is_latest_consultation(s, setup["new"]) is True
    with pytest.raises(ConsultationLockedError):
        assert_consultation_writable(s, late_entry)


def test_other_patients_unaffected(setup):
    s, c, h = setup["session"], setup["client"], setup["h"]
    other_pid, _ = create_test_patient(s, setup["med"])
    other = _new_record(s, setup["med"], other_pid)
    assert is_latest_consultation(s, other) is True
    r = c.put(f"/medical_records/{other}", json=_mr(), headers=h)
    assert r.status_code == 200


def test_is_editable_in_payloads(setup):
    c, h, pid = setup["client"], setup["h"], setup["patient_id"]
    hist = c.get(f"/medical_records/patient/{pid}/history", headers=h).json()
    flags = {r["record_id"]: r["is_editable"] for r in hist}
    assert flags[setup["old"]] is False and flags[setup["new"]] is True
    assert c.get(f"/medical_records/{setup['old']}", headers=h).json()["is_editable"] is False
    page = c.get("/medical_records/", params={"patient_id": pid}, headers=h).json()["data"]
    assert {r["record_id"]: r["is_editable"] for r in page} == flags


# ---------- prescriptions ----------

def test_prescription_create_on_old_refused_on_newest_allowed(setup):
    c, h, pid = setup["client"], setup["h"], setup["patient_id"]
    r = c.post("/prescriptions/", json=_presc_payload(pid, setup["old"]), headers=h)
    assert r.status_code == 409
    assert r.json()["detail"] == LOCKED_MESSAGE
    r = c.post("/prescriptions/", json=_presc_payload(pid, setup["new"]), headers=h)
    assert r.status_code == 201, r.text
    # sans consultation : non concernee
    r = c.post("/prescriptions/", json=_presc_payload(pid, None), headers=h)
    assert r.status_code == 201


def test_prescription_update_stop_delete_on_old_refused(setup):
    s, c, h = setup["session"], setup["client"], setup["h"]
    presc = _new_prescription(s, setup["patient_id"], setup["old"], setup["med"])
    assert c.put(f"/prescriptions/{presc}", json=_pu(setup["patient_id"], setup["old"], dosage="1g"), headers=h).status_code == 409
    # arret / renouvellement passent par PUT (end_date/duration) ; status
    # n'est pas dans PrescriptionUpdate (ignore) mais la requete reste refusee.
    assert c.put(f"/prescriptions/{presc}", json=_pu(setup["patient_id"], setup["old"], status="completed"), headers=h).status_code == 409
    assert c.put(f"/prescriptions/{presc}", json=_pu(setup["patient_id"], setup["old"], status="active"), headers=h).status_code == 409
    assert c.put(f"/prescriptions/{presc}", json=_pu(setup["patient_id"], setup["old"], end_date="2099-01-01"), headers=h).status_code == 409
    assert c.delete(f"/prescriptions/{presc}", headers=h).status_code == 409
    got = c.get(f"/prescriptions/{presc}", headers=h)
    assert got.status_code == 200 and got.json()["is_editable"] is False


def test_prescription_on_newest_editable_and_cannot_be_moved_to_old(setup):
    s, c, h = setup["session"], setup["client"], setup["h"]
    presc = _new_prescription(s, setup["patient_id"], setup["new"], setup["med"])
    r = c.put(f"/prescriptions/{presc}", json=_pu(setup["patient_id"], setup["new"], status="completed"), headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["is_editable"] is True
    assert c.put(f"/prescriptions/{presc}", json=_pu(setup["patient_id"], setup["old"]), headers=h).status_code == 409
    assert c.delete(f"/prescriptions/{presc}", headers=h).status_code == 204


def test_prescription_unknown_is_404(setup):
    c, h = setup["client"], setup["h"]
    assert c.put("/prescriptions/999999999", json=_pu(setup["patient_id"], None), headers=h).status_code == 404


def test_prescription_is_editable_flag_in_patient_list(setup):
    s, c, h, pid = setup["session"], setup["client"], setup["h"], setup["patient_id"]
    p_old = _new_prescription(s, pid, setup["old"], setup["med"])
    p_new = _new_prescription(s, pid, setup["new"], setup["med"])
    items = c.get(f"/prescriptions/patient/{pid}", headers=h).json()
    flags = {p["prescription_id"]: p["is_editable"] for p in items}
    assert flags[p_old] is False and flags[p_new] is True


# ---------- role matrix unchanged ----------

def test_role_matrix_unchanged(db_session, api_client):
    """nurse garde l'ecriture sur la plus recente (comme avant) ; un role
    hors perimetre reste refuse par le garde de route (403), jamais 409."""
    nurse = create_test_user(db_session, "ro_rule_nurse", "nurse", password=PW)
    create_test_user(db_session, "ro_rule_secr", "secretaire", password=PW)
    pid, _ = create_test_patient(db_session, nurse)
    old = _new_record(db_session, nurse, pid)
    new = _new_record(db_session, nurse, pid)
    c = _client(api_client)
    hn = auth_headers(c, "ro_rule_nurse", PW)
    hs = auth_headers(c, "ro_rule_secr", PW)
    assert c.put(f"/medical_records/{new}", json=_mr(), headers=hn).status_code == 200
    assert c.put(f"/medical_records/{old}", json=_mr(), headers=hn).status_code == 409
    assert c.put(f"/medical_records/{old}", json=_mr(), headers=hs).status_code == 403


# ---------- revue 2026-10-22 ----------

def _set_date(session, record_id, value):
    session.execute(text("UPDATE medical_records SET consultation_date = :d WHERE record_id = :r"),
                    {"d": value, "r": record_id})
    session.commit()


def test_tie_on_same_date_broken_by_record_id(setup):
    s = setup["session"]
    same = datetime(2026, 5, 5, 10, 0, 0)
    _set_date(s, setup["old"], same)
    _set_date(s, setup["new"], same)
    assert is_latest_consultation(s, setup["new"]) is True
    assert is_latest_consultation(s, setup["old"]) is False


def test_null_date_counts_as_oldest(setup):
    s = setup["session"]
    _set_date(s, setup["new"], None)
    assert is_latest_consultation(s, setup["old"]) is True
    assert is_latest_consultation(s, setup["new"]) is False


def test_move_prescription_from_old_to_newest_refused(setup):
    s, c, h, pid = setup["session"], setup["client"], setup["h"], setup["patient_id"]
    presc = _new_prescription(s, pid, setup["old"], setup["med"])
    assert c.put(f"/prescriptions/{presc}", json=_pu(pid, setup["new"]), headers=h).status_code == 409


def test_detaching_prescription_from_old_consultation_refused(setup):
    s, c, h, pid = setup["session"], setup["client"], setup["h"], setup["patient_id"]
    presc = _new_prescription(s, pid, setup["old"], setup["med"])
    r = c.put(f"/prescriptions/{presc}", json=_pu(pid, None, dosage="1g"), headers=h)
    assert r.status_code == 409
    assert s.execute(text("SELECT medical_record_id FROM prescriptions WHERE prescription_id = :p"),
                     {"p": presc}).scalar() == setup["old"]


def test_replayed_prescription_create_same_uuid_not_409(setup):
    s, c, h, pid = setup["session"], setup["client"], setup["h"], setup["patient_id"]
    body = {**_presc_payload(pid, setup["new"]), "uuid": "3f0e7a52-8b1c-4c1e-9a77-1d2b3c4d5e6f"}
    assert c.post("/prescriptions/", json=body, headers=h).status_code == 201
    _new_record(s, setup["med"], pid)  # "new" devient ancienne
    r = c.post("/prescriptions/", json=body, headers=h)
    assert r.status_code == 201, r.text
    assert s.execute(text("SELECT count(*) FROM prescriptions WHERE uuid = CAST(:u AS uuid)"),
                     {"u": body["uuid"]}).scalar() == 1


def test_replayed_identical_updates_not_409(setup):
    s, c, h, pid = setup["session"], setup["client"], setup["h"], setup["patient_id"]
    presc = _new_prescription(s, pid, setup["new"], setup["med"])
    pbody = _pu(pid, setup["new"], dosage="1g")
    mbody = _mr(diagnosis="final")
    assert c.put(f"/prescriptions/{presc}", json=pbody, headers=h).status_code == 200
    assert c.put(f"/medical_records/{setup['new']}", json=mbody, headers=h).status_code == 200
    _new_record(s, setup["med"], pid)
    assert c.put(f"/prescriptions/{presc}", json=pbody, headers=h).status_code == 200
    assert c.put(f"/medical_records/{setup['new']}", json=mbody, headers=h).status_code == 200
    # mais une VRAIE modification reste refusee
    assert c.put(f"/prescriptions/{presc}", json=_pu(pid, setup["new"], dosage="2g"), headers=h).status_code == 409
    assert c.put(f"/medical_records/{setup['new']}", json=_mr(diagnosis="autre"), headers=h).status_code == 409


def test_pending_review_and_claim_carry_is_editable(db_session, api_client):
    nurse = create_test_user(db_session, "ro_rule_nurse2", "nurse", password=PW)
    med = create_test_user(db_session, "ro_rule_med2", "medecin", password=PW)
    pid, _ = create_test_patient(db_session, nurse)
    create_test_medical_record(db_session, nurse, pid, needs_doctor_review=True, assigned_doctor_id=med.user_id)
    rid = db_session.execute(text("SELECT max(record_id) FROM medical_records WHERE patient_id = :p"), {"p": pid}).scalar()
    c = _client(api_client)
    hm = auth_headers(c, "ro_rule_med2", PW)
    pending = [r for r in c.get("/medical_records/pending-review", headers=hm).json() if r["record_id"] == rid]
    assert pending and pending[0]["is_editable"] is True
    r = c.post(f"/medical_records/{rid}/claim", headers=hm)
    assert r.status_code == 200, r.text
    assert r.json()["is_editable"] is True


def test_get_by_day_annotated(setup):
    from controller.medical_controller import MedicalRecordController
    from repositories.medical_repo import MedicalRecordRepository
    s = setup["session"]
    ctrl = MedicalRecordController(repo=MedicalRecordRepository(s), current_user=setup["med"])
    day = s.execute(text("SELECT consultation_date::date FROM medical_records WHERE record_id = :r"),
                    {"r": setup["new"]}).scalar()
    mine = {r.record_id: r.is_editable for r in ctrl.get_by_day(day) if r.patient_id == setup["patient_id"]}
    assert mine == {setup["old"]: False, setup["new"]: True}


def test_concurrency_lock_taken_and_sequential_equivalence(setup, monkeypatch):
    """Simulation : la creation d'une consultation et l'ecriture sur la
    precedente prennent le meme verrou patient (FOR NO KEY UPDATE) ; quel que
    soit l'ordre de passage, le resultat est celui d'une execution
    sequentielle."""
    s, c, h, pid = setup["session"], setup["client"], setup["h"], setup["patient_id"]
    seen = []
    real_execute = s.execute

    def spy(stmt, *a, **kw):
        sql = str(stmt)
        if "FOR NO KEY UPDATE" in sql:
            seen.append(sql)
        return real_execute(stmt, *a, **kw)

    monkeypatch.setattr(s, "execute", spy)
    # ordre 1 : edition de la plus recente PUIS creation -> les deux passent
    assert c.put(f"/medical_records/{setup['new']}", json=_mr(diagnosis="avant"), headers=h).status_code == 200
    assert seen, "le verrou patient doit etre pris par l'ecriture"
    n = len(seen)
    third = _new_record(s, setup["med"], pid)
    assert len(seen) > n, "le verrou patient doit etre pris par la creation"
    # ordre 2 : la creation est passee -> l'edition de la precedente est refusee
    assert c.put(f"/medical_records/{setup['new']}", json=_mr(diagnosis="apres"), headers=h).status_code == 409
    assert c.put(f"/medical_records/{third}", json=_mr(diagnosis="apres"), headers=h).status_code == 200
    assert not any("FOR UPDATE" in q.replace("FOR NO KEY UPDATE", "") for q in seen)
