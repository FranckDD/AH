# tests/test_toxico_domain_fixes.py
"""Defauts toxicologie releves par les guides (2026-10-26). Base partagee : deltas uniquement."""
from datetime import date, timedelta

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from controller.toxico_controller import ToxicoController
from models.patient import Patient
from repositories.toxico_repo import ToxicoRepository, ToxicoValidationError
from tests.conftest import auth_headers, create_test_user, create_test_patient

PWD = "TestPass123!"


def _admission(client, headers, psy, **extra):
    data = {"firstName": "Gen", "lastName": "Der", "dob": "1990-01-01", "mothersName": "Mere",
            "admissionDate": date.today().isoformat(), "substance": "Alcool", "psychologist": str(psy.user_id),
            "guardianName": "Tuteur", "guardianContact": "000"}
    data.update(extra)
    return client.post("/toxico/admission", data=data, headers=headers)


def test_nouvelle_admission_exige_le_sexe_et_l_enregistre(db_session, api_client):
    assistant = create_test_user(db_session, "t_tdf_assist", "Assistant", password=PWD)
    psy = create_test_user(db_session, "t_tdf_psy", "Psychologist", password=PWD)
    db_session.flush()
    client = api_client(auth_endpoints, toxico_endpoint)
    h = auth_headers(client, "t_tdf_assist", PWD)
    refused = _admission(client, h, psy, firstName="SansSexe")
    assert refused.status_code == 422, refused.text
    ok = _admission(client, h, psy, firstName="AvecSexe", gender="F")
    assert ok.status_code == 201, ok.text
    p = db_session.query(Patient).filter_by(code_patient=ok.json()["code_patient"]).one()
    assert p.gender == "F"


def test_liste_des_referents_ne_contient_que_les_psychologues(db_session):
    psy = create_test_user(db_session, "t_tdf_psy2", "Psychologist", password=PWD)
    mgr = create_test_user(db_session, "t_tdf_mgr2", "ToxicoManager", password=PWD)
    doc = create_test_user(db_session, "t_tdf_doc2", "medecin", password=PWD)
    db_session.flush()
    ids = {u.user_id for u in ToxicoRepository(db_session).get_psychologists()}
    assert psy.user_id in ids and mgr.user_id not in ids and doc.user_id not in ids


def _dossier(db, assistant, psy, first_name, admission=None, substance="Alcool"):
    pid, _ = create_test_patient(db, assistant, first_name=first_name, mother_name="Maman Stockee")
    repo = ToxicoRepository(db)
    d = repo.create_dossier_after_patient_commit(pid, {
        "admission_date": admission or date.today() - timedelta(days=10), "substance": substance,
        "psychologist_id": psy.user_id, "guardian_name": "G", "guardian_contact": "1"})
    return pid, d, repo


def test_sortie_a_une_date_passee_mais_ni_future_ni_avant_l_admission(db_session):
    assistant = create_test_user(db_session, "t_tdf_a3", "Assistant", password=PWD)
    psy = create_test_user(db_session, "t_tdf_p3", "Psychologist", password=PWD)
    pid, d, repo = _dossier(db_session, assistant, psy, "SortieDate", admission=date.today() - timedelta(days=10))
    with pytest.raises(ToxicoValidationError):
        repo.discharge(d.id, "guerison", None, psy.user_id, discharge_date=date.today() + timedelta(days=1))
    with pytest.raises(ToxicoValidationError):
        repo.discharge(d.id, "guerison", None, psy.user_id, discharge_date=date.today() - timedelta(days=11))
    past = date.today() - timedelta(days=3)
    repo.discharge(d.id, "guerison", None, psy.user_id, discharge_date=past)
    stay = repo.get_open_stay(d.id)
    assert stay is None
    from models.toxico import ToxicoStay
    s = db_session.query(ToxicoStay).filter_by(dossier_id=d.id).one()
    assert s.discharge_date == past


def test_stats_globales_independantes_de_la_recherche(db_session):
    assistant = create_test_user(db_session, "t_tdf_a4", "Assistant", password=PWD)
    psy = create_test_user(db_session, "t_tdf_p4", "Psychologist", password=PWD)
    repo = ToxicoRepository(db_session)
    before = repo.active_stats()
    _dossier(db_session, assistant, psy, "StatUn", substance="Cannabis")
    _dossier(db_session, assistant, psy, "StatDeux", admission=date.today() - timedelta(days=2), substance="Cannabis")
    after = repo.active_stats()
    assert after["total_active"] == before["total_active"] + 2
    assert after["by_phase"][1] == before["by_phase"][1] + 2
    assert after["by_substance"].get("Cannabis", 0) == before["by_substance"].get("Cannabis", 0) + 2
    assert after["new_this_week"] == before["new_this_week"] + 1  # seul le dossier admis il y a 2 jours
    assert after["by_psychologist"][psy.full_name] == before["by_psychologist"].get(psy.full_name, 0) + 2
    assert set(after) >= {"total_active", "by_phase", "relapse_patients", "by_substance", "by_psychologist", "new_this_week"}


def test_le_detail_donne_le_nom_de_la_mere_enregistre(db_session):
    assistant = create_test_user(db_session, "t_tdf_a5", "Assistant", password=PWD)
    psy = create_test_user(db_session, "t_tdf_p5", "Psychologist", password=PWD)
    pid, d, repo = _dossier(db_session, assistant, psy, "MereOk")
    from controller.toxico_controller import ToxicoController
    ctrl = ToxicoController.__new__(ToxicoController)
    ctrl.user = assistant
    out = ctrl.serialize_dossier_details(repo.get_dossier_full(pid))
    assert out["mothersName"] == "Maman Stockee"
