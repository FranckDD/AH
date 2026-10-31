# tests/test_lab_result_snapshot.py
"""
Copie figee d'impression a la validation (migration 044, tache C3).

Le serveur ecrit lab_results.print_snapshot UNE fois, quand le resultat devient valide ; ensuite elle est
immuable, meme si le catalogue change ; une correction (amendement) en cree une nouvelle et archive l'ancienne.
"""
import json
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from models.lab import (Examen, LabResult, LabResultDetail, LabSnapshotImmutableError, Parametre, ReferenceRange)
from repositories.lab_repo import LabRepository, PatientBio
from tests.conftest import auth_headers, create_test_patient, create_test_user
from utils.business_time import business_now, business_today
from utils.lab_snapshot import SNAPSHOT_VERSION, build_print_snapshot, strip_pregnancy

PWD = "Correct123!"
TOP_KEYS = {"version", "exam", "patient", "pregnancy", "dossier", "parameters", "conclusion", "note"}
EXAM_KEYS = {"code", "title", "section", "method", "family", "signature_label", "sort_order", "fixed_notes"}
PATIENT_KEYS = {"age_label", "age_days", "sex"}
PARAM_KEYS = {"id", "label", "unit", "kind", "order", "value_text", "value_num", "flagged", "interpretation",
              "norm", "group", "norm_text", "norms"}
NORM_KEYS = {"text", "min", "max", "sex", "age_min_days", "age_max_days", "ga_min_weeks", "ga_max_weeks"}


def _catalogue(db, tag):
    ex = Examen(code=f"SN-{uuid.uuid4().hex[:8]}", nom=f"Glycemie {tag}", categorie="Bio", prix=1000,
                section="BIOCHIMIE", method="Enzymatique", layout_family="table", signature_label="Dr X",
                print_title="GLYCEMIE A JEUN", sort_order=7)
    db.add(ex)
    db.flush()
    p1 = Parametre(examen_id=ex.id, nom_parametre="Glycemie", unite="g/L", type_valeur="numeric",
                   input_type="numeric", ordre=1, print_label="Glycemie a jeun")
    p2 = Parametre(examen_id=ex.id, nom_parametre="Aspect", unite="", type_valeur="text", input_type="text",
                   ordre=2, result_kind="text")
    db.add_all([p1, p2])
    db.flush()
    db.add_all([
        ReferenceRange(parametre_id=p1.id, sexe="X", age_min_days=0, age_max_days=28,
                       valeur_min=Decimal("2.0"), valeur_max=Decimal("4.5")),
        ReferenceRange(parametre_id=p1.id, sexe="X", age_min_days=6570, age_max_days=None,
                       valeur_min=Decimal("0.70"), valeur_max=Decimal("1.10")),
    ])
    db.flush()
    return ex, p1, p2


def _result(db, tag, birth=None, status="pending", pregnancy=None, ex_p=None, user=None):
    lab = user or create_test_user(db, f"sn_lab_{tag}", "laborantin", password=PWD)
    pid, _ = create_test_patient(db, lab, first_name=f"Snap{tag}", last_name="Identite", gender="F",
                                 **({"birth_date": birth} if birth else {}))
    ex, p1, p2 = ex_p or _catalogue(db, tag)
    kw = {}
    if pregnancy:
        kw = {"pregnancy_status_at_result": pregnancy[0], "gestational_age_weeks": pregnancy[1]}
    r = LabResult(patient_id=pid, test_type=ex.nom, status=status, examen_id=ex.id, note=None,
                  code_lab_patient=f"LAB-SN-{uuid.uuid4().hex[:8]}", test_date=business_now(), **kw)
    db.add(r)
    db.flush()
    d1 = LabResultDetail(result_id=r.result_id, parametre_id=p1.id, valeur_text="", valeur_num=None, flagged=False)
    d2 = LabResultDetail(result_id=r.result_id, parametre_id=p2.id, valeur_text="", valeur_num=None, flagged=False)
    db.add_all([d1, d2])
    db.flush()
    return lab, r, (ex, p1, p2), (d1, d2)


def _validate(db, r, d1, d2, g="0.9", user_id=None, note=None, conclusion=None):
    repo = LabRepository(db)
    return repo.save_results_values(
        r.result_id, {d1.detail_id: {"valeur": g}, d2.detail_id: {"valeur": "Clair"}}, mark_completed=True,
        global_note=note, global_conclusion=conclusion, user_id=user_id)


def _client(api_client, username):
    client = api_client(auth_endpoints, lab_endpoints)
    return client, auth_headers(client, username, PWD)


# ------------------------------------------------------------------ forme

def test_copie_creee_a_la_validation_avec_la_forme_exacte(db_session):
    lab, r, (ex, p1, p2), (d1, d2) = _result(db_session, "f1")
    assert r.print_snapshot is None
    _validate(db_session, r, d1, d2, note="NB test", conclusion="Conclusion test", user_id=lab.user_id)
    db_session.expire_all()
    r = db_session.get(LabResult, r.result_id)
    s = r.print_snapshot
    assert set(s) == TOP_KEYS
    assert s["version"] == SNAPSHOT_VERSION == 2
    assert s["exam"] == {"code": ex.code, "title": "GLYCEMIE A JEUN", "section": "BIOCHIMIE", "method": "Enzymatique",
                         "family": "table", "signature_label": "Dr X", "sort_order": 7, "fixed_notes": []}
    assert set(s["patient"]) == PATIENT_KEYS and s["patient"]["sex"] == "F"
    assert s["patient"]["age_days"] > 6570 and s["patient"]["age_label"]
    assert s["pregnancy"] is None and s["dossier"] is not None   # numero attribue a la validation si absent
    assert [p["label"] for p in s["parameters"]] == ["Glycemie a jeun", "Aspect"]
    g, a = s["parameters"]
    assert set(g) == PARAM_KEYS and set(g["norm"]) == NORM_KEYS
    assert g["id"] == p1.id and g["unit"] == "g/L" and g["kind"] == "numeric" and g["order"] == 1
    assert g["value_text"] == "0.9" and g["value_num"] == 0.9 and g["flagged"] is False
    assert g["interpretation"] == "Normal" and g["group"] is None
    assert g["norm"]["text"] == "0.7 - 1.1" and g["norm"]["min"] == 0.7 and g["norm"]["max"] == 1.1
    assert g["norm"]["age_min_days"] == 6570 and g["norm"]["age_max_days"] is None and g["norm"]["sex"] == "X"
    assert a["kind"] == "text" and a["value_text"] == "Clair" and a["value_num"] is None and a["norm"] is None
    assert s["conclusion"] == "Conclusion test" and s["note"] == "NB test"
    assert r.print_snapshot_at is not None and r.print_snapshot_by == lab.user_id
    assert r.print_snapshot_history is None
    json.dumps(s)  # serialisable


def test_copie_sans_identite_du_patient(db_session):
    lab, r, _, (d1, d2) = _result(db_session, "id1")
    _validate(db_session, r, d1, d2)
    dumped = json.dumps(r.print_snapshot).lower()
    for forbidden in ("snapid1", "identite", "first_name", "last_name", "birth", "phone", "telephone", "nom"):
        assert forbidden not in dumped


def test_json_serialisable_decimaux_et_dates(db_session):
    lab, r, (ex, p1, p2), (d1, d2) = _result(db_session, "js1")
    d1.valeur_num = Decimal("0.90")
    d1.valeur_text = "0.90"
    s = build_print_snapshot(r, ex, [d1, d2], PatientBio(9000, "F", None, "24 ans"))
    assert json.loads(json.dumps(s)) == s


# ------------------------------------------------------------------ immuabilite

def test_catalogue_modifie_apres_validation_ne_change_pas_la_copie(db_session):
    lab, r, (ex, p1, p2), (d1, d2) = _result(db_session, "im1")
    _validate(db_session, r, d1, d2)
    before = json.loads(json.dumps(r.print_snapshot))
    p1.print_label = "Autre libelle"
    p1.nom_parametre = "Renomme"
    p1.unite = "mmol/L"
    p1.ordre = 9
    ex.layout_family = "boxed"
    ex.signature_label = "Dr Autre"
    ex.print_title = "AUTRE TITRE"
    ex.method = "Autre"
    for rr in db_session.query(ReferenceRange).filter_by(parametre_id=p1.id):
        rr.valeur_min, rr.valeur_max = Decimal("5"), Decimal("9")
    db_session.flush()
    db_session.expire_all()
    assert db_session.get(LabResult, r.result_id).print_snapshot == before


def test_ecriture_directe_sur_une_copie_existante_leve(db_session):
    lab, r, _, (d1, d2) = _result(db_session, "im2")
    _validate(db_session, r, d1, d2)
    r.print_snapshot = {"version": 1, "pirate": True}
    with pytest.raises(LabSnapshotImmutableError):
        db_session.flush()
    db_session.rollback()


def test_seconde_validation_n_ecrase_pas_la_copie(db_session):
    lab, r, _, (d1, d2) = _result(db_session, "im3")
    _validate(db_session, r, d1, d2)
    first = json.loads(json.dumps(r.print_snapshot))
    at = r.print_snapshot_at
    repo = LabRepository(db_session)
    assert repo.freeze_print_snapshot(r) is False  # appel direct : rien
    _validate(db_session, r, d1, d2)  # rejeu identique : sans effet
    assert r.print_snapshot == first and r.print_snapshot_at == at


def test_resultat_ancien_sans_copie_reste_intact(db_session):
    lab, r, _, (d1, d2) = _result(db_session, "old1", status="completed")
    db_session.expire_all()
    r = db_session.get(LabResult, r.result_id)
    assert r.print_snapshot is None and r.print_snapshot_at is None and r.print_snapshot_history is None
    r.note = "autre champ"
    db_session.flush()  # un resultat sans copie reste modifiable ailleurs
    assert r.print_snapshot is None


# ------------------------------------------------------------------ amendement

def test_amendement_cree_une_nouvelle_copie_et_garde_l_ancienne(db_session):
    lab, r, (ex, p1, p2), (d1, d2) = _result(db_session, "am1")
    _validate(db_session, r, d1, d2, conclusion="Avant")
    old = json.loads(json.dumps(r.print_snapshot))
    old_at = r.print_snapshot_at
    p1.print_label = "Nouveau libelle"  # change apres validation: n'apparait qu'avec la nouvelle copie
    db_session.flush()
    repo = LabRepository(db_session)
    editor = create_test_user(db_session, "sn_edit_am1", "laborantin", password=PWD)
    repo.amend_result(r.result_id, {d1.detail_id: {"valeur": "1.5"}}, None, "Erreur de saisie",
                      user_id=editor.user_id, user_name="Editeur", global_conclusion="Apres")
    db_session.expire_all()
    r = db_session.get(LabResult, r.result_id)
    new = r.print_snapshot
    assert new != old
    assert new["parameters"][0]["label"] == "Nouveau libelle" and new["parameters"][0]["value_text"] == "1.5"
    assert new["parameters"][0]["flagged"] is True and new["conclusion"] == "Apres"
    assert r.print_snapshot_by == editor.user_id and r.print_snapshot_at >= old_at
    hist = r.print_snapshot_history
    assert len(hist) == 1 and hist[0]["snapshot"] == old
    assert hist[0]["replaced_by"] == editor.user_id and hist[0]["replaced_by_name"] == "Editeur"
    assert hist[0]["reason"] == "Erreur de saisie" and hist[0]["replaced_at"]
    # second amendement : 2 elements, ordre chronologique
    repo.amend_result(r.result_id, {d1.detail_id: {"valeur": "0.8"}}, None, "Re-correction",
                      user_id=editor.user_id, user_name="Editeur")
    db_session.expire_all()
    r = db_session.get(LabResult, r.result_id)
    assert len(r.print_snapshot_history) == 2 and r.print_snapshot_history[1]["snapshot"] == new
    # la garde est de nouveau active apres l'amendement
    r.print_snapshot = {"x": 1}
    with pytest.raises(LabSnapshotImmutableError):
        db_session.flush()
    db_session.rollback()


def test_amender_un_ancien_resultat_sans_copie_en_cree_une_premiere(db_session):
    lab, r, _, (d1, d2) = _result(db_session, "am2", status="completed")
    LabRepository(db_session).amend_result(r.result_id, {d1.detail_id: {"valeur": "1.0"}}, None, "Motif",
                                           user_id=lab.user_id, user_name="L")
    db_session.expire_all()
    r = db_session.get(LabResult, r.result_id)
    assert r.print_snapshot is not None and not r.print_snapshot_history


# ------------------------------------------------------------------ normes

def test_nouveau_ne_et_adulte_n_ont_pas_la_meme_norme(db_session):
    shared = None
    lab, r_ad, shared, (a1, a2) = _result(db_session, "n1")
    _, r_nb, _, (b1, b2) = _result(db_session, "n2", birth=business_today() - timedelta(days=5), ex_p=shared)
    _validate(db_session, r_ad, a1, a2)
    _validate(db_session, r_nb, b1, b2, g="3.0")
    n_ad = r_ad.print_snapshot["parameters"][0]["norm"]
    n_nb = r_nb.print_snapshot["parameters"][0]["norm"]
    assert (n_ad["min"], n_ad["max"]) == (0.7, 1.1)
    assert (n_nb["min"], n_nb["max"]) == (2.0, 4.5) and n_nb["age_max_days"] == 28
    assert r_nb.print_snapshot["patient"]["age_days"] == 5
    assert r_nb.print_snapshot["parameters"][0]["flagged"] is False


# ------------------------------------------------------------------ grossesse

def test_cle_pregnancy_seulement_quand_il_y_a_une_donnee(db_session):
    _, r0, _, (a1, a2) = _result(db_session, "p0")
    _validate(db_session, r0, a1, a2)
    assert "pregnancy" in r0.print_snapshot and r0.print_snapshot["pregnancy"] is None
    _, r1, _, (b1, b2) = _result(db_session, "p1", pregnancy=("enceinte", 28))
    _validate(db_session, r1, b1, b2)
    assert r1.print_snapshot["pregnancy"] == {"status_at_result": "enceinte", "gestational_age_weeks": 28}
    assert strip_pregnancy(r1.print_snapshot)["pregnancy"] is None
    assert r1.print_snapshot["pregnancy"] is not None  # l'original n'est pas modifie
    _, r2, _, (c1, c2) = _result(db_session, "p2", pregnancy=("non_enceinte", None))
    _validate(db_session, r2, c1, c2)
    assert r2.print_snapshot["pregnancy"] == {"status_at_result": "non_enceinte", "gestational_age_weeks": None}


def test_dossier_dans_la_copie_quand_attribue(db_session):
    _, r, _, (d1, d2) = _result(db_session, "dos1")
    r.dossier_year, r.dossier_counter, r.dossier_rank = None, None, None
    _validate(db_session, r, d1, d2)
    assert r.print_snapshot["dossier"] is not None   # politique : attribue a la validation
    s = build_print_snapshot(type("R", (), {"dossier_year": 2026, "dossier_counter": 12, "dossier_rank": 3,
                                            "conclusion": None, "note": None})(),
                             r.examen, [], PatientBio(None, "X", None, None))
    assert s["dossier"] == {"year": 2026, "counter": 12, "rank": 3} and s["patient"]["age_days"] is None


# ------------------------------------------------------------------ API : conclusion / NB

def test_conclusion_et_nb_acceptes_et_stockes_par_l_api(db_session, api_client):
    lab, r, _, (d1, d2) = _result(db_session, "api1")
    client, h = _client(api_client, lab.username)
    resp = client.put(f"/labo/results/{r.result_id}/values", headers=h, json={
        "values": {str(d1.detail_id): {"valeur": 0.9}}, "completed": True, "note": "NB ici", "conclusion": "Rien a signaler"})
    assert resp.status_code == 200, resp.text
    db_session.expire_all()
    r = db_session.get(LabResult, r.result_id)
    assert r.conclusion == "Rien a signaler" and r.note == "NB ici"
    assert r.print_snapshot["conclusion"] == "Rien a signaler" and r.print_snapshot["note"] == "NB ici"
    assert r.print_snapshot_by == lab.user_id


def test_conclusion_bornee_a_5000_caracteres(db_session, api_client):
    lab, r, _, (d1, d2) = _result(db_session, "api2")
    client, h = _client(api_client, lab.username)
    ok = client.put(f"/labo/results/{r.result_id}/values", headers=h,
                    json={"values": {}, "completed": False, "conclusion": "x" * 5000})
    assert ok.status_code == 200, ok.text
    bad = client.put(f"/labo/results/{r.result_id}/values", headers=h,
                     json={"values": {}, "completed": False, "conclusion": "x" * 5001})
    assert bad.status_code == 422
    db_session.expire_all()
    assert len(db_session.get(LabResult, r.result_id).conclusion) == 5000


def test_conclusion_via_la_correction_et_modifier_la_conclusion_d_un_valide_est_refuse(db_session, api_client):
    lab, r, _, (d1, d2) = _result(db_session, "api3")
    client, h = _client(api_client, lab.username)
    assert client.put(f"/labo/results/{r.result_id}/values", headers=h, json={
        "values": {str(d1.detail_id): {"valeur": 0.9}}, "completed": True, "conclusion": "C1"}).status_code == 200
    locked = client.put(f"/labo/results/{r.result_id}/values", headers=h,
                        json={"values": {}, "completed": True, "conclusion": "C2"})
    assert locked.status_code == 409
    too_long = client.post(f"/labo/results/{r.result_id}/amend", headers=h,
                           json={"reason": "m", "values": {}, "conclusion": "x" * 5001})
    assert too_long.status_code == 422
    ok = client.post(f"/labo/results/{r.result_id}/amend", headers=h,
                     json={"reason": "m", "values": {}, "conclusion": "C3"})
    assert ok.status_code == 200, ok.text
    db_session.expire_all()
    r = db_session.get(LabResult, r.result_id)
    assert r.conclusion == "C3" and r.print_snapshot["conclusion"] == "C3"
    assert r.print_snapshot_history[0]["snapshot"]["conclusion"] == "C1"


# ------------------------------------------------------------------ chaque chemin de validation

def _path_repo(db, api_client):
    lab, r, _, (d1, d2) = _result(db, "pa_repo")
    _validate(db, r, d1, d2, user_id=lab.user_id)
    return r


def _path_api_detail_id(db, api_client):
    lab, r, _, (d1, d2) = _result(db, "pa_api")
    client, h = _client(api_client, lab.username)
    assert client.put(f"/labo/results/{r.result_id}/values", headers=h, json={
        "values": {str(d1.detail_id): {"valeur": 0.9}}, "completed": True}).status_code == 200
    return r


def _path_api_offline_uuid_negative_key(db, api_client):
    """Dossier cree hors ligne : segment d'URL = uuid local, cle de valeur = -parametre_id."""
    lab, r, (ex, p1, p2), (d1, d2) = _result(db, "pa_off")
    client, h = _client(api_client, lab.username)
    resp = client.put(f"/labo/results/{r.uuid}/values", headers=h, json={
        "values": {str(-p1.id): {"valeur": 0.9}}, "completed": True})
    assert resp.status_code == 200, resp.text
    return r


def _path_created_completed(db, api_client):
    lab, _, (ex, p1, p2), _ = _result(db, "pa_cr")
    pid, _ = create_test_patient(db, lab, first_name="SnapCr", last_name="X")
    res = LabRepository(db).create_lab_result({
        "patient_id": pid, "test_type": ex.nom, "examen_id": ex.id, "status": "completed",
        "details": [{"parametre_id": p1.id, "valeur_text": "0.9", "valeur_num": Decimal("0.9"), "flagged": False}],
        "created_by": lab.user_id})
    return res


def _path_amend(db, api_client):
    lab, r, _, (d1, d2) = _result(db, "pa_am", status="completed")
    client, h = _client(api_client, lab.username)
    resp = client.post(f"/labo/results/{r.result_id}/amend", headers=h, json={
        "reason": "m", "values": {str(d1.detail_id): {"valeur": 0.9}}})
    assert resp.status_code == 200, resp.text
    return r


@pytest.mark.parametrize("path", [_path_repo, _path_api_detail_id, _path_api_offline_uuid_negative_key,
                                  _path_created_completed, _path_amend])
def test_chaque_chemin_de_validation_pose_la_copie(db_session, api_client, path):
    r = path(db_session, api_client)
    db_session.expire_all()
    r = db_session.get(LabResult, r.result_id)
    assert r.status == "completed"
    assert r.print_snapshot is not None and r.print_snapshot["version"] == 2
    assert r.print_snapshot["parameters"] and r.print_snapshot_at is not None


def test_brouillon_ne_pose_pas_de_copie(db_session, api_client):
    lab, r, _, (d1, d2) = _result(db_session, "dr1")
    client, h = _client(api_client, lab.username)
    assert client.put(f"/labo/results/{r.result_id}/values", headers=h, json={
        "values": {str(d1.detail_id): {"valeur": 0.9}}, "completed": False}).status_code == 200
    db_session.expire_all()
    r = db_session.get(LabResult, r.result_id)
    assert r.status == "partial" and r.print_snapshot is None
