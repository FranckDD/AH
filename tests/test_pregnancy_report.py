# tests/test_pregnancy_report.py
"""Rapport de subvention (grossesse) : filtre par date de validation (minuit de Douala), internes et externes,
roles (promoteur et admin seulement), limite de 366 jours, PDF nominatif echappe. Patients inventes."""
import io
import uuid
from datetime import date, datetime

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints, pregnancy_report_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from models.lab import Examen, LabResult
from repositories.patient_repo import PatientRepository
from tests.conftest import create_test_user, create_test_patient, auth_headers

PWD = "Correct123!"
PROG = "SUIVI-RPT-1122"
EXT_PROG = "SUIVI-EXT-9911"
ROLES_OK = ["promoteur", "admin"]
ROLES_KO = ["secretaire", "laborantin", "medecin", "nurse", "Assistant", "ToxicoManager", "Psychologist",
            "SpiritualCounsellor", "StockController", "ProductionManager"]


def _user(db, role, tag):
    u = create_test_user(db, f"pr_{tag}_{uuid.uuid4().hex[:6]}", role, password=PWD)
    db.flush()
    return u


def _exam(db, nom):
    ex = Examen(code=f"PR-{uuid.uuid4().hex[:8]}", nom=nom, categorie="Bio", prix=0)
    db.add(ex)
    db.flush()
    return ex


def _result(db, ex, when, status="completed", patient_id=None, ext=None, sa=None, preg=None, snap=None):
    r = LabResult(
        patient_id=patient_id, test_type="Analyse Labo", test_date=when, status=status, examen_id=ex.id,
        code_lab_patient=f"RPT-{uuid.uuid4().hex[:10]}", external_patient_info=ext, gestational_age_weeks=sa,
        external_pregnancy_info=preg, pregnancy_status_at_result=snap,
        batch_id=uuid.uuid4(),
    )
    db.add(r)
    db.flush()
    return r


@pytest.fixture
def world(db_session, api_client):
    db = db_session
    admin = _user(db, "admin", "w")
    ex1, ex2 = _exam(db, "Glycemie <b>Test</b>"), _exam(db, "Hemogramme R")
    pid, code = create_test_patient(db, admin, first_name="Pregnantia", last_name="Reporta", gender="F")
    PatientRepository(db).set_pregnancy(pid, {"pregnancy_status": "enceinte", "pregnancy_program_number": PROG,
                                              "expected_delivery_date": date(2027, 3, 1)})
    pid_no, _ = create_test_patient(db, admin, first_name="Nonna", last_name="Nonenceinte", gender="F")
    PatientRepository(db).set_pregnancy(pid_no, {"pregnancy_status": "non_enceinte"})
    pid_unk, _ = create_test_patient(db, admin, first_name="Inconna", last_name="Inconnue", gender="F")
    ext_pregnant = {"nom": "Externa <script>x</script>", "prenom": "Fictive", "sexe": "F", "age": 30,
                    }
    ext_preg = {"pregnancy_status": "enceinte", "pregnancy_program_number": EXT_PROG, "gestational_age_weeks": 20}
    ext_not = {"nom": "Externe Nonenceinte", "prenom": "Zed", "sexe": "F"}
    d = datetime(2026, 3, 10, 10, 0)
    _result(db, ex1, d, patient_id=pid, sa=22, snap="enceinte")                                   # interne enceinte, valide
    _result(db, ex2, d.replace(hour=11), patient_id=pid, sa=22, snap="enceinte")                  # meme jour : regroupe
    _result(db, ex1, datetime(2026, 3, 10, 23, 59, 59), patient_id=pid_no, snap="non_enceinte")        # non enceinte
    _result(db, ex1, d, patient_id=pid_unk, snap="inconnu")                                       # inconnu
    _result(db, ex1, d, status="pending", patient_id=pid, sa=22, snap="enceinte")                  # non valide
    _result(db, ex1, d, status="partial", patient_id=pid, snap="enceinte")                         # non valide
    _result(db, ex1, datetime(2026, 3, 12, 8, 0), ext=ext_pregnant, preg=ext_preg, snap="enceinte", sa=20)        # externe enceinte
    _result(db, ex1, datetime(2026, 3, 12, 9, 0), ext=ext_not, preg={"pregnancy_status": "non_enceinte"}, snap="non_enceinte")                    # externe non enceinte
    client = api_client(auth_endpoints, lab_endpoints, pregnancy_report_endpoints, patients_endpoints)
    return {"client": client, "pid": pid, "code": code, "ex1": ex1, "ex2": ex2, "admin": admin, "db": db}


def _get(world, role, url):
    u = _user(world["db"], role, "u")
    return world["client"].get(url, headers=auth_headers(world["client"], u.username, PWD))


URL = "/labo/reports/pregnancy?from=2026-03-01&to=2026-03-31"


@pytest.mark.parametrize("role", ROLES_OK)
def test_allowed_roles(world, role):
    r = _get(world, role, URL)
    assert r.status_code == 200, r.text
    assert "rows" in r.json()
    assert _get(world, role, URL.replace("pregnancy?", "pregnancy.pdf?")).status_code == 200


@pytest.mark.parametrize("role", ROLES_KO)
def test_other_roles_forbidden_and_no_leak(world, role):
    for url in (URL, URL.replace("pregnancy?", "pregnancy.pdf?")):
        r = _get(world, role, url)
        assert r.status_code == 403, (role, url, r.status_code)
        for secret in (PROG, EXT_PROG, "Reporta", "Externa"):
            assert secret not in r.text


def test_anonymous_unauthorised(world):
    assert world["client"].get(URL).status_code == 401


def test_rows_internal_external_and_exclusions(world):
    body = _get(world, "promoteur", URL).json()
    names = [r["patient_name"] for r in body["rows"]]
    assert "Reporta Pregnantia" in names
    assert any(n.startswith("Externa") for n in names)
    assert not any("Nonenceinte" in n or "Inconnue" in n for n in names)
    assert body["total_rows"] == 2 and body["total_patients"] == 2
    internal = next(r for r in body["rows"] if r["patient_name"] == "Reporta Pregnantia")
    assert internal["patient_number"] == world["code"]
    assert internal["pregnancy_program_number"] == PROG
    assert internal["gestational_age_weeks"] == 22
    assert internal["validated_on"] == "2026-03-10"
    assert sorted(internal["exams"]) == sorted(["Glycemie <b>Test</b>", "Hemogramme R"])  # pending / partial exclus
    ext = next(r for r in body["rows"] if r["external"])
    assert ext["pregnancy_program_number"] == EXT_PROG and ext["gestational_age_weeks"] == 20
    assert ext["patient_number"] == ""
    # ordre par date de validation
    assert [r["validated_on"] for r in body["rows"]] == sorted(r["validated_on"] for r in body["rows"])


def test_period_boundary_at_douala_midnight(world):
    db, ex = world["db"], world["ex1"]
    pid = world["pid"]
    _result(db, ex, datetime(2026, 5, 9, 23, 59, 59), patient_id=pid, snap="enceinte")
    _result(db, ex, datetime(2026, 5, 10, 0, 0, 0), patient_id=pid, snap="enceinte")

    def days(frm, to):
        b = _get(world, "admin", f"/labo/reports/pregnancy?from={frm}&to={to}").json()
        return [r["validated_on"] for r in b["rows"]]

    assert days("2026-05-09", "2026-05-09") == ["2026-05-09"]
    assert days("2026-05-10", "2026-05-10") == ["2026-05-10"]
    assert days("2026-05-09", "2026-05-10") == ["2026-05-09", "2026-05-10"]
    assert days("2026-05-11", "2026-05-20") == []
    assert days("2026-05-01", "2026-05-08") == []


def test_validation_date_not_reception_date(world):
    """Seuls les resultats valides comptent, dates prises sur la validation (test_date d'un resultat termine)."""
    b = _get(world, "admin", "/labo/reports/pregnancy?from=2026-03-11&to=2026-03-11").json()
    assert b["rows"] == [] and b["total_rows"] == 0 and b["total_patients"] == 0


@pytest.mark.parametrize("qs", [
    "from=2026-13-01&to=2026-12-31", "from=abc&to=2026-12-31", "from=2026-03-01", "to=2026-03-01",
    "from=2026-03-10&to=2026-03-09", "from=2025-01-01&to=2026-12-31", "from=2026-02-30&to=2026-03-01", "from=&to=",
])
def test_bad_dates_422(world, qs):
    for base in ("/labo/reports/pregnancy", "/labo/reports/pregnancy.pdf"):
        assert _get(world, "promoteur", f"{base}?{qs}").status_code == 422, (base, qs)


def test_range_limit_366_days(world):
    assert _get(world, "promoteur", "/labo/reports/pregnancy?from=2026-01-01&to=2026-12-31").status_code == 200  # 365 j
    assert _get(world, "promoteur", "/labo/reports/pregnancy?from=2028-01-01&to=2028-12-31").status_code == 200  # 366 j (bissextile)
    assert _get(world, "promoteur", "/labo/reports/pregnancy?from=2026-01-01&to=2027-01-01").status_code == 200  # 366 j inclusifs
    assert _get(world, "promoteur", "/labo/reports/pregnancy?from=2026-01-01&to=2027-01-02").status_code == 422  # 367 j


def test_pdf_content_escaped(world):
    r = _get(world, "promoteur", URL.replace("pregnancy?", "pregnancy.pdf?"))
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    from pypdf import PdfReader
    text = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "Reporta Pregnantia" in text
    assert PROG in text and EXT_PROG in text
    assert "Glycemie <b>Test</b>" in text          # echappe : affiche litteralement, jamais interprete
    assert "<script>x</script>" in text
    assert "2 patiente(s)" in text and "2 ligne(s)" in text
    assert "10/03/2026" in text and "12/03/2026" in text


def test_pdf_empty_period(world):
    r = _get(world, "admin", "/labo/reports/pregnancy.pdf?from=2020-01-01&to=2020-01-31")
    assert r.status_code == 200
    from pypdf import PdfReader
    text = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "0 patiente(s)" in text


def test_secretary_elsewhere_gets_no_pregnancy_key(world):
    """Reutilise l'idee de la matrice B2 : une secretaire qui lit les patients n'obtient aucune cle de grossesse
    ni la valeur du numero de suivi, meme apres la creation des donnees du rapport."""
    sec = _user(world["db"], "secretaire", "sec")
    h = auth_headers(world["client"], sec.username, PWD)
    r = world["client"].get(f"/patients/{world['pid']}", headers=h)
    for key in ("pregnancy_status", "expected_delivery_date", "pregnancy_program_number", "gestational_age_weeks"):
        assert key not in r.text
    assert PROG not in r.text
