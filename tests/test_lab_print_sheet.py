# tests/test_lab_print_sheet.py
"""
Fiche de resultat labo imprimee (defaut 9, guides 2026-10-26) : sexe, valeurs de reference par sexe,
mot du drapeau, et jugement automatique du banc avec la plage du bon sexe.
Texte du PDF lu via pypdf (WeasyPrint sous-ensemble les polices).
"""
import io
import uuid
from datetime import date, datetime

from pypdf import PdfReader

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from controller.lab_controller import LabController
from models.lab import Examen, LabResult, LabResultDetail, Parametre, ReferenceRange
from repositories.lab_repo import LabRepository
from tests.conftest import create_test_user, create_test_patient, auth_headers

PWD = "Correct123!"


def _text(content: bytes) -> str:
    return "\n".join(" ".join((p.extract_text() or "").split()) for p in PdfReader(io.BytesIO(content)).pages)


class _FakeConfig:
    """Entete minimal : get_pdf_header_context lit le nom/logo configures."""


def _setup(db, tag, gender, birth=date(1990, 1, 1)):
    user = create_test_user(db, f"lps_{tag}", "admin", password=PWD)
    pid, _ = create_test_patient(db, user, first_name=f"Fiche{tag}", gender=gender, birth_date=birth)
    ex = Examen(code=f"PS-{uuid.uuid4().hex[:8]}", nom=f"NFS {tag}", categorie="Bio", prix=1000)
    db.add(ex)
    db.flush()
    glob = Parametre(examen_id=ex.id, nom_parametre="Hemoglobine", unite="g/dL", type_valeur="numeric", input_type="numeric")
    eryth = Parametre(examen_id=ex.id, nom_parametre="Erythrocytes", unite="T/L", type_valeur="numeric", input_type="numeric")
    db.add_all([glob, eryth])
    db.flush()
    db.add_all([
        ReferenceRange(parametre_id=glob.id, sexe="M", age_min=0, age_max=120, valeur_min=13, valeur_max=17),
        ReferenceRange(parametre_id=glob.id, sexe="F", age_min=0, age_max=120, valeur_min=12, valeur_max=15.5),
        ReferenceRange(parametre_id=eryth.id, sexe="M", age_min=0, age_max=120, valeur_min=4.5, valeur_max=6.5),
    ])
    r = LabResult(patient_id=pid, test_type=ex.nom, status="completed", examen_id=ex.id,
                  code_lab_patient=f"LAB-PS-{uuid.uuid4().hex[:8]}", test_date=datetime.now())
    db.add(r)
    db.flush()
    d1 = LabResultDetail(result_id=r.result_id, parametre_id=glob.id, valeur_text="16", valeur_num=16, flagged=True, interpretation="")
    d2 = LabResultDetail(result_id=r.result_id, parametre_id=eryth.id, valeur_text="5", valeur_num=5, flagged=False, interpretation="")
    db.add_all([d1, d2])
    db.flush()
    return user, r, glob, eryth


def _print_data(db, result_id):
    from controller.config_controller import ConfigController
    from repositories.config_repo import ConfigRepository
    ctrl = LabController(repo=LabRepository(db))
    return ctrl.get_print_data(result_id, ConfigController(repo=ConfigRepository(db)))


# ----------------------------------------------------------------- helpers purs

def test_normalize_sex_codes():
    from utils.lab_reference import normalize_sex
    assert normalize_sex("F") == "F"
    assert normalize_sex("female") == "F"
    assert normalize_sex("Femme") == "F"
    assert normalize_sex("M") == "M"
    assert normalize_sex("homme") == "M"
    assert normalize_sex(None) == "X"
    assert normalize_sex("O") == "X"
    assert normalize_sex("") == "X"


def test_select_range_prefers_exact_sex_then_generic_never_the_other_sex():
    from utils.lab_reference import select_range
    from types import SimpleNamespace as R
    m = R(sexe="M", age_min=0, age_max=120)
    f = R(sexe="F", age_min=0, age_max=120)
    x = R(sexe="X", age_min=0, age_max=120)
    assert select_range([m, f], "F", 30) is f
    assert select_range([m, f, x], "F", 30) is f
    assert select_range([m, x], "F", 30) is x
    assert select_range([m], "F", 30) is None          # plage masculine seule : rien pour une femme
    assert select_range([m, f], "X", 30) is None       # sexe inconnu : pas de choix arbitraire
    assert select_range([x], "X", 30) is x
    assert select_range([R(sexe="F", age_min=0, age_max=10)], "F", 30) is None
    assert select_range([R(sexe="F", age_min=0, age_max=10)], "F", None) is not None  # age inconnu : on ne filtre pas


# ------------------------------------------------------------------- donnees d'impression

def test_fiche_femme_affiche_le_sexe_et_la_plage_feminine(db_session):
    _, r, _, _ = _setup(db_session, "f1", "F")
    data = _print_data(db_session, r.result_id)
    assert data["patient"]["sexe"] == "Féminin"
    rows = {d["parametre_nom"]: d for d in data["details"]}
    assert rows["Hemoglobine"]["reference_str"] == "[12 - 15.5]"


def test_fiche_homme_affiche_la_plage_masculine(db_session):
    _, r, _, _ = _setup(db_session, "m1", "M")
    data = _print_data(db_session, r.result_id)
    assert data["patient"]["sexe"] == "Masculin"
    rows = {d["parametre_nom"]: d for d in data["details"]}
    assert rows["Hemoglobine"]["reference_str"] == "[13 - 17]"
    assert rows["Erythrocytes"]["reference_str"] == "[4.5 - 6.5]"


def test_plage_masculine_seule_n_est_jamais_imprimee_pour_une_femme(db_session):
    _, r, _, _ = _setup(db_session, "f2", "F")
    rows = {d["parametre_nom"]: d for d in _print_data(db_session, r.result_id)["details"]}
    assert rows["Erythrocytes"]["reference_str"] == "-"


def test_drapeau_manuel_sans_texte_imprime_un_mot(db_session):
    _, r, _, _ = _setup(db_session, "f3", "F")
    rows = {d["parametre_nom"]: d for d in _print_data(db_session, r.result_id)["details"]}
    assert rows["Hemoglobine"]["is_abnormal"] is True
    assert rows["Hemoglobine"]["interpretation"] == "Anormal"


def test_patient_externe_sexe_en_toutes_lettres(db_session):
    user = create_test_user(db_session, "lps_ext", "admin", password=PWD)
    ex = Examen(code=f"PS-{uuid.uuid4().hex[:8]}", nom="Glyc ext", categorie="Bio", prix=1000)
    db_session.add(ex)
    db_session.flush()
    r = LabResult(patient_id=None, external_patient_info={"nom": "Ext Femme", "age": 30, "sexe": "F"}, test_type="x",
                  status="completed", examen_id=ex.id, code_lab_patient=f"EXT-PS-{uuid.uuid4().hex[:8]}")
    db_session.add(r)
    db_session.flush()
    assert _print_data(db_session, r.result_id)["patient"]["sexe"] == "Féminin"


# ------------------------------------------------------------------------------ PDF rendu

def test_pdf_ne_montre_ni_X_ni_etoiles_vides_et_porte_la_plage_et_le_mot(db_session, api_client):
    user, r, _, _ = _setup(db_session, "f4", "F")
    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lps_f4", PWD)
    resp = client.get(f"/labo/results/{r.result_id}/pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    text = _text(resp.content)
    assert "Féminin" in text
    assert " X / " not in text
    assert "12 - 15.5" in text
    assert "* *" not in text
    assert "Anormal" in text


def test_pdf_dossier_complet_meme_correction(db_session, api_client):
    user, r, _, _ = _setup(db_session, "f5", "F")
    r.batch_id = uuid.uuid4()
    db_session.flush()
    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lps_f5", PWD)
    resp = client.get(f"/labo/batch/{r.batch_id}/pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    text = _text(resp.content)
    assert "Féminin" in text and "12 - 15.5" in text and "* *" not in text


# --------------------------------------------------------------- jugement automatique du banc

def _save(db, r, glob, value, flag=None, interp=None):
    d = db.query(LabResultDetail).filter_by(result_id=r.result_id, parametre_id=glob.id).first()
    repo = LabRepository(db)
    repo.save_results_values(r.result_id, {d.detail_id: {"valeur": value, "flag": flag, "interpretation": interp}}, False)
    db.refresh(d)
    return d


def _reopen(db, r):
    r.status = "partial"
    db.flush()


def test_banc_juge_une_femme_avec_la_plage_feminine(db_session):
    _, r, glob, _ = _setup(db_session, "f6", "F")
    _reopen(db_session, r)
    # 12.5 : normal pour une femme (12 - 15.5), BAS pour la plage masculine (13 - 17).
    d = _save(db_session, r, glob, 12.5)
    assert d.flagged is False and d.interpretation == "Normal"
    d = _save(db_session, r, glob, 16)
    assert d.flagged is True and d.interpretation == "Haut"


def test_banc_n_applique_pas_une_plage_d_un_autre_sexe(db_session):
    _, r, _, eryth = _setup(db_session, "f7", "F")
    _reopen(db_session, r)
    d = _save(db_session, r, eryth, 9)     # seule plage = masculine
    assert d.flagged is False and not d.interpretation


def test_banc_utilise_la_plage_generique_x(db_session):
    _, r, glob, _ = _setup(db_session, "f8", "F")
    db_session.query(ReferenceRange).filter_by(parametre_id=glob.id).delete()
    db_session.add(ReferenceRange(parametre_id=glob.id, sexe="X", age_min=0, age_max=120, valeur_min=1, valeur_max=2))
    db_session.flush()
    db_session.expire_all()
    _reopen(db_session, r)
    d = _save(db_session, r, glob, 5)
    assert d.flagged is True and d.interpretation == "Haut"


def test_drapeau_manuel_haut_sans_texte_est_enregistre_avec_son_mot(db_session):
    _, r, glob, _ = _setup(db_session, "f9", "F")
    _reopen(db_session, r)
    assert _save(db_session, r, glob, 14, flag="H").interpretation == "Haut"
    assert _save(db_session, r, glob, 14, flag="L").interpretation == "Bas"
    assert _save(db_session, r, glob, 14, flag="A").interpretation == "Anormal"
    d = _save(db_session, r, glob, 14, flag="H", interp="Controle")
    assert d.interpretation == "Controle" and d.flagged is True
