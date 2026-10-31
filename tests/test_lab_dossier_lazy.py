# tests/test_lab_dossier_lazy.py
"""Politique : l'impression n'est JAMAIS bloquee par un numero de dossier manquant. Tout chemin de creation
attribue le numero ; un ancien resultat sans numero le recoit a la demande (validation, impression), tout son lot
avec lui ; script de rattrapage. Patients inventes uniquement."""
import threading
import uuid
from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from api_backend.backend_app.database import engine
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from models.lab import Examen, LabResult
from tests.conftest import auth_headers, create_test_user
from tests.test_lab_pdf_routes import _client, _exam, _setup, _text, _validated
from utils.lab_dossier import (DossierNotAssignedError, ensure_dossier_assigned, format_dossier, result_dossier)

PWD = "Correct123!"


@pytest.fixture(scope="module")
def backfill_script():
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts",
                        "backfill_lab_dossier_numbers.py")
    spec = importlib.util.spec_from_file_location("backfill_lab_dossier_numbers", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _lab_client(db, api_client):
    lab = create_test_user(db, f"dl_{uuid.uuid4().hex[:6]}", "laborantin", password=PWD)
    lab.postgres_role = "app_laborantin"
    db.flush()
    client = api_client(auth_endpoints, lab_endpoints)
    return client, auth_headers(client, lab.username, PWD)


def _plain_exam(db):
    ex = Examen(code=f"DL-{uuid.uuid4().hex[:8]}", nom="Examen lazy", categorie="Bio", prix=0)
    db.add(ex)
    db.flush()
    return ex


def _ext(nom, **extra):
    info = {"nom": nom, "prenom": "", "age": 30, "sexe": "M", "telephone": ""}
    info.update(extra)
    return info


def _legacy(db, *, patient_id=None, ext=None, batch=None, when=None, status="completed"):
    """Resultat ancien, sans aucun numero de dossier."""
    r = LabResult(patient_id=patient_id, external_patient_info=ext, test_type="x", status=status,
                  batch_id=batch, test_date=when or datetime(2096, 3, 4, 10, 0),
                  code_lab_patient=f"LG-{uuid.uuid4().hex[:10]}")
    db.add(r)
    db.flush()
    return r


def _num(r):
    return (r.dossier_year, r.dossier_counter, r.dossier_rank)


def _post_batch(client, h, **body):
    resp = client.post("/labo/results/batch", headers=h, json=body)
    assert resp.status_code == 201, resp.text
    return resp


# ------------------------------------------------------------------ creation : chaque chemin numerote

def test_every_creation_path_ends_with_a_number(db_session, api_client):
    client, h = _lab_client(db_session, api_client)
    ex = _plain_exam(db_session)
    lab, pid = _setup(db_session, "cp")

    b_ext = _post_batch(client, h, external_patient_info=_ext("Lot Ext"), batch_uuid=str(uuid.uuid4()),
                        results=[{"uuid": str(uuid.uuid4()), "examen_id": ex.id}]).json()
    b_int = _post_batch(client, h, patient_id=pid, batch_uuid=str(uuid.uuid4()),
                        results=[{"uuid": str(uuid.uuid4()), "examen_id": ex.id}]).json()
    s_ext = client.post("/labo/results", headers=h, json={"examen_id": ex.id, "external_patient_info": _ext("Seul Ext")})
    s_int = client.post("/labo/results", headers=h, json={"examen_id": ex.id, "patient_id": pid})
    assert s_ext.status_code == 201 and s_int.status_code == 201, (s_ext.text, s_int.text)
    for body in (b_ext, b_int):
        assert body["dossier"] and body["dossier_counter"] and body["dossier_rank"]
    assert s_ext.json()["dossier"] and s_int.json()["dossier"]

    db_session.expire_all()
    rows = db_session.query(LabResult).filter(LabResult.examen_id == ex.id).all()
    assert len(rows) == 4
    assert all(result_dossier(r) is not None and r.patient_key for r in rows)


def test_single_route_same_patient_same_day_shares_number_and_externals_do_not(db_session, api_client):
    client, h = _lab_client(db_session, api_client)
    ex = _plain_exam(db_session)
    lab, pid = _setup(db_session, "sp")
    a = client.post("/labo/results", headers=h, json={"examen_id": ex.id, "patient_id": pid}).json()
    b = client.post("/labo/results", headers=h, json={"examen_id": ex.id, "patient_id": pid}).json()
    assert a["dossier"] == b["dossier"]
    e1 = client.post("/labo/results", headers=h, json={"examen_id": ex.id, "external_patient_info": _ext("Meme Nom")}).json()
    e2 = client.post("/labo/results", headers=h, json={"examen_id": ex.id, "external_patient_info": _ext("Meme Nom")}).json()
    assert e1["dossier"] != e2["dossier"]


def test_batch_extra_exam_for_a_legacy_batch_gives_the_whole_batch_one_number(db_session, api_client):
    """Un examen ajoute a une reception ancienne (frere sans numero) : tout le lot partage le meme numero."""
    client, h = _lab_client(db_session, api_client)
    ex = _plain_exam(db_session)
    batch, bu = uuid.uuid4(), str(uuid.uuid4())
    old = _legacy(db_session, ext=_ext("Ancien Lot"), batch=batch)
    old.batch_uuid = bu
    db_session.flush()
    resp = _post_batch(client, h, external_patient_info=_ext("Ancien Lot"), batch_uuid=bu,
                       results=[{"uuid": str(uuid.uuid4()), "examen_id": ex.id}])
    db_session.expire_all()
    rows = db_session.query(LabResult).filter(LabResult.batch_id == batch).all()
    assert len(rows) == 2 and len({_num(r) for r in rows}) == 1 and _num(rows[0])[0] is not None
    assert resp.json()["dossier_counter"] == rows[0].dossier_counter


# ------------------------------------------------------------------ attribution a la demande

def test_ensure_assigns_whole_batch_with_the_oldest_day(db_session):
    batch = uuid.uuid4()
    a = _legacy(db_session, ext=_ext("Lot Legacy"), batch=batch, when=datetime(2096, 3, 4, 9, 0))
    b = _legacy(db_session, ext=_ext("Lot Legacy"), batch=batch, when=datetime(2096, 3, 9, 15, 0))
    n = ensure_dossier_assigned(a)
    db_session.expire_all()
    assert _num(a) == _num(b) == tuple(n) and a.patient_key == b.patient_key
    day = db_session.execute(text("SELECT day FROM lab_dossier_ranks WHERE year=:y AND counter=:c AND rank=:r"),
                             {"y": n.year, "c": n.counter, "r": n.rank}).scalar()
    assert str(day) == "2096-03-04"
    assert ensure_dossier_assigned(b) == n                       # idempotent, deja attribue


def test_same_patient_two_exams_same_day_share_and_different_externals_differ(db_session):
    lab, pid = _setup(db_session, "lz")
    p1 = _legacy(db_session, patient_id=pid, when=datetime(2096, 5, 6, 8, 0))
    p2 = _legacy(db_session, patient_id=pid, when=datetime(2096, 5, 6, 17, 0))
    assert ensure_dossier_assigned(p1) == ensure_dossier_assigned(p2)
    e1 = _legacy(db_session, ext=_ext("Homonyme"), batch=uuid.uuid4(), when=datetime(2096, 5, 6, 9, 0))
    e2 = _legacy(db_session, ext=_ext("Homonyme"), batch=uuid.uuid4(), when=datetime(2096, 5, 6, 9, 5))
    n1, n2 = ensure_dossier_assigned(e1), ensure_dossier_assigned(e2)
    assert n1.counter == n2.counter and n1.rank != n2.rank


def test_result_without_identity_or_batch_still_gets_a_number(db_session):
    r = _legacy(db_session)
    assert ensure_dossier_assigned(r) is not None and r.patient_key.startswith("r:")


def test_ensure_raises_only_when_assignment_itself_fails(db_session, monkeypatch):
    r = _legacy(db_session, ext=_ext("Echec"))
    import utils.lab_dossier as ld

    def boom(s, res):
        raise RuntimeError("boom")
    monkeypatch.setattr(ld, "assign_missing_dossier", boom)
    with pytest.raises(DossierNotAssignedError):
        ensure_dossier_assigned(r)


# ------------------------------------------------------------------ impression

def _legacy_validated(db, tag, *, batch=None):
    lab, pid = _setup(db, tag)
    ex, params = _exam(db, tag, "table", [f"Param {tag}"])
    r, _ = _validated(db, pid, lab, ex, params, batch=batch)
    return lab, r


def _erase_number(db, *results):
    ids = [r.result_id for r in results]
    db.execute(text("UPDATE lab_results SET dossier_year=NULL, dossier_counter=NULL, dossier_rank=NULL, "
                    "patient_key=NULL WHERE result_id = ANY(:ids)"), {"ids": ids})
    db.expire_all()


def test_print_assigns_a_missing_number_never_409_and_reprint_is_identical(db_session, api_client):
    batch = uuid.uuid4()
    lab, r1 = _legacy_validated(db_session, "pa", batch=batch)
    ex2, params2 = _exam(db_session, "pb", "table", ["Param pb"])
    r2 = _validated(db_session, r1.patient_id, lab, ex2, params2, batch=batch)[0]
    _erase_number(db_session, r1, r2)
    client, headers = _client(api_client, "pr_pa")

    resp = client.get(f"/labo/results/{r1.result_id}/pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    db_session.expire_all()
    a, b = db_session.get(LabResult, r1.result_id), db_session.get(LabResult, r2.result_id)
    assert result_dossier(a) is not None and _num(a) == _num(b)          # tout le lot, meme numero
    day = db_session.execute(text("SELECT day FROM lab_dossier_ranks WHERE year=:y AND counter=:c AND rank=:r"),
                             {"y": a.dossier_year, "c": a.dossier_counter, "r": a.dossier_rank}).scalar()
    assert format_dossier(result_dossier(a), day) in _text(resp.content)  # numero imprime == numero stocke

    again = client.get(f"/labo/results/{r1.result_id}/pdf", headers=headers)
    batch_pdf = client.get(f"/labo/batch/{batch}/pdf", headers=headers)
    assert again.status_code == 200 and batch_pdf.status_code == 200
    assert _text(again.content) == _text(resp.content)                   # reimpression identique
    db_session.expire_all()
    assert _num(db_session.get(LabResult, r1.result_id)) == _num(a)      # rien de re-attribue


def test_print_falls_back_to_reference_code_when_assignment_fails(db_session, api_client, monkeypatch):
    lab, r = _legacy_validated(db_session, "fb")
    _erase_number(db_session, r)
    import utils.lab_dossier as ld

    def boom(s, res):
        raise RuntimeError("boom")
    monkeypatch.setattr(ld, "assign_missing_dossier", boom)
    client, headers = _client(api_client, "pr_fb")
    resp = client.get(f"/labo/results/{r.result_id}/pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    assert r.code_lab_patient in _text(resp.content)
    db_session.expire_all()
    assert result_dossier(db_session.get(LabResult, r.result_id)) is None


def test_validation_assigns_the_number_of_a_legacy_result(db_session):
    lab, pid = _setup(db_session, "vl")
    ex, params = _exam(db_session, "vl", "table", ["Param vl"])
    r, _ = _validated(db_session, pid, lab, ex, params, dossier=False)
    assert result_dossier(r) is not None and r.print_snapshot["dossier"] is not None


# ------------------------------------------------------------------ script de rattrapage

def test_backfill_dry_run_then_apply(db_session, backfill_script):
    batch = uuid.uuid4()
    a = _legacy(db_session, ext=_ext("Script"), batch=batch, when=datetime(2096, 7, 1, 9, 0))
    b = _legacy(db_session, ext=_ext("Script"), batch=batch, when=datetime(2096, 7, 1, 9, 30))
    solo = _legacy(db_session, ext=_ext("Seul Script"), when=datetime(2096, 7, 2, 9, 0))
    done = _legacy(db_session, ext=_ext("Deja"), when=datetime(2096, 7, 3, 9, 0))
    keep = ensure_dossier_assigned(done)
    before = backfill_script._count_missing(db_session)

    dry = backfill_script.backfill(db_session, apply=False)
    db_session.expire_all()
    assert dry["missing_before"] == before and dry["missing_after"] == 0
    assert a.dossier_year is None and solo.dossier_year is None          # simulation : rien d'ecrit

    real = backfill_script.backfill(db_session, apply=True)
    db_session.expire_all()
    assert real["assigned_rows"] == before and real["missing_after"] == 0
    assert _num(a) == _num(b) and _num(solo) != _num(a)
    assert result_dossier(done) == keep                                   # jamais touche
    assert backfill_script.backfill(db_session, apply=True)["assigned_rows"] == 0   # idempotent


# ------------------------------------------------------------------ concurrence

def test_concurrent_lazy_assignment_does_not_duplicate():
    year = 2098
    batch = uuid.uuid4()

    def cleanup():
        with engine.begin() as c:
            c.execute(text("DELETE FROM lab_results WHERE code_lab_patient LIKE 'LGC-%'"))
            c.execute(text("DELETE FROM lab_dossier_ranks WHERE year = :y"), {"y": year})
            c.execute(text("DELETE FROM lab_dossier_days WHERE year = :y"), {"y": year})

    cleanup()
    try:
        with Session(engine) as s:
            for i in range(4):
                s.add(LabResult(external_patient_info=_ext("Conc"), test_type="x", status="completed", batch_id=batch,
                                test_date=datetime(year, 2, 3, 10, i), code_lab_patient=f"LGC-{uuid.uuid4().hex[:10]}"))
            for i in range(3):   # trois autres lots, un patient chacun
                s.add(LabResult(external_patient_info=_ext(f"Conc{i}"), test_type="x", status="completed",
                                batch_id=uuid.uuid4(), test_date=datetime(year, 2, 3, 11, i),
                                code_lab_patient=f"LGC-{uuid.uuid4().hex[:10]}"))
            s.commit()
            ids = [r.result_id for r in s.query(LabResult).filter(LabResult.code_lab_patient.like("LGC-%")).all()]
        out, errors = [], []

        def work(rid):
            s = Session(engine)
            try:
                r = s.get(LabResult, rid)
                n = ensure_dossier_assigned(r, commit=True)
                out.append((r.batch_id, tuple(n)))
            except Exception as e:  # pragma: no cover
                errors.append(e)
            finally:
                s.close()

        threads = [threading.Thread(target=work, args=(i,)) for i in ids]
        [t.start() for t in threads]
        [t.join(timeout=30) for t in threads]
        assert not errors, errors
        per_batch = {}
        for b, n in out:
            per_batch.setdefault(b, set()).add(n)
        assert len(per_batch) == 4 and all(len(v) == 1 for v in per_batch.values())
        assert sorted(next(iter(v))[2] for v in per_batch.values()) == [1, 2, 3, 4]
        assert len({next(iter(v))[1] for v in per_batch.values()}) == 1       # meme jour, meme compteur
    finally:
        cleanup()
        with engine.connect() as c:
            left = c.execute(text("SELECT (SELECT count(*) FROM lab_dossier_ranks WHERE year=:y)+"
                                  "(SELECT count(*) FROM lab_results WHERE code_lab_patient LIKE 'LGC-%')"),
                             {"y": year}).scalar()
        assert left == 0
