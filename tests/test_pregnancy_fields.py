# tests/test_pregnancy_fields.py
"""Suivi de grossesse : visibilite par role et par route, ecriture reservee, regles de synchronisation.

La secretaire (et tout role non liste) ne voit ni n'ecrit JAMAIS ces donnees. Patients inventes uniquement.
"""
import json
import re
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from api_backend.backend_app.routes.patient_dossier import patient_dossier_endpoint
from models.lab import Examen, LabResult
from models.patient import Patient
from repositories.patient_repo import PatientRepository
from tests.conftest import create_test_user, create_test_patient, create_test_transaction, auth_headers
from utils.pregnancy_visibility import (
    PREGNANCY_FIELDS, can_see_pregnancy, can_write_pregnancy, strip_pregnancy_fields,
    clean_pregnancy_input, clean_external_pregnancy, validate_gestational_weeks,
)

PWD = "Correct123!"
PROGRAM = "SUIVI-TEST-7788"
EXT_PROGRAM = "SUIVI-EXT-4455"
ROOT = Path(__file__).resolve().parents[1]

# nom du role en base (application_roles) -> (peut voir, peut ecrire)
ROLES = {
    "secretaire": (False, False),
    "laborantin": (True, True),
    "medecin": (True, True),
    "nurse": (True, True),
    "admin": (True, True),
    "promoteur": (True, False),
    "Assistant": (False, False),
    "ToxicoManager": (False, False),
    "Psychologist": (False, False),
    "SpiritualCounsellor": (False, False),
    "StockController": (False, False),
    "ProductionManager": (False, False),
}


class _U:
    def __init__(self, *roles):
        self.roles = list(roles)


# --------------------------------------------------------------------------------------------------
# Unitaire
# --------------------------------------------------------------------------------------------------

def test_pregnancy_fields_exact_names():
    assert set(PREGNANCY_FIELDS) == {
        "pregnancy_status", "expected_delivery_date", "pregnancy_program_number", "gestational_age_weeks",
    }


@pytest.mark.parametrize("role,expected", [
    ("medecin", True), ("nurse", True), ("laborantin", True), ("admin", True), ("promoteur", True),
    ("secretaire", False), ("assistant", False), ("toxicomanager", False), ("psychologist", False),
    ("spiritualcounsellor", False), ("stockcontroller", False), ("productionmanager", False),
    ("manager", False), ("inconnu", False),
])
def test_can_see(role, expected):
    assert can_see_pregnancy(_U(role)) is expected


@pytest.mark.parametrize("role,expected", [
    ("medecin", True), ("nurse", True), ("laborantin", True), ("admin", True),
    ("promoteur", False), ("secretaire", False), ("assistant", False), ("manager", False),
])
def test_can_write(role, expected):
    assert can_write_pregnancy(_U(role)) is expected


def test_no_user_sees_nothing():
    assert can_see_pregnancy(None) is False
    assert can_write_pregnancy(None) is False
    assert can_see_pregnancy(_U()) is False


def test_aliases_are_canonicalised():
    assert can_see_pregnancy(_U("Infirmier")) is True
    assert can_see_pregnancy(_U("secretary")) is False


def test_strip_is_recursive_and_non_destructive():
    payload = {
        "patient_id": 1,
        "pregnancy_status": "enceinte",
        "external_patient_info": {"nom": "X", "pregnancy_program_number": "A", "expected_delivery_date": "2027-01-01"},
        "items": [{"gestational_age_weeks": 12, "ok": 1}],
    }
    out = strip_pregnancy_fields(payload, _U("secretaire"))
    assert out == {"patient_id": 1, "external_patient_info": {"nom": "X"}, "items": [{"ok": 1}]}
    assert payload["pregnancy_status"] == "enceinte"  # original intact
    assert strip_pregnancy_fields(payload, _U("medecin")) is payload


def test_clean_input_validation():
    assert clean_pregnancy_input({"pregnancy_status": " Enceinte ", "pregnancy_program_number": " P1 "}) == {
        "pregnancy_status": "enceinte", "pregnancy_program_number": "P1"}
    assert clean_pregnancy_input({}) == {}
    with pytest.raises(ValueError):
        clean_pregnancy_input({"pregnancy_status": "peut-etre"})
    with pytest.raises(ValueError):
        clean_pregnancy_input({"pregnancy_program_number": "x" * 51})
    with pytest.raises(ValueError):
        clean_pregnancy_input({"expected_delivery_date": "pas une date"})


@pytest.mark.parametrize("v,ok", [(0, True), (45, True), (24, True), ("12", True), (None, True), ("", True),
                                  (-1, False), (46, False), ("abc", False), (12.5, False), (True, False)])
def test_validate_weeks(v, ok):
    if ok:
        validate_gestational_weeks(v)
    else:
        with pytest.raises(ValueError):
            validate_gestational_weeks(v)


def test_clean_external_pregnancy():
    info = clean_external_pregnancy({"nom": "X", "pregnancy_status": "enceinte", "gestational_age_weeks": "20",
                                    "expected_delivery_date": "2027-02-03"})
    assert info == {"nom": "X", "pregnancy_status": "enceinte", "gestational_age_weeks": 20,
                    "expected_delivery_date": "2027-02-03"}
    assert clean_external_pregnancy({"nom": "X"}) == {"nom": "X"}
    with pytest.raises(ValueError):
        clean_external_pregnancy({"pregnancy_status": "x"})
    with pytest.raises(ValueError):
        clean_external_pregnancy({"gestational_age_weeks": 99})


# --------------------------------------------------------------------------------------------------
# Donnees de test
# --------------------------------------------------------------------------------------------------

def _exam(db):
    ex = Examen(code=f"PG-{uuid.uuid4().hex[:8]}", nom="Examen grossesse", categorie="Bio", prix=0)
    db.add(ex)
    db.flush()
    return ex


def _user(db, role, tag):
    u = create_test_user(db, f"pg_{tag}_{uuid.uuid4().hex[:6]}", role, password=PWD)
    if role == "laborantin":
        u.postgres_role = "app_laborantin"
    db.flush()
    return u


@pytest.fixture
def seeded(db_session, api_client):
    """Patient enceinte (interne), resultat interne avec SA, resultat externe avec champs de grossesse, transaction."""
    db = db_session
    lab = _user(db, "laborantin", "seed")
    admin = _user(db, "admin", "seedadm")
    pid, code = create_test_patient(db, admin, first_name="Pregnantia", last_name="Testovna",
                                    gender="F", is_clinical=True)
    PatientRepository(db).set_pregnancy(pid, {
        "pregnancy_status": "enceinte",
        "expected_delivery_date": __import__("datetime").date(2027, 3, 1),
        "pregnancy_program_number": PROGRAM,
    })
    db.flush()
    ex = _exam(db)
    client = api_client(auth_endpoints, lab_endpoints, patients_endpoints, caisse_endpoints, patient_dossier_endpoint)
    h = auth_headers(client, lab.username, PWD)
    r = client.post("/labo/results/batch", headers=h, json={
        "patient_id": pid, "gestational_age_weeks": 24, "batch_uuid": str(uuid.uuid4()),
        "results": [{"examen_id": ex.id}]})
    assert r.status_code == 201, r.text
    internal = db.query(LabResult).filter(LabResult.patient_id == pid).one()
    assert internal.gestational_age_weeks == 24
    r2 = client.post("/labo/results/batch", headers=h, json={
        "external_patient_info": {"nom": "Externa", "prenom": "Fictive", "age": 30, "sexe": "F", "telephone": "699000111",
                                  "pregnancy_status": "enceinte", "pregnancy_program_number": EXT_PROGRAM,
                                  "expected_delivery_date": "2027-04-02"},
        "gestational_age_weeks": 30, "batch_uuid": str(uuid.uuid4()),
        "results": [{"examen_id": ex.id}]})
    assert r2.status_code == 201, r2.text
    external = db.query(LabResult).filter(LabResult.patient_id.is_(None), LabResult.examen_id == ex.id,
                                          LabResult.gestational_age_weeks == 30).one()
    assert external.external_pregnancy_info["pregnancy_program_number"] == EXT_PROGRAM
    assert "pregnancy_program_number" not in external.external_patient_info
    tx = create_test_transaction(db, admin, patient_id=pid)
    return {"pid": pid, "code": code, "internal": internal, "external": external, "tx": tx.transaction_id,
            "batch": str(internal.batch_id), "ext_batch": str(external.batch_id), "client": client, "ex": ex}


def _routes(s):
    pid, tx = s["pid"], s["tx"]
    return [
        ("patient par id", "GET", f"/patients/{pid}"),
        ("liste patients", "GET", "/patients/?per_page=100"),
        ("recherche patients", "GET", "/patients/?search=Pregnantia&per_page=100"),
        ("recherche par code", "GET", f"/patients/find?q={s['code']}"),
        ("find_by_code", "GET", f"/patients/find_by_code?code={s['code']}"),
        ("liste clinique", "GET", "/patients/clinical?per_page=100"),
        ("dossier consolide", "GET", f"/patients/{pid}/dossier"),
        ("caisse: patient joint", "GET", f"/caisse/patient/{pid}"),
        ("caisse: transaction", "GET", f"/caisse/{tx}"),
        ("caisse: liste", "GET", "/caisse/"),
        ("resultat par id", "GET", f"/labo/results/{s['internal'].result_id}"),
        ("resultat externe par id", "GET", f"/labo/results/{s['external'].result_id}"),
        ("resultats par lot", "GET", f"/labo/batch/{s['batch']}"),
        ("resultats externes par lot", "GET", f"/labo/batch/{s['ext_batch']}"),
        ("historique labo", "GET", "/labo/history/paginated?limit=100"),
        ("historique patient", "GET", f"/labo/patient/{pid}/history"),
        ("recherche labo", "GET", "/labo/search?q=Testovna"),
        ("recherche labo externe", "GET", "/labo/search?q=Externa"),
        ("paillasse", "GET", "/labo/paillasse"),
        ("export csv", "GET", "/patients/export?format=csv"),
    ]


SECRETS = (PROGRAM, EXT_PROGRAM, "2027-03-01", "2027-04-02")


def _assert_clean(resp, label):
    body = resp.text
    for f in PREGNANCY_FIELDS:
        assert f not in body, f"{label}: cle {f} presente"
    for v in SECRETS:
        assert v not in body, f"{label}: valeur de grossesse presente"


# --------------------------------------------------------------------------------------------------
# Matrice role x route : lecture
# --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("role", list(ROLES))
def test_read_matrix(db_session, seeded, role):
    can_see, _ = ROLES[role]
    u = _user(db_session, role, "reader")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    ok_routes = 0
    for label, method, url in _routes(seeded):
        resp = client.request(method, url, headers=h)
        if not can_see:
            _assert_clean(resp, f"{role} / {label} ({resp.status_code})")
        if resp.status_code == 200:
            ok_routes += 1
    assert ok_routes >= 0  # certaines routes sont interdites au role (403), ce n'est pas ce qu'on teste ici


@pytest.mark.parametrize("role", ["medecin", "nurse", "admin"])
def test_viewers_get_patient_pregnancy(db_session, seeded, role):
    u = _user(db_session, role, "viewer")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    for url in (f"/patients/{seeded['pid']}", f"/patients/find?q={seeded['code']}"):
        r = client.get(url, headers=h)
        assert r.status_code == 200, (url, r.text)
        data = r.json()
        assert data["pregnancy_status"] == "enceinte"
        assert data["pregnancy_program_number"] == PROGRAM
        assert data["expected_delivery_date"] == "2027-03-01"
    lst = client.get("/patients/?search=Pregnantia&per_page=100", headers=h).json()["data"]
    row = [p for p in lst if p["patient_id"] == seeded["pid"]][0]
    assert row["pregnancy_status"] == "enceinte"


@pytest.mark.parametrize("role", ["medecin", "nurse", "admin", "promoteur"])
def test_viewers_get_dossier_pregnancy(db_session, seeded, role):
    u = _user(db_session, role, "dossier")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    r = client.get(f"/patients/{seeded['pid']}/dossier", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["patient"]["pregnancy_status"] == "enceinte"
    assert r.json()["patient"]["pregnancy_program_number"] == PROGRAM


@pytest.mark.parametrize("role", ["laborantin", "admin", "medecin", "nurse"])
def test_viewers_get_lab_result_pregnancy(db_session, seeded, role):
    u = _user(db_session, role, "labview")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    for res in (seeded["internal"], seeded["external"]):
        # medecin/nurse ne lisent que les resultats valides : on valide ceux du test
        res.status = "completed"
    db_session.flush()
    r = client.get(f"/labo/results/{seeded['internal'].result_id}", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["gestational_age_weeks"] == 24
    assert r.json()["patient_info"]["pregnancy_status"] == "enceinte"
    r = client.get(f"/labo/results/{seeded['external'].result_id}", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["gestational_age_weeks"] == 30
    assert r.json()["patient_info"]["pregnancy_program_number"] == EXT_PROGRAM
    r = client.get(f"/labo/batch/{seeded['batch']}", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()[0]["gestational_age_weeks"] == 24
    r = client.get(f"/labo/batch/{seeded['ext_batch']}", headers=h)
    assert r.json()[0]["external_pregnancy_info"]["pregnancy_program_number"] == EXT_PROGRAM


def test_secretary_lab_endpoints_even_when_allowed(db_session, seeded):
    """/labo/exams est ouvert a la secretaire : jamais de champ de grossesse ; les resultats lui sont fermes."""
    u = _user(db_session, "secretaire", "labsec")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    _assert_clean(client.get("/labo/exams", headers=h), "secretaire / exams")
    r = client.get(f"/labo/results/{seeded['internal'].result_id}", headers=h)
    assert r.status_code == 403
    _assert_clean(r, "secretaire / resultat")


def test_secretary_patient_routes_open_but_clean(db_session, seeded):
    u = _user(db_session, "secretaire", "patsec")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    r = client.get(f"/patients/{seeded['pid']}", headers=h)
    assert r.status_code == 200
    assert r.json()["first_name"] == "Pregnantia"
    _assert_clean(r, "secretaire / patient")
    r = client.get("/patients/?search=Pregnantia&per_page=100", headers=h)
    assert r.status_code == 200 and r.json()["data"]
    _assert_clean(r, "secretaire / liste")
    r = client.get(f"/caisse/{seeded['tx']}", headers=h)
    assert r.status_code == 200
    _assert_clean(r, "secretaire / caisse")


def test_unauthenticated_response_has_no_pregnancy(seeded):
    r = seeded["client"].get(f"/patients/{seeded['pid']}")
    assert r.status_code == 401
    _assert_clean(r, "anonyme")


# --------------------------------------------------------------------------------------------------
# Ecriture
# --------------------------------------------------------------------------------------------------

def _patient_payload(**extra):
    return {"first_name": "Newia", "last_name": "Testova", "birth_date": "1995-05-05", "gender": "F",
            "is_clinical": True, **extra}


def _row(db, pid):
    db.expire_all()
    return db.query(Patient).filter(Patient.patient_id == pid).one()


@pytest.mark.parametrize("field,value", [
    ("pregnancy_status", "enceinte"),
    ("expected_delivery_date", "2027-06-01"),
    ("pregnancy_program_number", "SUIVI-HACK"),
])
def test_secretary_cannot_write_on_update(db_session, seeded, field, value):
    u = _user(db_session, "secretaire", "wsec")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    r = client.put(f"/patients/{seeded['pid']}", headers=h, json={field: value})
    assert r.status_code == 403, r.text
    assert "grossesse" in r.json()["detail"]
    p = _row(db_session, seeded["pid"])
    assert p.pregnancy_program_number == PROGRAM and p.pregnancy_status == "enceinte"


def test_secretary_cannot_write_on_create(db_session, seeded):
    u = _user(db_session, "secretaire", "wsec2")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    before = db_session.query(Patient).count()
    r = client.post("/patients/", headers=h, json=_patient_payload(pregnancy_status="enceinte"))
    assert r.status_code == 403, r.text
    assert db_session.query(Patient).count() == before


def test_secretary_ordinary_update_still_works_and_keeps_pregnancy(db_session, seeded):
    u = _user(db_session, "secretaire", "wsec3")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    r = client.put(f"/patients/{seeded['pid']}", headers=h, json={"residence": "Quartier Test"})
    assert r.status_code == 200, r.text
    _assert_clean(r, "secretaire / maj ordinaire")
    p = _row(db_session, seeded["pid"])
    assert p.residence == "Quartier Test"
    assert p.pregnancy_status == "enceinte" and p.pregnancy_program_number == PROGRAM


def test_secretary_create_without_pregnancy_defaults_inconnu(db_session, seeded):
    u = _user(db_session, "secretaire", "wsec4")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    r = client.post("/patients/", headers=h, json=_patient_payload())
    assert r.status_code == 201, r.text
    _assert_clean(r, "secretaire / creation")
    p = _row(db_session, r.json()["patient_id"])
    assert p.pregnancy_status == "inconnu" and p.expected_delivery_date is None and p.pregnancy_program_number is None


@pytest.mark.parametrize("role", ["medecin", "nurse", "admin"])
def test_writers_can_write_on_update_and_create(db_session, seeded, role):
    u = _user(db_session, role, "writer")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    r = client.put(f"/patients/{seeded['pid']}", headers=h, json={
        "pregnancy_status": "non_enceinte", "expected_delivery_date": "2027-07-07", "pregnancy_program_number": "N-1"})
    assert r.status_code == 200, r.text
    assert r.json()["pregnancy_status"] == "non_enceinte"
    p = _row(db_session, seeded["pid"])
    assert (p.pregnancy_status, str(p.expected_delivery_date), p.pregnancy_program_number) == (
        "non_enceinte", "2027-07-07", "N-1")
    r = client.post("/patients/", headers=h, json=_patient_payload(pregnancy_status="enceinte",
                                                                    pregnancy_program_number="C-9"))
    assert r.status_code == 201, r.text
    assert r.json()["pregnancy_status"] == "enceinte" and r.json()["pregnancy_program_number"] == "C-9"


def test_write_invalid_values_rejected(db_session, seeded):
    u = _user(db_session, "medecin", "winv")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    r = client.put(f"/patients/{seeded['pid']}", headers=h, json={"pregnancy_status": "peut-etre"})
    assert r.status_code == 400, r.text
    r = client.put(f"/patients/{seeded['pid']}", headers=h, json={"pregnancy_program_number": "x" * 51})
    assert r.status_code == 400, r.text
    assert _row(db_session, seeded["pid"]).pregnancy_status == "enceinte"


def test_db_constraints(db_session, seeded):
    pid = seeded["pid"]
    for sql in (
        f"UPDATE patients SET pregnancy_status = 'x' WHERE patient_id = {pid}",
        f"UPDATE lab_results SET gestational_age_weeks = 46 WHERE result_id = {seeded['internal'].result_id}",
        f"UPDATE lab_results SET gestational_age_weeks = -1 WHERE result_id = {seeded['internal'].result_id}",
    ):
        sp = db_session.begin_nested()
        with pytest.raises(Exception):
            db_session.execute(text(sql))
        sp.rollback()
    db_session.execute(text(f"UPDATE lab_results SET gestational_age_weeks = 45 WHERE result_id = {seeded['internal'].result_id}"))
    db_session.execute(text(f"UPDATE lab_results SET gestational_age_weeks = 0 WHERE result_id = {seeded['internal'].result_id}"))
    db_session.execute(text(f"UPDATE lab_results SET gestational_age_weeks = NULL WHERE result_id = {seeded['internal'].result_id}"))


def test_lab_batch_rejects_bad_weeks_and_external_values(db_session, seeded):
    lab = _user(db_session, "laborantin", "wlab")
    client = seeded["client"]
    h = auth_headers(client, lab.username, PWD)
    ex = seeded["ex"]
    base = {"patient_id": seeded["pid"], "batch_uuid": str(uuid.uuid4()), "results": [{"examen_id": ex.id}]}
    r = client.post("/labo/results/batch", headers=h, json={**base, "gestational_age_weeks": 46})
    assert r.status_code == 422, r.text
    r = client.post("/labo/results/batch", headers=h, json={
        "external_patient_info": {"nom": "E", "prenom": "F", "age": 20, "sexe": "F", "telephone": "699222333",
                                  "pregnancy_status": "oui"},
        "batch_uuid": str(uuid.uuid4()), "results": [{"examen_id": ex.id}]})
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("role", ["ToxicoManager"])
def test_non_writer_lab_write_forbidden(db_session, seeded, role):
    """ToxicoManager peut creer un resultat unitaire (POST /labo/results) mais pas ecrire la grossesse."""
    u = _user(db_session, role, "wtox")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    ex = seeded["ex"]
    before = db_session.query(LabResult).count()
    r = client.post("/labo/results", headers=h, json={"examen_id": ex.id, "patient_id": seeded["pid"],
                                                       "gestational_age_weeks": 12})
    assert r.status_code == 403, r.text
    r = client.post("/labo/results", headers=h, json={
        "examen_id": ex.id, "external_patient_info": {"nom": "E", "pregnancy_status": "enceinte"}})
    assert r.status_code == 403, r.text
    assert db_session.query(LabResult).count() == before


@pytest.mark.parametrize("role", ["secretaire", "Assistant", "StockController", "promoteur"])
def test_non_writers_cannot_post_lab_batch(db_session, seeded, role):
    u = _user(db_session, role, "wbatch")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    r = client.post("/labo/results/batch", headers=h, json={
        "patient_id": seeded["pid"], "gestational_age_weeks": 10, "batch_uuid": str(uuid.uuid4()),
        "results": [{"examen_id": seeded["ex"].id}]})
    assert r.status_code == 403, r.text


def test_batch_creation_response_is_clean_for_lab(db_session, seeded):
    lab = _user(db_session, "laborantin", "wresp")
    client = seeded["client"]
    h = auth_headers(client, lab.username, PWD)
    r = client.post("/labo/results/batch", headers=h, json={
        "patient_id": seeded["pid"], "gestational_age_weeks": 10, "batch_uuid": str(uuid.uuid4()),
        "results": [{"examen_id": seeded["ex"].id}]})
    assert r.status_code == 201, r.text
    assert not any(f in r.text for f in PREGNANCY_FIELDS)  # la reponse de creation ne renvoie pas les donnees


# --------------------------------------------------------------------------------------------------
# Journal d'audit
# --------------------------------------------------------------------------------------------------

def test_audit_never_contains_pregnancy(db_session, seeded):
    u = _user(db_session, "medecin", "waud")
    client = seeded["client"]
    h = auth_headers(client, u.username, PWD)
    r = client.put(f"/patients/{seeded['pid']}", headers=h, json={
        "pregnancy_status": "non_enceinte", "pregnancy_program_number": "AUDIT-SECRET-1", "residence": "Rue Audit"})
    assert r.status_code == 200, r.text
    r = client.post("/patients/", headers=h, json=_patient_payload(pregnancy_status="enceinte",
                                                                    pregnancy_program_number="AUDIT-SECRET-2"))
    assert r.status_code == 201, r.text
    rows = db_session.execute(text(
        "SELECT old_values::text, new_values::text FROM audit_user_actions WHERE resource_type = 'Patient' "
        "ORDER BY 1 DESC")).fetchall()
    blob = " ".join((a or "") + " " + (b or "") for a, b in rows)
    assert "Rue Audit" in blob  # l'audit des autres champs fonctionne
    for f in PREGNANCY_FIELDS:
        assert f not in blob
    assert "AUDIT-SECRET" not in blob and PROGRAM not in blob


# --------------------------------------------------------------------------------------------------
# PowerSync : regles de synchronisation
# --------------------------------------------------------------------------------------------------

def _streams():
    import yaml
    cfg = yaml.safe_load((ROOT / "powersync" / "sync-config.yaml").read_text(encoding="utf-8"))
    return cfg["streams"]


def test_sync_config_never_selects_pregnancy_columns():
    raw = (ROOT / "powersync" / "sync-config.yaml").read_text(encoding="utf-8")
    code = "\n".join(l for l in raw.splitlines() if not l.strip().startswith("#"))
    for f in PREGNANCY_FIELDS:
        assert f not in code
    assert not re.search(r"select\s+\*", code, re.I)
    assert not re.search(r"\b(patients|lab_results)\s*\.\s*\*", code, re.I)


def test_secretary_streams_use_explicit_columns():
    """Chaque flux qui lit patients ou lab_results liste ses colonnes une a une (aucun SELECT *), donc une
    colonne ajoutee plus tard n'est jamais envoyee au secretariat sans decision explicite."""
    streams = _streams()
    assert streams
    for name, spec in streams.items():
        for q in spec.get("queries", []):
            assert "*" not in q, f"{name}: SELECT * interdit"
            if re.search(r"\bpatients\b|\blab_results\b", q):
                assert re.search(r"select\s+\w", q, re.I)


def _table_blocks(schema_js: str) -> dict:
    """AppSchema.js : {nom de table locale: texte de son bloc `new Table(...)`}, par appariement des parentheses."""
    blocks = {}
    for m in re.finditer(r"const\s+(\w+)\s*=\s*new Table\(", schema_js):
        depth, i = 1, m.end()
        while depth and i < len(schema_js):
            depth += {"(": 1, ")": -1}.get(schema_js[i], 0)
            i += 1
        blocks[m.group(1)] = schema_js[m.end():i]
    return blocks


def test_local_schema_has_no_pregnancy_column():
    schema = (ROOT / "ah2-admin-web" / "src" / "powersync-client" / "AppSchema.js").read_text(encoding="utf-8")
    blocks = _table_blocks(schema)
    assert "lab_results" in blocks and len(blocks) > 10
    # Seules exceptions (B4) : colonnes locales de la demande de laboratoire, ecrites a la reception (hors ligne)
    # puis envoyees par le connecteur, jamais telechargees (aucun flux ne les selectionne).
    allowed = {"gestational_age_weeks", "external_pregnancy_info", "pregnancy_status_at_result"}
    for f in list(PREGNANCY_FIELDS) + ["external_pregnancy_info", "pregnancy_status_at_result"]:
        owners = [name for name, body in blocks.items() if re.search(rf"^\s*{f}\s*:", body, re.M)]
        if f in allowed:
            assert owners == ["lab_results"], (f, owners)  # DANS le bloc lab_results, nulle part ailleurs
        else:
            assert owners == [], (f, owners)
