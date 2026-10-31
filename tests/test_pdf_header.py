# tests/test_pdf_header.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock
from api_backend.backend_app.utils.pdf_header import resolve_local_asset_path, get_ticket_header_context


def test_resolve_local_asset_path_returns_none_for_empty_url():
    assert resolve_local_asset_path(None) is None
    assert resolve_local_asset_path("") is None


def test_resolve_local_asset_path_returns_none_for_missing_file():
    assert resolve_local_asset_path("/static/uploads/logos/does-not-exist.png") is None


def test_resolve_local_asset_path_resolves_existing_relative_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("static/uploads/logos", exist_ok=True)
    with open("static/uploads/logos/real.png", "wb") as f:
        f.write(b"fake-png-bytes")
    result = resolve_local_asset_path("/static/uploads/logos/real.png")
    assert result is not None
    assert result.name == "real.png"


def test_get_ticket_header_context_no_logo_when_field_empty():
    structure = MagicMock(ticket_logo_url=None)
    config_ctrl = MagicMock()
    config_ctrl.get_structure_info.return_value = structure
    ctx = get_ticket_header_context(config_ctrl)
    assert ctx["structure"] is structure
    assert ctx["ticket_logo_path"] is None


def test_pdf_header_context_embeds_a_light_logo(tmp_path, monkeypatch):
    """Un logo source de ~3 Mo : le contexte des PDF pointe sur une copie reduite, l'original reste dispo, et
    l'image embarquee dans un PDF genere pese moins de 150 Ko."""
    import io
    from datetime import date
    from types import SimpleNamespace
    from urllib.parse import unquote, urlparse
    from pypdf import PdfReader
    from PIL import Image
    from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
    from api_backend.backend_app.utils.lab_sheet import render_lab_sheet
    from tests.test_lab_sheet_families import build

    monkeypatch.chdir(tmp_path)
    os.makedirs("static/uploads/logos", exist_ok=True)
    from PIL import ImageDraw
    side = 980  # RVB non compresse : ~2,9 Mo, comme un logo exporte tel quel d'un logiciel de dessin
    img = Image.new("RGB", (side, side), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((100, 100, side - 100, side - 100), fill=(20, 120, 60))
    draw.rectangle((350, 350, 630, 630), fill=(240, 240, 240))
    img.save("static/uploads/logos/big.png", compress_level=0)
    assert os.path.getsize("static/uploads/logos/big.png") > 2_000_000

    structure = SimpleNamespace(name="Centre Test Alpha", slogan=None, address="Rue 1", city="Douala", po_box=None,
                                phone="600000001", phone2=None, email="c@example.org", website=None,
                                agrement_number=None, niu=None, rccm=None, legal_info=None, footer_text=None,
                                signature_label_default=None, logo_url="/static/uploads/logos/big.png")
    cfg = MagicMock()
    cfg.get_structure_info.return_value = structure
    ctx = get_pdf_header_context(cfg)
    assert ctx["logo_path_original"].endswith("big.png")
    assert ctx["logo_path"] != ctx["logo_path_original"]
    light = os.path.getsize(unquote(urlparse(ctx["logo_path"]).path).lstrip("/"))
    assert light < 150_000

    context = dict(ctx, validation_date=date(2026, 10, 8), dossier_label="301/04 du 08/10/2026",
                   dossier_day=date(2026, 10, 8))
    pdf = render_lab_sheet(build("ASLO", ["150"]), {"name": "TESTEUR Jean", "prescriber": None}, context,
                           show_pregnancy=False)
    total = 0
    for page in PdfReader(io.BytesIO(pdf)).pages:
        for im in page.images:
            total += len(im.data)
    assert 0 < total < 150_000 * 4  # decoded size of a 400 px logo; the original would be ~6.7 MB


# --- logo : resolution independante du dossier de lancement (parcours navigateur 2026-10-31) -------------------

def _fake_logo(base, name="real.png", sub="static/uploads/logos"):
    target = os.path.join(str(base), *sub.split("/"))
    os.makedirs(target, exist_ok=True)
    with open(os.path.join(target, name), "wb") as f:
        f.write(b"fake-png-bytes")
    return os.path.join(target, name)


def test_logo_found_relative_to_repo_root_when_cwd_is_elsewhere(tmp_path, monkeypatch):
    from api_backend.backend_app.utils import pdf_header
    elsewhere, repo, api = tmp_path / "elsewhere", tmp_path / "repo", tmp_path / "api"
    for d in (elsewhere, repo, api):
        d.mkdir()
    expected = _fake_logo(repo)
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(pdf_header, "_REPO_ROOT", repo)
    monkeypatch.setattr(pdf_header, "_API_DIR", api)
    assert str(resolve_local_asset_path("/static/uploads/logos/real.png")) == os.path.realpath(expected)


def test_logo_found_relative_to_api_backend_dir_when_not_at_repo_root(tmp_path, monkeypatch):
    from api_backend.backend_app.utils import pdf_header
    elsewhere, repo, api = tmp_path / "elsewhere", tmp_path / "repo", tmp_path / "api"
    for d in (elsewhere, repo, api):
        d.mkdir()
    expected = _fake_logo(api)
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(pdf_header, "_REPO_ROOT", repo)
    monkeypatch.setattr(pdf_header, "_API_DIR", api)
    assert str(resolve_local_asset_path("/static/uploads/logos/real.png")) == os.path.realpath(expected)


def test_logo_cwd_wins_then_repo_then_api_and_container_layout(tmp_path, monkeypatch):
    from api_backend.backend_app.utils import pdf_header
    cwd, repo, api, app = (tmp_path / n for n in ("cwd", "repo", "api", "app"))
    for d in (cwd, repo, api, app):
        d.mkdir()
    in_cwd = _fake_logo(cwd)
    _fake_logo(repo)
    _fake_logo(api)
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(pdf_header, "_REPO_ROOT", repo)
    monkeypatch.setattr(pdf_header, "_API_DIR", api)
    monkeypatch.setattr(pdf_header, "_CONTAINER_ROOT", app)
    assert str(resolve_local_asset_path("/static/uploads/logos/real.png")) == os.path.realpath(in_cwd)
    os.remove(in_cwd)
    assert os.path.realpath(str(resolve_local_asset_path("/static/uploads/logos/real.png"))).startswith(os.path.realpath(str(repo)))
    # conteneur : seul /app/static/uploads/... contient le fichier
    only_app = _fake_logo(app, "only_app.png")
    assert str(resolve_local_asset_path("/static/uploads/logos/only_app.png")) == os.path.realpath(only_app)


def test_logo_absolute_legacy_url_and_dir_constants_fallback(tmp_path, monkeypatch):
    from api_backend.backend_app.utils import pdf_header
    repo = tmp_path / "repo"
    repo.mkdir()
    expected = _fake_logo(repo, "legacy.png")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pdf_header, "_REPO_ROOT", repo)
    # URL absolue d'avant la convention : seul le chemin compte
    assert str(resolve_local_asset_path("http://old-host:8000/static/uploads/logos/legacy.png")) == os.path.realpath(expected)
    # prefixe inconnu : repli sur le nom du fichier dans le dossier d'envoi configure
    assert str(resolve_local_asset_path("/media/other/legacy.png")) == os.path.realpath(expected)
    # jamais de sortie du depot par « .. »
    assert resolve_local_asset_path("/static/../../etc/passwd") is None


def test_upload_dir_constants_mirror_config_controller():
    from api_backend.backend_app.utils import pdf_header
    from controller import config_controller
    assert pdf_header.UPLOAD_DIR == config_controller.UPLOAD_DIR
    assert pdf_header.TICKET_LOGO_UPLOAD_DIR == config_controller.TICKET_LOGO_UPLOAD_DIR


def test_header_context_and_light_logo_use_the_same_lookup_from_any_cwd(tmp_path, monkeypatch):
    from PIL import Image
    from api_backend.backend_app.utils import pdf_header
    repo, elsewhere = tmp_path / "repo", tmp_path / "elsewhere"
    repo.mkdir()
    elsewhere.mkdir()
    logo_dir = repo / "static" / "uploads" / "logos"
    logo_dir.mkdir(parents=True)
    Image.new("RGB", (900, 700), (10, 90, 160)).save(logo_dir / "big.png")
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(pdf_header, "_REPO_ROOT", repo)
    monkeypatch.setattr(pdf_header, "_API_DIR", tmp_path / "none")
    config_ctrl = MagicMock()
    config_ctrl.get_structure_info.return_value = MagicMock(logo_url="/static/uploads/logos/big.png")
    ctx = pdf_header.get_pdf_header_context(config_ctrl)
    assert ctx["logo_path_original"] and ctx["logo_path"] and ctx["logo_path"] != ctx["logo_path_original"]
    # le chemin /static/... brut passe aussi par light_logo (meme assistant) et donne une copie reduite
    assert pdf_header.light_logo("/static/uploads/logos/big.png").startswith("file:")
    assert pdf_header.light_logo("/static/uploads/logos/missing.png") == "/static/uploads/logos/missing.png"


# --- en-tete : prefixes deja presents dans la valeur enregistree -----------------------------------------------

def _header_lines(template, **fields):
    from jinja2 import Environment, FileSystemLoader
    from types import SimpleNamespace
    base = dict(name="Centre", slogan=None, address="Rue 1", city="Ville", po_box=None, phone=None, phone2=None,
                email=None, website=None, niu=None, rccm=None, legal_info=None, agrement_number=None,
                footer_text=None)
    base.update(fields)
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "..", "api_backend",
                                                           "backend_app", "utils", "templates")))
    html = env.get_template(template).render(structure=SimpleNamespace(**base), logo_path=None)
    return html.split("</style>", 1)[1] if "</style>" in html else html


@pytest.mark.parametrize("template", ["_pdf_header.html", "_lab_sheet_header.html"])
def test_header_does_not_double_the_bp_prefix(template):
    for stored in ("BP: 06", "bp:06", "B.P. 06", "BP 06"):
        out = _header_lines(template, po_box=stored)
        assert out.count("BP") + out.count("bp") + out.count("B.P") == 1, (template, stored)
        assert "BP: BP" not in out and stored in out
    assert "BP: 06" in _header_lines(template, po_box="06")
    assert "| BP: 06" in _header_lines(template, po_box="  06  ")


@pytest.mark.parametrize("template", ["_pdf_header.html", "_lab_sheet_header.html"])
def test_header_does_not_double_the_phone_label(template):
    out = _header_lines(template, phone="Tel : 677000001")
    assert "Tel : 677000001" in out and out.count("Tel") + out.count("Tél") == 1
    assert out.count("677000001") == 1
    out = _header_lines(template, phone="677000001")
    assert out.count("Tel") + out.count("Tél") == 1


def test_lab_header_does_not_double_the_email_label():
    out = _header_lines("_lab_sheet_header.html", email="Email : a@example.org", phone="677000001")
    assert out.count("mail") == 1 and "Email : a@example.org" in out
    out = _header_lines("_lab_sheet_header.html", email="a@example.org", phone="677000001")
    assert "Email : a@example.org" in out and out.count("mail") == 1
