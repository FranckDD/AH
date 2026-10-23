# tests/test_lab_passages.py
"""
Regroupement des examens d'un meme passage patient (batch_id) - 2026-10-23.

Tout est additif : la paillasse, le tableau de bord et l'historique gardent tous leurs champs
d'origine ; ils gagnent le batch_id et la liste des examens du meme passage (termines compris),
pour que l'ecran montre un patient une seule fois avec tous ses examens.
"""
import os
import sys
import uuid
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from controller.lab_controller import LabController
from models.lab import Examen, LabResult
from repositories.lab_repo import LabRepository
from tests.conftest import create_test_user, create_test_patient

PASSWORD = "Correct123!"


def _examen(db, nom):
    ex = Examen(code=f"EXP-{uuid.uuid4().hex[:8]}", nom=nom, categorie="Bio", prix=1000)
    db.add(ex)
    db.flush()
    return ex


def _resultat(db, patient_id, examen, status, batch_id=None, minutes_ago=0):
    r = LabResult(
        patient_id=patient_id, test_type=examen.nom, status=status, examen_id=examen.id,
        code_lab_patient=f"LAB-P-{uuid.uuid4().hex[:10]}", batch_id=batch_id,
        test_date=datetime.now() - timedelta(minutes=minutes_ago),
    )
    db.add(r)
    db.flush()
    return r


def _controller(db):
    return LabController(repo=LabRepository(db))


def _passage(db, tag, statuses, minutes_ago=0):
    """Un patient (nom unique) avec un examen par statut, tous dans le meme batch_id."""
    user = create_test_user(db, f"lab_pass_{tag}", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db, user, first_name=f"Pass{tag}")
    batch = uuid.uuid4()
    rows = [_resultat(db, pid, _examen(db, f"Ex{tag}{i}"), st, batch_id=batch, minutes_ago=minutes_ago) for i, st in enumerate(statuses)]
    return pid, batch, rows


# --------------------------------------------------------------------- paillasse

def test_paillasse_ajoute_batch_id_et_les_examens_du_meme_passage_termines_compris(db_session):
    _, batch, rows = _passage(db_session, "A1", ["pending", "pending", "completed"])
    items = [i for i in _controller(db_session).get_paillasse_list() if i["batch_id"] == str(batch)]

    # seuls les examens a saisir restent des lignes (le compteur de la paillasse ne change pas)
    assert sorted(i["result_id"] for i in items) == sorted(r.result_id for r in rows if r.status == "pending")
    for item in items:
        exams = {e["result_id"]: e["status"] for e in item["batch_exams"]}
        # mais chaque ligne connait tous les examens du passage, y compris le termine
        assert exams == {r.result_id: r.status for r in rows}
        assert all({"result_id", "examen_nom", "status"} <= set(e) for e in item["batch_exams"])


def test_paillasse_garde_tous_les_champs_d_origine(db_session):
    _passage(db_session, "A2", ["pending"])
    item = next(i for i in _controller(db_session).get_paillasse_list() if "PassA2" in i["patient_name"])
    for k in ("result_id", "code", "patient_name", "patient_sexe", "patient_age", "is_external", "examen_nom", "test_date", "status"):
        assert k in item


def test_paillasse_examen_seul_sans_batch_id(db_session):
    user = create_test_user(db_session, "lab_pass_solo", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="PassSolo")
    r = _resultat(db_session, pid, _examen(db_session, "ExSolo"), "pending", batch_id=None)
    item = next(i for i in _controller(db_session).get_paillasse_list() if i["result_id"] == r.result_id)

    assert item["batch_id"] is None
    assert [e["result_id"] for e in item["batch_exams"]] == [r.result_id]


# --------------------------------------------------------------------- tableau de bord

def test_dashboard_recent_passages_regroupe_les_examens_d_un_patient(db_session):
    _, batch, rows = _passage(db_session, "B1", ["pending", "pending", "pending", "completed"])
    stats = LabRepository(db_session).get_advanced_stats("month")

    passage = next(p for p in stats["recent_passages"] if p["batch_id"] == str(batch))
    assert passage["patient_name"].startswith("PassB1")
    assert {e["result_id"] for e in passage["exams"]} == {r.result_id for r in rows}
    assert passage["first_pending_id"] in {r.result_id for r in rows if r.status == "pending"}
    assert len(stats["recent_passages"]) <= 3


def test_dashboard_recent_pending_d_origine_inchange(db_session):
    _passage(db_session, "B2", ["pending", "pending"])
    stats = LabRepository(db_session).get_advanced_stats("month")

    assert len(stats["recent_pending"]) <= 3
    assert {"id", "patient_name", "code_patient", "test_type"} <= set(stats["recent_pending"][0])


# --------------------------------------------------------------------- historique

def test_historique_groupe_pagine_par_passage_sans_couper_un_passage(db_session):
    # le plus recent : un passage de 3 examens ; plus ancien : 1 examen d'un autre passage
    user = create_test_user(db_session, "lab_pass_h1", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="PassHist")
    batch_new, batch_old = uuid.uuid4(), uuid.uuid4()
    new_rows = [_resultat(db_session, pid, _examen(db_session, f"ExH{i}"), "completed", batch_id=batch_new, minutes_ago=1) for i in range(3)]
    old_row = _resultat(db_session, pid, _examen(db_session, "ExHold"), "completed", batch_id=batch_old, minutes_ago=60)

    repo = LabRepository(db_session)
    total, page1 = repo.get_paginated_history(skip=0, limit=1, search_query="passhist", group_by_batch=True)
    assert total == 2                                                        # 2 passages, pas 4 examens
    assert {r.result_id for r in page1} == {r.result_id for r in new_rows}   # le passage entier tient sur la page
    total, page2 = repo.get_paginated_history(skip=1, limit=1, search_query="passhist", group_by_batch=True)
    assert [r.result_id for r in page2] == [old_row.result_id]


def test_historique_par_defaut_reste_une_ligne_par_examen(db_session):
    user = create_test_user(db_session, "lab_pass_h2", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="PassFlat")
    batch = uuid.uuid4()
    for i in range(3):
        _resultat(db_session, pid, _examen(db_session, f"ExF{i}"), "completed", batch_id=batch)

    total, rows = LabRepository(db_session).get_paginated_history(skip=0, limit=20, search_query="passflat")
    assert total == 3 and len(rows) == 3


def test_historique_examens_sans_batch_id_sont_chacun_leur_propre_passage(db_session):
    user = create_test_user(db_session, "lab_pass_h3", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="PassNoBatch")
    for i in range(2):
        _resultat(db_session, pid, _examen(db_session, f"ExN{i}"), "completed", batch_id=None)

    total, rows = LabRepository(db_session).get_paginated_history(skip=0, limit=20, search_query="passnobatch", group_by_batch=True)
    assert total == 2 and len(rows) == 2


def test_controleur_historique_groupe_expose_le_batch_id_et_compte_les_passages(db_session):
    user = create_test_user(db_session, "lab_pass_h4", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="PassCtl")
    batch = uuid.uuid4()
    for i in range(2):
        _resultat(db_session, pid, _examen(db_session, f"ExC{i}"), "completed", batch_id=batch)

    out = _controller(db_session).get_paginated_results(page=1, limit=10, search="passctl", group_by_batch=True)
    assert out["total_items"] == 1 and len(out["items"]) == 2
    assert {i["batch_id"] for i in out["items"]} == {str(batch)}


# --------------------------------------------------------------------- schemas de reponse

def test_les_schemas_de_reponse_laissent_passer_les_nouveaux_champs(db_session):
    from api_backend.backend_app.routes.labo.labo_schemas import LabStatsOut

    _, batch, _ = _passage(db_session, "S1", ["pending", "completed"])
    stats = LabStatsOut(**LabRepository(db_session).get_advanced_stats("month"))
    passage = next(p for p in stats.recent_passages if p.batch_id == str(batch))
    assert len(passage.exams) == 2 and passage.first_pending_id


# --------------------------------------------------------------------- bout en bout HTTP

def test_http_paillasse_stats_et_historique_groupe(db_session, api_client):
    from tests.conftest import auth_headers
    from api_backend.backend_app.routes.auth import auth_endpoints
    from api_backend.backend_app.routes.labo import lab_endpoints

    create_test_user(db_session, "lab_pass_http", "laborantin", password=PASSWORD)
    user = create_test_user(db_session, "lab_pass_http_p", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="PassHttp")
    batch = uuid.uuid4()
    rows = [_resultat(db_session, pid, _examen(db_session, f"ExHttp{i}"), st, batch_id=batch)
            for i, st in enumerate(["pending", "pending", "completed"])]

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_pass_http", PASSWORD)

    paillasse = client.get("/labo/paillasse", headers=headers).json()
    mine = [i for i in paillasse if i["batch_id"] == str(batch)]
    assert len(mine) == 2 and len(mine[0]["batch_exams"]) == 3

    stats = client.get("/labo/stats", headers=headers).json()
    assert any(p["batch_id"] == str(batch) and len(p["exams"]) == 3 for p in stats["recent_passages"])

    grouped = client.get("/labo/history/paginated", params={"search": "passhttp", "group": "true", "limit": 5}, headers=headers).json()
    assert grouped["total_items"] == 1 and len(grouped["items"]) == 3

    flat = client.get("/labo/history/paginated", params={"search": "passhttp", "limit": 5}, headers=headers).json()
    assert flat["total_items"] == 3


# --------------------------------------------------------------------- anomalies visibles des la liste

def test_historique_expose_le_nombre_d_anomalies_par_examen(db_session):
    from models.lab import LabResultDetail, Parametre
    user = create_test_user(db_session, "lab_pass_nb", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="PassNb")
    batch = uuid.uuid4()
    ex_a, ex_b = _examen(db_session, "ExNbA"), _examen(db_session, "ExNbB")
    ra = _resultat(db_session, pid, ex_a, "completed", batch_id=batch)
    rb = _resultat(db_session, pid, ex_b, "completed", batch_id=batch)
    pa = Parametre(examen_id=ex_a.id, nom_parametre="P1", unite="g/L", type_valeur="numeric")
    pb = Parametre(examen_id=ex_a.id, nom_parametre="P2", unite="g/L", type_valeur="numeric")
    db_session.add_all([pa, pb])
    db_session.flush()
    for p, flagged in ((pa, True), (pb, True)):
        db_session.add(LabResultDetail(result_id=ra.result_id, parametre_id=p.id, valeur_text="9", valeur_num=9, flagged=flagged))
    db_session.flush()

    out = _controller(db_session).get_paginated_results(page=1, limit=10, search="passnb", group_by_batch=True)
    by_id = {i["result_id"]: i["nb_anormaux"] for i in out["items"]}
    assert by_id == {ra.result_id: 2, rb.result_id: 0}
