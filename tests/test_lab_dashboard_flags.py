# tests/test_lab_dashboard_flags.py
"""
Logique du dashboard labo (get_advanced_stats) et compteur d'anomalies par
dossier (count_flagged_by_result / nb_anormaux) - correctifs labo 2026-10-20.

Les compteurs sont globaux a la base de test : chaque test compare un etat
avant/apres plutot que des valeurs absolues.
"""
import os
import sys
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from controller.lab_controller import LabController
from models.lab import Examen, LabResult, LabResultDetail, Parametre
from repositories.lab_repo import LabRepository
from tests.conftest import create_test_user, create_test_patient

PASSWORD = "Correct123!"


def _examen(db, suffix):
    ex = Examen(code=f"EXD-{suffix}-{uuid.uuid4().hex[:4]}", nom=f"Examen {suffix}", categorie="Bio", prix=1000)
    db.add(ex)
    db.flush()
    return ex


def _parametre(db, examen):
    p = Parametre(examen_id=examen.id, nom_parametre="Glycemie", unite="g/L", type_valeur="numeric")
    db.add(p)
    db.flush()
    return p


def _resultat(db, patient_id, examen, status):
    r = LabResult(
        patient_id=patient_id, test_type=examen.nom, status=status,
        examen_id=examen.id, code_lab_patient=f"LAB-D-{uuid.uuid4().hex[:10]}",
    )
    db.add(r)
    db.flush()
    return r


def _detail(db, result, parametre, flagged):
    d = LabResultDetail(result_id=result.result_id, parametre_id=parametre.id,
                        valeur_text="9", valeur_num=9, flagged=flagged)
    db.add(d)
    db.flush()
    return d


def test_pathologiques_compte_aussi_les_dossiers_completed(db_session):
    user = create_test_user(db_session, "lab_dash_u1", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="DashA")
    ex = _examen(db_session, "A")
    param = _parametre(db_session, ex)
    repo = LabRepository(db_session)

    avant = repo.get_advanced_stats("month")["critical"]
    r = _resultat(db_session, pid, ex, "completed")
    _detail(db_session, r, param, flagged=True)
    apres = repo.get_advanced_stats("month")["critical"]

    assert apres == avant + 1


def test_pathologiques_ignore_les_dossiers_sans_flag(db_session):
    user = create_test_user(db_session, "lab_dash_u2", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="DashB")
    ex = _examen(db_session, "B")
    param = _parametre(db_session, ex)
    repo = LabRepository(db_session)

    avant = repo.get_advanced_stats("month")["critical"]
    r = _resultat(db_session, pid, ex, "pending")
    _detail(db_session, r, param, flagged=False)

    assert repo.get_advanced_stats("month")["critical"] == avant


def test_en_attente_inclut_analyzed(db_session):
    user = create_test_user(db_session, "lab_dash_u3", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="DashC")
    ex = _examen(db_session, "C")
    repo = LabRepository(db_session)

    avant = repo.get_advanced_stats("month")["pending"]
    _resultat(db_session, pid, ex, "analyzed")
    assert repo.get_advanced_stats("month")["pending"] == avant + 1


def test_activite_totale_compte_les_dossiers_crees_sur_la_periode(db_session):
    user = create_test_user(db_session, "lab_dash_u4", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="DashD")
    ex = _examen(db_session, "D")
    repo = LabRepository(db_session)

    avant = repo.get_advanced_stats("month")
    _resultat(db_session, pid, ex, "completed")
    apres = repo.get_advanced_stats("month")

    # +1 dossier cree ; "pending" (stock) ne bouge pas, contrairement a
    # l'ancienne definition completed + pending.
    assert apres["total_month"] == avant["total_month"] + 1
    assert apres["pending"] == avant["pending"]


def test_dernieres_entrees_ne_contiennent_que_des_dossiers_a_traiter(db_session):
    user = create_test_user(db_session, "lab_dash_u5", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="Jeanne")
    ex = _examen(db_session, "E")
    repo = LabRepository(db_session)

    en_attente = _resultat(db_session, pid, ex, "pending")
    _resultat(db_session, pid, ex, "completed")

    items = repo.get_advanced_stats("month")["recent_pending"]
    ids = {i["id"] for i in items}
    assert en_attente.result_id in ids
    statuts = {db_session.get(LabResult, i["id"]).status for i in items}
    assert statuts <= {"pending", "partial", "analyzed"}
    mine = next(i for i in items if i["id"] == en_attente.result_id)
    assert mine["patient_name"] == "Patient Jeanne"  # meme forme partout : Nom Prenom


def test_historique_patient_expose_nb_anormaux(db_session):
    user = create_test_user(db_session, "lab_dash_u6", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="DashF")
    ex = _examen(db_session, "F")
    param = _parametre(db_session, ex)
    avec = _resultat(db_session, pid, ex, "completed")
    _detail(db_session, avec, param, flagged=True)
    _detail(db_session, avec, param, flagged=True)
    _detail(db_session, avec, param, flagged=False)
    sans = _resultat(db_session, pid, ex, "completed")
    _detail(db_session, sans, param, flagged=False)

    ctrl = LabController(repo=LabRepository(db_session), current_user=user)
    par_id = {h["result_id"]: h for h in ctrl.get_patient_lab_history(pid)}

    assert par_id[avec.result_id]["nb_anormaux"] == 2
    assert par_id[sans.result_id]["nb_anormaux"] == 0


def test_detail_resultat_expose_date_examen_et_prescripteur(db_session):
    user = create_test_user(db_session, "lab_dash_u7", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="DashG")
    ex = _examen(db_session, "G")
    r = _resultat(db_session, pid, ex, "completed")
    r.prescribed_by_name = "Dr Test"
    db_session.flush()
    db_session.refresh(r)

    ctrl = LabController(repo=LabRepository(db_session), current_user=user)
    detail = ctrl.get_result_detail(r.result_id)

    assert detail["test_date"] is not None
    assert detail["medecin_prescripteur"] == "Dr Test"


def test_historique_pagine_renvoie_une_date_iso(db_session):
    user = create_test_user(db_session, "lab_dash_u8", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="DashH")
    ex = _examen(db_session, "H")
    r = _resultat(db_session, pid, ex, "completed")
    db_session.refresh(r)

    ctrl = LabController(repo=LabRepository(db_session), current_user=user)
    page = ctrl.get_paginated_results(page=1, limit=50)
    item = next(i for i in page["items"] if i["result_id"] == r.result_id)

    # Le frontend (dayjs) ne sait pas relire "JJ/MM/AAAA" : sans ISO, la
    # date s'affichait "Invalid Date" (ou jour/mois inverses).
    assert item["test_date"] == r.test_date.isoformat()


def test_historique_filtre_cas_anormaux_et_periode(db_session):
    user = create_test_user(db_session, "lab_dash_u9", "admin", password=PASSWORD)
    pid, _ = create_test_patient(db_session, user, first_name="DashI")
    ex = _examen(db_session, "I")
    param = _parametre(db_session, ex)
    anormal = _resultat(db_session, pid, ex, "completed")
    _detail(db_session, anormal, param, flagged=True)
    normal = _resultat(db_session, pid, ex, "completed")
    _detail(db_session, normal, param, flagged=False)

    repo = LabRepository(db_session)
    total, rows = repo.get_paginated_history(limit=100, abnormal_only=True, period="month")
    ids = {r.result_id for r in rows}
    assert anormal.result_id in ids
    assert normal.result_id not in ids

    # Meme definition que la carte "Pathologiques" du dashboard.
    assert total == repo.get_advanced_stats("month")["critical"]

    # Sans le filtre, le dossier normal reste visible.
    _, tous = repo.get_paginated_history(limit=100)
    assert normal.result_id in {r.result_id for r in tous}
