# tests/test_lab_dossier_number.py
"""Numero de dossier du laboratoire NNN/NN du JJ/MM/AAAA (patients inventes uniquement).

Les annees de test (2090+) n'existent pas dans la base de developpement : les compteurs repartent de 1."""
import threading
import uuid
from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from api_backend.backend_app.database import engine
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from models.lab import Examen, LabResult
from tests.conftest import create_test_user, auth_headers
from utils.business_time import business_now, business_today
from utils.lab_dossier import (
    DossierNotAssignedError, DossierNumber, assign_dossier, build_patient_key,
    dossier_labels, ensure_dossier_assigned, format_dossier,
)

PWD = "Correct123!"


def _key(n):
    return f"p:{900000 + n}"


def test_format_dossier_padding():
    assert format_dossier(DossierNumber(2026, 289, 2), date(2026, 10, 8)) == "289/02 du 08/10/2026"
    assert format_dossier(DossierNumber(2026, 1, 1), date(2026, 1, 2)) == "001/01 du 02/01/2026"
    assert format_dossier(DossierNumber(2026, 1000, 100), date(2026, 12, 31)) == "1000/100 du 31/12/2026"


def test_first_dossier_of_day_advances_counter(db_session):
    a = assign_dossier(db_session, _key(1), date(2091, 3, 1))
    b = assign_dossier(db_session, _key(2), date(2091, 3, 2))
    assert (a.counter, a.rank) == (1, 1)
    assert (b.counter, b.rank) == (2, 1)


def test_same_patient_same_day_shares_rank_and_counter(db_session):
    a = assign_dossier(db_session, _key(1), date(2091, 3, 1))
    again = assign_dossier(db_session, _key(1), date(2091, 3, 1))
    assert a == again == DossierNumber(2091, 1, 1)
    # le meme patient un autre jour : nouveau compteur, rang 1
    assert assign_dossier(db_session, _key(1), date(2091, 3, 2)) == DossierNumber(2091, 2, 1)


def test_second_patient_gets_next_rank(db_session):
    a = assign_dossier(db_session, _key(1), date(2091, 3, 1))
    b = assign_dossier(db_session, _key(2), date(2091, 3, 1))
    c = assign_dossier(db_session, _key(3), date(2091, 3, 1))
    assert (a.counter, a.rank) == (1, 1)
    assert (b.counter, b.rank) == (1, 2)
    assert (c.counter, c.rank) == (1, 3)


def test_no_registration_day_does_not_advance_counter(db_session):
    a = assign_dossier(db_session, _key(1), date(2091, 3, 1))
    # 2, 3 et 4 mars : aucune activite ; le 5 mars prend le numero suivant, pas +4
    b = assign_dossier(db_session, _key(2), date(2091, 3, 5))
    assert b.counter == a.counter + 1


def test_new_year_resets_counter_to_001(db_session):
    last = assign_dossier(db_session, _key(1), date(2091, 12, 31))
    assign_dossier(db_session, _key(2), date(2091, 12, 31))
    first = assign_dossier(db_session, _key(2), date(2092, 1, 1))
    assert last.counter == 1
    assert first == DossierNumber(2092, 1, 1)
    assert format_dossier(first, date(2092, 1, 1)) == "001/01 du 01/01/2092"


def test_rank_is_not_reused_after_a_result_is_deleted(db_session):
    """Le rang le plus eleve est porte par un resultat ; on le supprime, puis on enregistre un autre patient :
    il prend le rang SUIVANT (3), jamais le rang libere (2)."""
    ex = Examen(code=f"DN-{uuid.uuid4().hex[:8]}", nom="Examen dossier", categorie="Bio", prix=0)
    db_session.add(ex)
    db_session.flush()
    day = date(2091, 4, 1)
    assign_dossier(db_session, _key(1), day)                       # rang 1 (sans resultat)
    n2 = assign_dossier(db_session, _key(2), day)                  # rang 2, porte par un resultat
    assert n2.rank == 2
    r = LabResult(patient_id=None, external_patient_info={"nom": "X"}, test_type="x", status="pending",
                  examen_id=ex.id, code_lab_patient=f"DN-{uuid.uuid4().hex[:10]}",
                  dossier_year=n2.year, dossier_counter=n2.counter, dossier_rank=n2.rank, patient_key=_key(2))
    db_session.add(r)
    db_session.flush()
    db_session.delete(r)
    db_session.flush()
    assert db_session.query(LabResult).filter_by(dossier_year=n2.year, dossier_counter=n2.counter).count() == 0
    assert assign_dossier(db_session, _key(3), day) == DossierNumber(2091, 1, 3)


def test_rank_day_is_tied_to_its_counter_day(db_session):
    assign_dossier(db_session, _key(1), date(2091, 6, 1))
    with pytest.raises(Exception):   # le rang du compteur du 1er juin ne peut pas porter un autre jour
        db_session.execute(text(
            "INSERT INTO lab_dossier_ranks (year, counter, rank, patient_key, day) "
            "VALUES (2091, 1, 2, 'p:other', '2091-06-02')"))
    db_session.rollback()


def test_two_different_patients_cannot_share_a_triple(db_session):
    assign_dossier(db_session, _key(1), date(2091, 5, 1))
    with pytest.raises(Exception):
        db_session.execute(text(
            "INSERT INTO lab_dossier_ranks (year, counter, rank, patient_key, day) "
            "VALUES (2091, 1, 1, 'p:other', '2091-05-01')"))
    db_session.rollback()


def test_build_patient_key_stable_for_external():
    base = {"nom": "  Patient  Fictif ", "prenom": "Alpha", "age": 30, "sexe": "M", "telephone": "6 12 34"}
    same = {"nom": "patient fictif", "prenom": "ALPHA", "age": "30", "sexe": "m", "telephone": "61234"}
    other = dict(base, age=31)
    assert build_patient_key(external_info=base) == build_patient_key(external_info=same)
    assert build_patient_key(external_info=base) != build_patient_key(external_info=other)
    assert build_patient_key(external_info=base).startswith("x:")
    assert build_patient_key(patient_id=12) == "p:12"
    with pytest.raises(ValueError):
        build_patient_key()
    with pytest.raises(ValueError):
        build_patient_key(external_info={"nom": " ", "age": 3})


def test_concurrent_assignments_never_collide():
    """16 transactions simultanees (vraies connexions, vrais commit) : 4 patients x 2 demandes x 2 jours."""
    year = 2097
    days = [date(year, 6, 1), date(year, 6, 2)]
    results, errors = [], []
    barrier = threading.Barrier(16)

    def cleanup():
        with engine.begin() as c:
            c.execute(text("DELETE FROM lab_dossier_ranks WHERE year = :y"), {"y": year})
            c.execute(text("DELETE FROM lab_dossier_days WHERE year = :y"), {"y": year})

    def work(i):
        day_idx, patient = i // 8, (i % 8) // 2
        s = Session(bind=engine)
        try:
            barrier.wait(timeout=10)
            n = assign_dossier(s, f"p:{800000 + patient}", days[day_idx])
            s.commit()
            results.append((day_idx, patient, n))
        except Exception as e:  # pragma: no cover
            errors.append(e)
            s.rollback()
        finally:
            s.close()

    cleanup()
    try:
        threads = [threading.Thread(target=work, args=(i,)) for i in range(16)]
        [t.start() for t in threads]
        [t.join(timeout=30) for t in threads]
        assert not errors, errors
        by_key = {}
        for day_idx, patient, n in results:
            by_key.setdefault((day_idx, patient), set()).add(n)
        assert len(by_key) == 8 and all(len(v) == 1 for v in by_key.values())   # un patient et un jour: un numero
        for day_idx in (0, 1):
            triples = {next(iter(v)) for (d, _), v in by_key.items() if d == day_idx}
            assert len(triples) == 4
            assert len({t.counter for t in triples}) == 1                      # meme jour, meme compteur
            assert sorted(t.rank for t in triples) == [1, 2, 3, 4]
        assert {next(iter(v)).counter for v in by_key.values()} == {1, 2}       # deux jours, deux compteurs
    finally:
        cleanup()
        with engine.connect() as c:
            left = c.execute(text("SELECT (SELECT count(*) FROM lab_dossier_ranks WHERE year = :y) + "
                                  "(SELECT count(*) FROM lab_dossier_days WHERE year = :y)"), {"y": year}).scalar()
        assert left == 0, "le test de concurrence doit nettoyer ses lignes de l'annee 2097"


# ---------------------------------------------------------------- reception (route) et synchronisation


def _exam(db):
    ex = Examen(code=f"DN-{uuid.uuid4().hex[:8]}", nom="Examen dossier", categorie="Bio", prix=0)
    db.add(ex)
    db.flush()
    return ex


def _client(db, api_client, monkeypatch, day=None):
    """`day` fixe le jour des receptions SANS received_at (heure serveur simulee) ; sans `day`, vraie horloge."""
    from controller import lab_controller
    if day is not None:
        real = lab_controller.resolve_client_time

        def fake(raw, clock=None, ref=""):
            if raw is None:
                return datetime.combine(day, time(10, 0))
            return real(raw, clock=clock, ref=ref)
        monkeypatch.setattr(lab_controller, "resolve_client_time", fake)
    lab = create_test_user(db, f"dn_lab_{uuid.uuid4().hex[:6]}", "laborantin", password=PWD)
    lab.postgres_role = "app_laborantin"
    db.flush()
    client = api_client(auth_endpoints, lab_endpoints)
    return client, auth_headers(client, lab.username, PWD)


def _ext(nom, **extra):
    info = {"nom": nom, "prenom": "", "age": 30, "sexe": "M", "telephone": "",
            "prescriber_title": "Dr", "prescriber_name": "Test Alpha"}
    info.update(extra)
    return info


def test_offline_provisional_reference_replaced_by_official_number_on_sync(db_session, api_client, monkeypatch):
    client, h = _client(db_session, api_client, monkeypatch, date(2093, 10, 8))
    ex1, ex2 = _exam(db_session), _exam(db_session)
    batch_uuid, u1, u2 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    info = _ext("Sync Fictif")

    # Hors ligne : le client n'a que sa reference temporaire (code local), aucun numero officiel.
    # A l'arrivee (rejeu du connecteur, une operation par examen), le serveur attribue le numero.
    r1 = client.post("/labo/results/batch", headers=h, json={
        "external_patient_info": info, "batch_uuid": batch_uuid,
        "results": [{"uuid": u1, "examen_id": ex1.id}]})
    assert r1.status_code == 201, r1.text
    assert r1.json()["dossier"] == "001/01 du 08/10/2093"
    r2 = client.post("/labo/results/batch", headers=h, json={
        "external_patient_info": info, "batch_uuid": batch_uuid,
        "results": [{"uuid": u2, "examen_id": ex2.id}]})
    assert r2.json()["dossier"] == "001/01 du 08/10/2093"            # meme patient, meme jour: meme numero
    replay = client.post("/labo/results/batch", headers=h, json={
        "external_patient_info": info, "batch_uuid": batch_uuid,
        "results": [{"uuid": u1, "examen_id": ex1.id}]})
    assert replay.json()["dossier"] == "001/01 du 08/10/2093"        # idempotent, pas de numero brule
    rows = db_session.query(LabResult).filter(LabResult.uuid.in_([uuid.UUID(u1), uuid.UUID(u2)])).all()
    assert len(rows) == 2
    assert {(r.dossier_year, r.dossier_counter, r.dossier_rank) for r in rows} == {(2093, 1, 1)}
    assert all(r.patient_key.startswith("x:") for r in rows)
    other = client.post("/labo/results/batch", headers=h, json={
        "external_patient_info": _ext("Autre Fictif"), "batch_uuid": str(uuid.uuid4()),
        "results": [{"uuid": str(uuid.uuid4()), "examen_id": ex1.id}]})
    assert other.json()["dossier"] == "001/02 du 08/10/2093"


def test_history_and_detail_expose_the_number(db_session, api_client, monkeypatch):
    client, h = _client(db_session, api_client, monkeypatch, date(2094, 2, 3))
    ex = _exam(db_session)
    created = client.post("/labo/results/batch", headers=h, json={
        "external_patient_info": _ext("Liste Fictif"), "batch_uuid": str(uuid.uuid4()),
        "results": [{"uuid": str(uuid.uuid4()), "examen_id": ex.id}]})
    assert created.status_code == 201, created.text
    batch_id = created.json()["batch_id"]
    res = client.get(f"/labo/batch/{batch_id}", headers=h)
    assert res.status_code == 200
    body = res.json()
    assert body[0]["dossier"] == "001/01 du 03/02/2094"
    assert (body[0]["dossier_counter"], body[0]["dossier_rank"]) == (1, 1)
    detail = client.get(f"/labo/results/{body[0]['result_id']}", headers=h)
    assert detail.json()["dossier"] == "001/01 du 03/02/2094"


def test_unassigned_result_cannot_be_printed(db_session):
    unassigned = LabResult(test_type="x", status="completed", code_lab_patient="DN-NONE")
    with pytest.raises(DossierNotAssignedError) as exc:
        ensure_dossier_assigned(unassigned)
    assert "Numero de dossier non encore attribue" in str(exc.value)
    assigned = LabResult(test_type="x", status="completed", code_lab_patient="DN-OK",
                         dossier_year=2026, dossier_counter=289, dossier_rank=2)
    assert ensure_dossier_assigned(assigned) == DossierNumber(2026, 289, 2)
    assert dossier_labels(db_session, [unassigned]) == {}


# ---------------------------------------------------------------- jour de RECEPTION (C1), siblings (I1), cles (I2, I3)
# Ces tests utilisent la vraie horloge et le vrai resolve_client_time (aucun patch).


def _post(client, h, info, batch_uuid=None, received_at=None, exams=()):
    body = {"external_patient_info": info, "batch_uuid": batch_uuid or str(uuid.uuid4()),
            "results": [{"uuid": str(uuid.uuid4()), "examen_id": e.id} for e in exams]}
    if received_at is not None:
        body["received_at"] = received_at
    return client.post("/labo/results/batch", headers=h, json=body)


def _fmt(d):
    return d.strftime("%d/%m/%Y")


def test_offline_reception_on_a_past_day_keeps_the_reception_day(db_session, api_client, monkeypatch):
    client, h = _client(db_session, api_client, monkeypatch)
    ex = _exam(db_session)
    yesterday = business_now() - timedelta(days=1)
    r = _post(client, h, _ext("Veille Fictif"), received_at=yesterday.isoformat(), exams=[ex])
    assert r.status_code == 201, r.text
    assert r.json()["dossier"].endswith("du " + _fmt(yesterday.date()))
    row = db_session.query(LabResult).filter(LabResult.batch_id == uuid.UUID(r.json()["batch_id"])).one()
    assert row.test_date.date() == yesterday.date()
    # avec fuseau (Z) : meme resultat, converti en heure de Douala
    z = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    r2 = _post(client, h, _ext("Avant Veille Fictif"), received_at=z, exams=[ex])
    assert r2.status_code == 201, r2.text
    assert r2.json()["dossier"].endswith("du " + _fmt((business_now() - timedelta(days=2)).date()))
    # une reception d'aujourd'hui (sans received_at) a son propre compteur
    today = _post(client, h, _ext("Aujourdhui Fictif"), exams=[ex])
    assert today.json()["dossier"].endswith("du " + _fmt(business_today()))
    assert today.json()["dossier_counter"] not in (r.json()["dossier_counter"], r2.json()["dossier_counter"])


def test_out_of_bounds_or_invalid_received_at(db_session, api_client, monkeypatch):
    client, h = _client(db_session, api_client, monkeypatch)
    ex = _exam(db_session)
    today = _fmt(business_today())
    for i, raw in enumerate(((business_now() - timedelta(days=8)).isoformat(),
                             (business_now() + timedelta(hours=2)).isoformat())):
        r = _post(client, h, _ext(f"Borne Fictif {i}"), received_at=raw, exams=[ex])
        assert r.status_code == 201, r.text
        assert r.json()["dossier"].endswith("du " + today), raw     # hors bornes: heure serveur
    bad = _post(client, h, _ext("Invalide Fictif"), received_at="pas-une-date", exams=[ex])
    assert bad.status_code == 422, bad.text


def test_siblings_of_one_batch_share_one_number_across_days(db_session, api_client, monkeypatch):
    client, h = _client(db_session, api_client, monkeypatch)
    ex1, ex2, ex3 = _exam(db_session), _exam(db_session), _exam(db_session)
    yesterday = business_now() - timedelta(days=1)
    batch = str(uuid.uuid4())
    info = _ext("Frere Fictif")
    first = _post(client, h, info, batch_uuid=batch, received_at=yesterday.isoformat(), exams=[ex1])
    # les items suivants arrivent "apres minuit" (heure serveur, ou received_at d'aujourd'hui) : meme numero, meme jour
    second = _post(client, h, info, batch_uuid=batch, exams=[ex2])
    third = _post(client, h, info, batch_uuid=batch, received_at=business_now().isoformat(), exams=[ex3])
    for r in (first, second, third):
        assert r.status_code == 201, r.text
    labels = {first.json()["dossier"], second.json()["dossier"], third.json()["dossier"]}
    assert len(labels) == 1 and labels.pop().endswith("du " + _fmt(yesterday.date()))
    rows = db_session.query(LabResult).filter(LabResult.batch_uuid == batch).all()
    assert len(rows) == 3
    assert len({(r.dossier_year, r.dossier_counter, r.dossier_rank) for r in rows}) == 1


def test_external_without_name_is_rejected_with_422(db_session, api_client, monkeypatch):
    client, h = _client(db_session, api_client, monkeypatch)
    ex = _exam(db_session)
    for nom in ("", "   ", None):
        r = _post(client, h, dict(_ext("x"), nom=nom), exams=[ex])
        assert r.status_code == 422, (nom, r.text)


def test_same_name_externals_get_separate_ranks_but_one_reception_shares_its_rank(db_session, api_client, monkeypatch):
    client, h = _client(db_session, api_client, monkeypatch, date(2095, 7, 1))
    ex1, ex2 = _exam(db_session), _exam(db_session)
    info = _ext("Homonyme Fictif")
    a = _post(client, h, info, exams=[ex1, ex2])       # une reception, deux examens, une seule requete
    b = _post(client, h, info, exams=[ex1])            # autre personne de meme nom/age/sexe
    assert a.status_code == b.status_code == 201
    rows = db_session.query(LabResult).filter(LabResult.batch_id == uuid.UUID(a.json()["batch_id"])).all()
    assert len(rows) == 2 and len({(r.dossier_counter, r.dossier_rank) for r in rows}) == 1
    assert a.json()["dossier_counter"] == b.json()["dossier_counter"]
    assert a.json()["dossier_rank"] != b.json()["dossier_rank"]
    # hors ligne : deux requetes (un examen chacune) du meme lot partagent le rang
    batch = str(uuid.uuid4())
    c1 = _post(client, h, info, batch_uuid=batch, exams=[ex1])
    c2 = _post(client, h, info, batch_uuid=batch, exams=[ex2])
    assert c1.json()["dossier"] == c2.json()["dossier"]
    assert c1.json()["dossier_rank"] not in (a.json()["dossier_rank"], b.json()["dossier_rank"])


def test_external_with_phone_still_merges_by_person(db_session, api_client, monkeypatch):
    client, h = _client(db_session, api_client, monkeypatch, date(2095, 7, 2))
    ex = _exam(db_session)
    info = _ext("Telephone Fictif", telephone="6 12 34 56 78")
    a = _post(client, h, info, exams=[ex])
    b = _post(client, h, info, exams=[ex])
    assert a.json()["dossier"] == b.json()["dossier"]
