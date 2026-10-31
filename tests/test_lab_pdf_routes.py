# tests/test_lab_pdf_routes.py
"""
Branchement des routes PDF du laboratoire sur les fiches (D3) : un resultat valide avec copie figee s'imprime avec
le gabarit de sa famille (une fiche par examen), un passage a plusieurs examens donne UN PDF dont les pages suivent
l'ordre du passage, les anciens resultats gardent l'ancien PDF, la fiche exige le numero de dossier, la reimpression
est identique meme si le catalogue change. Patients inventes. Texte lu via pypdf.
"""
import io
import time
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from pypdf import PdfReader

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from models.lab import Examen, LabResult, LabResultDetail, Parametre, ReferenceRange
from repositories.lab_repo import LabRepository
from tests.conftest import auth_headers, create_test_patient, create_test_user
from utils.business_time import business_now
from utils.lab_dossier import assign_dossier, build_patient_key

PWD = "Correct123!"
OLD_MARKER = "Le chef du laboratoire"
_DAY = [0]


@pytest.fixture(autouse=True)
def _quiet_font_subsetting_logs():
    """fontTools journalise chaque table au niveau DEBUG: pytest les capture et ralentit chaque rendu de ~10x
    (en production le niveau est INFO ou plus)."""
    import logging
    names = ("fontTools", "weasyprint", "fontTools.subset", "fontTools.ttLib.ttFont", "fontTools.subset.timer")
    saved = [(n, logging.getLogger(n).level) for n in names]
    for n in names:
        logging.getLogger(n).setLevel(logging.WARNING)
    yield
    for n, lv in saved:
        logging.getLogger(n).setLevel(lv)


def _text(content: bytes) -> str:
    return "\n".join(" ".join((p.extract_text() or "").split()) for p in PdfReader(io.BytesIO(content)).pages)


def _pages(content: bytes) -> list:
    return [" ".join((p.extract_text() or "").split()) for p in PdfReader(io.BytesIO(content)).pages]


def _client(api_client, username):
    client = api_client(auth_endpoints, lab_endpoints)
    return client, auth_headers(client, username, PWD)


def _exam(db, tag, family, labels):
    ex = Examen(code=f"PR-{uuid.uuid4().hex[:8]}", nom=f"Examen {tag}", categorie="Bio", prix=1000,
                section="BIOCHIMIE", method="Methode test", layout_family=family, signature_label=f"Sig {tag}",
                print_title=f"TITRE {tag}", sort_order=1)
    db.add(ex)
    db.flush()
    params = []
    for i, label in enumerate(labels, start=1):
        p = Parametre(examen_id=ex.id, nom_parametre=f"nom{tag}{i}", unite="g/L", type_valeur="numeric",
                      input_type="numeric", ordre=i, print_label=label)
        db.add(p)
        db.flush()
        db.add(ReferenceRange(parametre_id=p.id, sexe="X", age_min_days=0, age_max_days=None,
                              valeur_min=Decimal("0.70"), valeur_max=Decimal("1.10")))
        params.append(p)
    db.flush()
    return ex, params


def _validated(db, pid, lab, ex, params, *, batch=None, dossier=True, pregnancy=None, value="0.9", validate=True):
    kw = {}
    if pregnancy:
        kw = {"pregnancy_status_at_result": pregnancy[0], "gestational_age_weeks": pregnancy[1]}
    r = LabResult(patient_id=pid, test_type=ex.nom, status="pending", examen_id=ex.id, batch_id=batch,
                  code_lab_patient=f"LAB-PR-{uuid.uuid4().hex[:8]}", test_date=business_now(),
                  prescribed_by_name="Dr Prescripteur Test", **kw)
    if dossier:
        _DAY[0] += 1
        day = date(2095, 1, 1) + timedelta(days=_DAY[0] % 360)
        key = build_patient_key(patient_id=pid)
        num = assign_dossier(db, key, day)
        r.patient_key, r.dossier_year, r.dossier_counter, r.dossier_rank = key, num.year, num.counter, num.rank
    db.add(r)
    db.flush()
    details = []
    for p in params:
        d = LabResultDetail(result_id=r.result_id, parametre_id=p.id, valeur_text="", valeur_num=None, flagged=False)
        db.add(d)
        details.append(d)
    db.flush()
    if validate:
        LabRepository(db).save_results_values(
            r.result_id, {d.detail_id: {"valeur": value} for d in details}, mark_completed=True,
            global_note=None, global_conclusion=None, user_id=lab.user_id)
        db.flush()
        db.refresh(r)
    return r, details


def _setup(db, tag, role="laborantin", gender="F"):
    lab = create_test_user(db, f"pr_{tag}", role, password=PWD)
    pid, _ = create_test_patient(db, lab, first_name=f"Prn{tag}", last_name=f"Nom{tag}", gender=gender,
                                 birth_date=date(1990, 5, 5))
    return lab, pid


def _old_result(db, pid, batch=None, tag="o"):
    ex = Examen(code=f"PO-{uuid.uuid4().hex[:8]}", nom=f"Ancien {tag}", categorie="Bio", prix=1000)
    db.add(ex)
    db.flush()
    p = Parametre(examen_id=ex.id, nom_parametre=f"ParamAncien{tag}", unite="g/L", type_valeur="numeric")
    db.add(p)
    db.flush()
    r = LabResult(patient_id=pid, test_type=ex.nom, status="completed", examen_id=ex.id, batch_id=batch,
                  code_lab_patient=f"LAB-OLD-{uuid.uuid4().hex[:8]}", test_date=datetime.now() - timedelta(minutes=1))
    db.add(r)
    db.flush()
    db.add(LabResultDetail(result_id=r.result_id, parametre_id=p.id, valeur_text="7", valeur_num=7, flagged=False))
    db.flush()
    return r


# ------------------------------------------------------------------ un resultat, une fiche par famille

FAMILIES = [("table", ["Hemoglobine zz", "Hematocrite zz", "Leucocytes zz"]),
            ("three_columns", ["Glycemie zz", "Uree zz"]),
            ("label_value", ["Aspect zz", "Couleur zz"]),
            ("boxed", ["Resultat zz"]),
            ("narrative", ["Compte rendu zz"])]


@pytest.mark.parametrize("family,labels", FAMILIES)
def test_fiche_de_la_famille_une_page_libelles_dans_l_ordre(db_session, api_client, family, labels):
    lab, pid = _setup(db_session, f"f{family[:3]}")
    ex, params = _exam(db_session, family[:3], family, labels)
    r, _ = _validated(db_session, pid, lab, ex, params)
    client, headers = _client(api_client, f"pr_f{family[:3]}")

    resp = client.get(f"/labo/results/{r.result_id}/pdf", headers=headers)

    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.headers["content-disposition"] == f'attachment; filename="Resultat_{r.code_lab_patient}.pdf"'
    pages = _pages(resp.content)
    assert len(pages) == 1
    txt = pages[0]
    positions = [txt.index(label) for label in labels]
    assert positions == sorted(positions)
    assert OLD_MARKER not in txt                    # pas l'ancien gabarit
    assert f"Nomf{family[:3]}".lower() in txt.lower()
    assert "Dr Prescripteur Test" in txt


def test_cache_control_no_store_sur_les_deux_routes_et_l_ancien_chemin(db_session, api_client):
    lab, pid = _setup(db_session, "cc")
    ex, params = _exam(db_session, "cc", "table", ["Param cc"])
    batch = uuid.uuid4()
    r, _ = _validated(db_session, pid, lab, ex, params, batch=batch)
    old = _old_result(db_session, pid, tag="cc")
    client, headers = _client(api_client, "pr_cc")

    for url in (f"/labo/results/{r.result_id}/pdf", f"/labo/batch/{batch}/pdf", f"/labo/results/{old.result_id}/pdf"):
        resp = client.get(url, headers=headers)
        assert resp.status_code == 200, (url, resp.text)
        assert resp.headers["cache-control"] == "no-store, private"


# ------------------------------------------------------------------ passage a plusieurs examens

def test_passage_plusieurs_examens_un_pdf_une_fiche_par_examen_dans_l_ordre(db_session, api_client):
    lab, pid = _setup(db_session, "mp")
    batch = uuid.uuid4()
    labels = [("table", "Alpha mp"), ("boxed", "Bravo mp"), ("label_value", "Charlie mp"), ("narrative", "Delta mp")]
    for fam, lab_text in labels:
        ex, params = _exam(db_session, lab_text[:3], fam, [lab_text])
        _validated(db_session, pid, lab, ex, params, batch=batch)
    client, headers = _client(api_client, "pr_mp")

    resp = client.get(f"/labo/batch/{batch}/pdf", headers=headers)

    assert resp.status_code == 200, resp.text
    pages = _pages(resp.content)
    assert len(pages) == 4
    for page, (_, text) in zip(pages, labels):
        assert text in page
        assert page.count("Nommp") == 1
    assert resp.headers["content-disposition"].startswith('attachment; filename="Dossier_LAB-PR-')


def test_passage_mixte_ancien_et_nouveau_chacun_son_chemin(db_session, api_client):
    lab, pid = _setup(db_session, "mx")
    batch = uuid.uuid4()
    old = _old_result(db_session, pid, batch=batch, tag="mx")
    ex, params = _exam(db_session, "mx", "table", ["Param nouveau mx"])
    _validated(db_session, pid, lab, ex, params, batch=batch)
    client, headers = _client(api_client, "pr_mx")

    resp = client.get(f"/labo/batch/{batch}/pdf", headers=headers)

    assert resp.status_code == 200, resp.text
    pages = _pages(resp.content)
    assert len(pages) == 2
    assert "ParamAncienmx" in pages[0] and OLD_MARKER in pages[0]       # ancien resultat d'abord (id plus petit)
    assert "Param nouveau mx" in pages[1] and OLD_MARKER not in pages[1]


def test_passage_sans_aucune_copie_garde_l_ancien_pdf_dossier_complet(db_session, api_client):
    lab, pid = _setup(db_session, "ob")
    batch = uuid.uuid4()
    _old_result(db_session, pid, batch=batch, tag="ob1")
    _old_result(db_session, pid, batch=batch, tag="ob2")
    client, headers = _client(api_client, "pr_ob")

    resp = client.get(f"/labo/batch/{batch}/pdf", headers=headers)

    assert resp.status_code == 200
    txt = _text(resp.content)
    assert "ParamAncienob1" in txt and "ParamAncienob2" in txt
    assert txt.count(OLD_MARKER) == 1                  # ancien dossier complet : une seule signature
    assert len(_pages(resp.content)) == 1


def test_batch_inconnu_ou_sans_examen_termine_garde_404_et_409(db_session, api_client):
    lab, pid = _setup(db_session, "e4")
    batch = uuid.uuid4()
    ex, params = _exam(db_session, "e4", "table", ["Param e4"])
    _validated(db_session, pid, lab, ex, params, batch=batch, validate=False)
    client, headers = _client(api_client, "pr_e4")

    assert client.get(f"/labo/batch/{uuid.uuid4()}/pdf", headers=headers).status_code == 404
    assert client.get(f"/labo/batch/{batch}/pdf", headers=headers).status_code == 409


def test_gros_passage_de_30_examens_en_moins_de_30_secondes(db_session, api_client):
    lab, pid = _setup(db_session, "bg")
    batch = uuid.uuid4()
    for i in range(30):
        ex, params = _exam(db_session, f"b{i:02d}", "table", [f"Param bg{i:02d}"])
        _validated(db_session, pid, lab, ex, params, batch=batch)
    client, headers = _client(api_client, "pr_bg")

    start = time.time()
    resp = client.get(f"/labo/batch/{batch}/pdf", headers=headers)
    elapsed = time.time() - start

    assert resp.status_code == 200, resp.text
    pages = _pages(resp.content)
    assert len(pages) == 30
    assert all(f"Param bg{i:02d}" in pages[i] for i in range(30))
    assert elapsed < 30, f"{elapsed:.1f} s"


# ------------------------------------------------------------------ ancien chemin et numero de dossier

def test_resultat_sans_copie_garde_l_ancien_gabarit(db_session, api_client):
    lab, pid = _setup(db_session, "ol")
    old = _old_result(db_session, pid, tag="ol")
    client, headers = _client(api_client, "pr_ol")

    resp = client.get(f"/labo/results/{old.result_id}/pdf", headers=headers)

    assert resp.status_code == 200
    txt = _text(resp.content)
    assert "ParamAncienol" in txt and OLD_MARKER in txt
    assert resp.headers["content-disposition"] == f'attachment; filename="Resultat_{old.code_lab_patient}.pdf"'


def test_numero_de_dossier_absent_est_attribue_a_l_impression_jamais_de_409(db_session, api_client):
    lab, pid = _setup(db_session, "nd")
    ex, params = _exam(db_session, "nd", "table", ["Param nd"])
    batch = uuid.uuid4()
    r, _ = _validated(db_session, pid, lab, ex, params, batch=batch, dossier=False)
    assert r.print_snapshot is not None
    client, headers = _client(api_client, "pr_nd")

    for url in (f"/labo/results/{r.result_id}/pdf", f"/labo/batch/{batch}/pdf"):
        resp = client.get(url, headers=headers)
        assert resp.status_code == 200, url
    db_session.expire_all()
    assert db_session.get(LabResult, r.result_id).dossier_counter is not None


def test_resultat_inconnu_404(db_session, api_client):
    _setup(db_session, "nf")
    client, headers = _client(api_client, "pr_nf")
    assert client.get("/labo/results/999999999/pdf", headers=headers).status_code == 404


# ------------------------------------------------------------------ reimpression

def test_reimpression_identique_et_catalogue_modifie_sans_effet(db_session, api_client):
    lab, pid = _setup(db_session, "rp")
    ex, params = _exam(db_session, "rp", "table", ["Hemoglobine rp", "Hematocrite rp"])
    r, _ = _validated(db_session, pid, lab, ex, params)
    client, headers = _client(api_client, "pr_rp")
    url = f"/labo/results/{r.result_id}/pdf"

    first = _text(client.get(url, headers=headers).content)
    assert first == _text(client.get(url, headers=headers).content)

    # le catalogue change apres la validation : libelle, unite, norme, ordre, famille, signature
    params[0].print_label = "RENOMME rp"
    params[0].unite = "mmol/L"
    params[0].ordre = 9
    params[1].ordre = 1
    ex.layout_family = "boxed"
    ex.signature_label = "Autre signataire"
    ex.print_title = "NOUVEAU TITRE"
    for rng in db_session.query(ReferenceRange).filter(ReferenceRange.parametre_id == params[0].id):
        rng.valeur_min, rng.valeur_max = Decimal("5"), Decimal("9")
    db_session.flush()

    after = _text(client.get(url, headers=headers).content)
    assert after == first
    assert "RENOMME" not in after and "Autre signataire" not in after


def test_amendement_imprime_la_nouvelle_copie(db_session, api_client):
    lab, pid = _setup(db_session, "am")
    ex, params = _exam(db_session, "am", "label_value", ["Glycemie am"])
    r, details = _validated(db_session, pid, lab, ex, params, value="0.9")
    client, headers = _client(api_client, "pr_am")
    url = f"/labo/results/{r.result_id}/pdf"
    before = _text(client.get(url, headers=headers).content)
    assert "0,9" in before or "0.9" in before

    LabRepository(db_session).amend_result(r.result_id, {details[0].detail_id: {"valeur": "1.75"}}, None,
                                           "Erreur de saisie", user_id=lab.user_id, user_name="Editeur")
    db_session.flush()
    db_session.expire_all()

    after = _text(client.get(url, headers=headers).content)
    assert "1,75" in after or "1.75" in after
    assert "0,9" not in after.replace("1,75", "")
    db_session.refresh(db_session.get(LabResult, r.result_id))
    assert len(db_session.get(LabResult, r.result_id).print_snapshot_history) == 1     # l'historique reste disponible


# ------------------------------------------------------------------ roles et grossesse

def test_matrice_des_roles_acces_inchange(db_session, api_client):
    lab, pid = _setup(db_session, "rm")
    ex, params = _exam(db_session, "rm", "table", ["Param rm"])
    r, _ = _validated(db_session, pid, lab, ex, params)
    users = {}
    for role in ("admin", "laborantin", "ToxicoManager", "medecin", "nurse", "secretaire"):
        name = f"pr_rm_{role.lower()}"
        create_test_user(db_session, name, role, password=PWD)
        users[role] = name
    client = api_client(auth_endpoints, lab_endpoints)

    for role, name in users.items():
        resp = client.get(f"/labo/results/{r.result_id}/pdf", headers=auth_headers(client, name, PWD))
        expected = 403 if role == "secretaire" else 200
        assert resp.status_code == expected, (role, resp.status_code)
    assert client.get(f"/labo/results/{r.result_id}/pdf").status_code in (401, 403)


def test_medecin_et_infirmier_n_obtiennent_pas_un_resultat_non_termine(db_session, api_client):
    lab, pid = _setup(db_session, "nt")
    ex, params = _exam(db_session, "nt", "table", ["Param nt"])
    r, _ = _validated(db_session, pid, lab, ex, params, validate=False)
    create_test_user(db_session, "pr_nt_med", "medecin", password=PWD)
    client, headers = _client(api_client, "pr_nt_med")
    assert client.get(f"/labo/results/{r.result_id}/pdf", headers=headers).status_code == 403


def test_grossesse_imprimee_pour_les_lecteurs_absente_pour_les_autres(db_session, api_client):
    lab, pid = _setup(db_session, "gr")
    ex, params = _exam(db_session, "gr", "table", ["Param gr"])
    batch = uuid.uuid4()
    r, _ = _validated(db_session, pid, lab, ex, params, pregnancy=("enceinte", 22), batch=batch)
    assert r.print_snapshot["pregnancy"]["gestational_age_weeks"] == 22
    create_test_user(db_session, "pr_gr_tox", "ToxicoManager", password=PWD)
    create_test_user(db_session, "pr_gr_med", "medecin", password=PWD)
    client = api_client(auth_endpoints, lab_endpoints)

    for url in (f"/labo/results/{r.result_id}/pdf", f"/labo/batch/{batch}/pdf"):
        viewer = _text(client.get(url, headers=auth_headers(client, "pr_gr_med", PWD)).content)
        assert "22 SA" in viewer and "Enceinte" in viewer
        other = _text(client.get(url, headers=auth_headers(client, "pr_gr_tox", PWD)).content)
        assert "22 SA" not in other and "Enceinte" not in other and "rossesse" not in other
        assert "Param gr" in other                            # la fiche reste imprimee
    # la copie stockee n'a pas ete modifiee par l'impression
    db_session.expire_all()
    assert db_session.get(LabResult, r.result_id).print_snapshot["pregnancy"]["gestational_age_weeks"] == 22
