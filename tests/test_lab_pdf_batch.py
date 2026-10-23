# tests/test_lab_pdf_batch.py
"""
PDF unique « dossier complet » d'un passage patient (batch_id) + signature du chef du laboratoire a droite
(2026-10-23). Texte et positions lus via pypdf (WeasyPrint sous-ensemble les polices : jamais dans les octets bruts).
"""
import io
import uuid
from datetime import datetime, timedelta

from pypdf import PdfReader

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from models.lab import Examen, LabResult, LabResultDetail, Parametre
from tests.conftest import create_test_user, create_test_patient, auth_headers

PWD = "Correct123!"
SIGNATURE_TITLE = "Le chef du laboratoire"


def _text(content: bytes) -> str:
    return "\n".join(" ".join((p.extract_text() or "").split()) for p in PdfReader(io.BytesIO(content)).pages)


def _x_of(content: bytes, marker: str):
    """(abscisse du texte, largeur de la page) du premier texte contenant `marker`."""
    for page in PdfReader(io.BytesIO(content)).pages:
        found = []

        def visitor(text, cm, tm, font_dict, font_size):
            if marker in text and not found:
                found.append(cm[4] + tm[4] * cm[0])

        page.extract_text(visitor_text=visitor)
        if found:
            return found[0], float(page.mediabox.width)
    raise AssertionError(f"{marker!r} introuvable dans le PDF")


def _exam_with_param(db, nom):
    ex = Examen(code=f"PB-{uuid.uuid4().hex[:8]}", nom=nom, categorie="Bio", prix=1000)
    db.add(ex)
    db.flush()
    p = Parametre(examen_id=ex.id, nom_parametre=f"Param {nom}", unite="g/L", type_valeur="numeric")
    db.add(p)
    db.flush()
    return ex, p


def _result(db, pid, ex, param, status, batch, note=None):
    r = LabResult(patient_id=pid, test_type=ex.nom, status=status, examen_id=ex.id, batch_id=batch, note=note,
                  code_lab_patient=f"LAB-B-{uuid.uuid4().hex[:10]}", test_date=datetime.now() - timedelta(minutes=1))
    db.add(r)
    db.flush()
    db.add(LabResultDetail(result_id=r.result_id, parametre_id=param.id, valeur_text="7", valeur_num=7, flagged=False))
    db.flush()
    return r


def _passage(db, tag, statuses, user_role="admin"):
    admin = create_test_user(db, f"pdfb_{tag}", user_role, password=PWD)
    pid, _ = create_test_patient(db, admin, first_name=f"PdfB{tag}")
    batch = uuid.uuid4()
    rows = []
    for i, st in enumerate(statuses):
        ex, p = _exam_with_param(db, f"Exam{tag}{i}")
        rows.append(_result(db, pid, ex, p, st, batch, note=f"Note {tag}{i}" if st == "completed" else None))
    return admin, batch, rows


def _client(api_client, db, username):
    client = api_client(auth_endpoints, lab_endpoints)
    return client, auth_headers(client, username, PWD)


# --------------------------------------------------------------------- dossier complet

def test_pdf_dossier_complet_reunit_les_examens_termines_d_un_passage(db_session, api_client):
    admin, batch, rows = _passage(db_session, "A1", ["completed", "completed", "pending"])
    client, headers = _client(api_client, db_session, "pdfb_A1")

    r = client.get(f"/labo/batch/{batch}/pdf", headers=headers)

    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    txt = _text(r.content)
    assert "ExamA10" in txt and "ExamA11" in txt            # les deux examens termines
    assert "ExamA12" not in txt                              # l'examen encore en attente n'y figure pas
    assert "Param ExamA10" in txt and "Param ExamA11" in txt
    assert "Note A10" in txt and "Note A11" in txt
    assert txt.count("PdfBA1") == 1                          # le patient n'est nomme qu'une seule fois
    assert txt.count(SIGNATURE_TITLE) == 1                   # une seule zone de signature pour tout le dossier
    assert "1 examen" in txt and "non termin" in txt         # mention claire de l'examen laisse de cote


def test_pdf_dossier_complet_sans_mention_quand_tout_est_termine(db_session, api_client):
    _, batch, _ = _passage(db_session, "A2", ["completed", "completed"])
    client, headers = _client(api_client, db_session, "pdfb_A2")

    txt = _text(client.get(f"/labo/batch/{batch}/pdf", headers=headers).content)
    assert "non termin" not in txt


def test_pdf_dossier_complet_aucun_examen_termine_est_refuse(db_session, api_client):
    _, batch, _ = _passage(db_session, "A3", ["pending", "pending"])
    client, headers = _client(api_client, db_session, "pdfb_A3")

    r = client.get(f"/labo/batch/{batch}/pdf", headers=headers)
    assert r.status_code == 409


def test_pdf_dossier_complet_lot_inconnu_ou_invalide(db_session, api_client):
    create_test_user(db_session, "pdfb_A4", "admin", password=PWD)
    client, headers = _client(api_client, db_session, "pdfb_A4")

    assert client.get(f"/labo/batch/{uuid.uuid4()}/pdf", headers=headers).status_code == 404
    assert client.get("/labo/batch/pas-un-uuid/pdf", headers=headers).status_code == 404


def test_pdf_dossier_complet_droits_comme_le_pdf_d_un_examen(db_session, api_client):
    admin, batch, _ = _passage(db_session, "A5", ["completed", "pending"])
    create_test_user(db_session, "pdfb_A5_med", "medecin", password=PWD)
    create_test_user(db_session, "pdfb_A5_sec", "secretaire", password=PWD)
    client = api_client(auth_endpoints, lab_endpoints)

    # le medecin lit les examens termines (lecture seule), pas la secretaire
    ok = client.get(f"/labo/batch/{batch}/pdf", headers=auth_headers(client, "pdfb_A5_med", PWD))
    assert ok.status_code == 200 and "ExamA50" in _text(ok.content)
    assert client.get(f"/labo/batch/{batch}/pdf", headers=auth_headers(client, "pdfb_A5_sec", PWD)).status_code == 403
    assert client.get(f"/labo/batch/{batch}/pdf").status_code in (401, 403)


# --------------------------------------------------------------------- signature a droite

def test_signature_du_pdf_d_un_examen_est_a_droite(db_session, api_client):
    _, batch, rows = _passage(db_session, "S1", ["completed"])
    client, headers = _client(api_client, db_session, "pdfb_S1")

    pdf = client.get(f"/labo/results/{rows[0].result_id}/pdf", headers=headers).content
    x, width = _x_of(pdf, SIGNATURE_TITLE)
    # case de 85 mm calee contre la marge droite : son titre commence vers le milieu de la page (a gauche : ~63 pt)
    assert x > 200, f"signature a gauche (x={x:.0f} sur {width:.0f})"


def test_signature_du_dossier_complet_est_a_droite(db_session, api_client):
    _, batch, _ = _passage(db_session, "S2", ["completed", "completed"])
    client, headers = _client(api_client, db_session, "pdfb_S2")

    pdf = client.get(f"/labo/batch/{batch}/pdf", headers=headers).content
    x, width = _x_of(pdf, SIGNATURE_TITLE)
    assert x > 200, f"signature a gauche (x={x:.0f} sur {width:.0f})"


def test_les_autres_pdf_gardent_la_signature_a_gauche():
    """Le partial partage ne change pas pour les autres exports : un seul bloc reste a gauche par defaut."""
    import os
    from jinja2 import Environment, FileSystemLoader
    tpl_dir = os.path.join(os.path.dirname(__file__), '..', 'api_backend', 'backend_app', 'utils', 'templates')
    env = Environment(loader=FileSystemLoader(tpl_dir))
    default = env.from_string("{% from '_pdf_signatures.html' import signature_block %}{{ signature_block([{'title': 'X'}]) }}").render()
    right = env.from_string("{% from '_pdf_signatures.html' import signature_block %}{{ signature_block([{'title': 'X'}], align='right') }}").render()
    assert 'sig-box sig-box-right' not in default
    assert 'sig-box sig-box-right' in right
