# tests/test_lab_domain_fixes.py
"""Defauts labo releves par les guides (2026-10-26, groupe laboratoire/stock/toxico/production)."""
import uuid
from datetime import datetime
from types import SimpleNamespace

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from controller.lab_controller import LabController
from models.lab import Examen, LabResult
from repositories.lab_repo import LabRepository
from tests.conftest import create_test_user, create_test_patient, auth_headers

PWD = "Correct123!"


def _examen(db, nom):
    ex = Examen(code=f"DF-{uuid.uuid4().hex[:8]}", nom=nom, categorie="Bio", prix=1000)
    db.add(ex)
    db.flush()
    return ex


def _resultat(db, pid, ex, status, minutes=0):
    r = LabResult(patient_id=pid, test_type=ex.nom, status=status, examen_id=ex.id,
                  code_lab_patient=f"LAB-DF-{uuid.uuid4().hex[:8]}", test_date=datetime.now())
    db.add(r)
    db.flush()
    return r


# --- ordre des parametres : ordre de definition, jamais l'ordre physique des lignes
from repositories.lab_repo import patient_bio


def test_detail_d_un_resultat_garde_l_ordre_de_definition_des_parametres():
    def det(did, pid, nom):
        return SimpleNamespace(detail_id=did, parametre_id=pid, valeur_num=1, valeur_text="1", interpretation=None,
                               flagged=False, parametre=SimpleNamespace(nom_parametre=nom, unite="u", input_type="numeric",
                                                                       options_list=None, reference_ranges=[], ordre=pid))
    # lignes revenues dans l'ordre inverse (cas d'une ligne modifiee apres un brouillon)
    r = SimpleNamespace(result_id=1, code_lab_patient="LAB-1", status="pending", note=None, test_date=None,
                        prescribed_by_name=None, patient=None, external_patient_info={"nom": "Ext"}, examen=None,
                        corrected=False, corrected_at=None,
                        details=[det(30, 12, "C"), det(10, 10, "A"), det(20, 11, "B")])
    repo = SimpleNamespace(get_full_lab_result=lambda _id: r, list_amendments=lambda _id: [],
                           _patient_bio=patient_bio)
    ctrl = LabController(repo=repo)
    out = ctrl.get_result_detail(1)
    assert [d["nom"] for d in out["details"]] == ["A", "B", "C"]


# --- filtre Pending de l'historique : tout ce qui n'est pas termine
def test_historique_pending_couvre_les_demandes_en_cours(db_session):
    user = create_test_user(db_session, "df_lab_pend", "admin", password=PWD)
    pid, _ = create_test_patient(db_session, user, first_name="DfPend", last_name="ZqPend")
    rows = {st: _resultat(db_session, pid, _examen(db_session, f"E{st}"), st) for st in ("pending", "partial", "analyzed", "completed")}
    total, items = LabRepository(db_session).get_paginated_history(skip=0, limit=50, search_query="ZqPend", status="pending", group_by_batch=False)
    ids = {r.result_id for r in items}
    assert ids == {rows["pending"].result_id, rows["partial"].result_id, rows["analyzed"].result_id}
    assert total == 3


# --- noms patients : "Nom Prenom" partout, patient externe = nom declare
def test_reception_affiche_nom_et_prenom(db_session, api_client):
    lab = create_test_user(db_session, "df_lab_name", "laborantin", password=PWD)
    lab.postgres_role = "app_laborantin"
    db_session.flush()
    pid, _ = create_test_patient(db_session, lab, first_name="Linda", last_name="ZqEtoga")
    from models.prescription import Prescription
    from datetime import date
    ex = _examen(db_session, "Glycemie df")
    p = Prescription(patient_id=pid, medication="Examens", dosage="-", frequency="-", duration="-", start_date=date.today(),
                     status="active", is_lab_order=True, lab_exams_list=[ex.nom], prescribed_by=lab.user_id, prescribed_by_name="x")
    db_session.add(p)
    db_session.flush()
    client = api_client(auth_endpoints, lab_endpoints)
    h = auth_headers(client, lab.username, PWD)
    resp = client.get("/labo/search-internal", headers=h, params={"q": "ZqEtoga"})
    assert resp.status_code == 200, resp.text
    assert resp.json()[0]["nom"] == "ZqEtoga Linda"


def test_tableau_de_bord_montre_le_nom_declare_du_patient_externe(db_session):
    user = create_test_user(db_session, "df_lab_ext", "admin", password=PWD)
    pid, _ = create_test_patient(db_session, user, first_name="Linda", last_name="ZqDash")
    ex = _examen(db_session, "ExDash")
    interne = _resultat(db_session, pid, ex, "pending")
    externe = LabResult(patient_id=None, test_type=ex.nom, status="pending", examen_id=ex.id,
                        code_lab_patient=f"LAB-DF-{uuid.uuid4().hex[:8]}", test_date=datetime.now(),
                        external_patient_info={"nom": "Mbarga", "prenom": "Paul"})
    db_session.add(externe)
    db_session.flush()
    stats = LabRepository(db_session).get_advanced_stats("day")
    names = {i["id"]: i["patient_name"] for i in stats["recent_pending"]}
    assert names[interne.result_id] == "ZqDash Linda"
    assert names[externe.result_id] == "Mbarga Paul"
