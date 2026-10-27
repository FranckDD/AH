# tests/test_pharmacy_photo.py
"""Photo des produits : redimensionnement, stockage hors /static, roles, versions."""
import io
import os
from unittest.mock import MagicMock

import pytest
from PIL import Image

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.pharmacy import pharmacy_endpoints
from models.pharmacy import Pharmacy
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
ROLES = ("admin", "Assistant", "ToxicoManager", "secretaire", "StockController")


@pytest.fixture(scope="module", autouse=True)
def _no_redis_no_celery():
    mp = pytest.MonkeyPatch()
    mp.setattr("controller.pharmacy_controller.task_check_low_stock_alert", MagicMock())
    mp.setattr("controller.pharmacy_controller.redis_client", MagicMock(get=MagicMock(return_value=None)))
    mp.setattr("controller.patient_controller.redis_client", MagicMock())
    yield
    mp.undo()


@pytest.fixture
def photo_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCT_PHOTO_DIR", str(tmp_path / "photos"))
    return tmp_path / "photos"


@pytest.fixture
def env(db_session, api_client, photo_dir):
    for r in ROLES:
        create_test_user(db_session, f"t_ph_{r.lower()}", r, password=PWD)
    client = api_client(auth_endpoints, pharmacy_endpoints)

    class _Heads(dict):
        def __missing__(self, role):
            self[role] = auth_headers(client, f"t_ph_{role.lower()}", PWD)
            return self[role]

    p = Pharmacy(drug_name="TEST_PH_PROD", quantity=3, threshold=1, medication_type="pharmaceutique",
                 forme="Autre", price=10, stock_status="normal")
    db_session.add(p)
    db_session.flush()
    return {"db": db_session, "client": client, "h": _Heads(), "pid": p.medication_id, "dir": photo_dir}


def _png(w=1200, h=800):
    img = Image.effect_noise((w, h), 80).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _put(env, role="admin", data=None, name="p.png", ctype="image/png", pid=None):
    data = _png() if data is None else data
    return env["client"].put(f"/pharmacy/{pid or env['pid']}/photo",
                             files={"file": (name, data, ctype)}, headers=env["h"][role])


def _files(env):
    return sorted(os.listdir(env["dir"])) if env["dir"].exists() else []


def test_upload_resizes_to_small_jpeg(env):
    r = _put(env)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_photo"] is True and body["photo_version"] == 1
    files = _files(env)
    assert len(files) == 1 and files[0].endswith(".jpg") and len(files[0]) == 36
    path = env["dir"] / files[0]
    assert path.stat().st_size <= 100 * 1024
    with Image.open(path) as img:
        assert img.format == "JPEG" and max(img.size) <= 480
    g = env["client"].get(f"/pharmacy/{env['pid']}/photo", headers=env["h"]["admin"])
    assert g.status_code == 200 and g.headers["content-type"] == "image/jpeg"
    assert "private" in g.headers["cache-control"]
    assert g.content == path.read_bytes()


def test_upload_rejects_non_image_and_oversize(env):
    r = _put(env, data=b"%PDF-1.4 not an image", name="x.pdf", ctype="application/pdf")
    assert r.status_code == 400
    assert r.json()["detail"].isascii()
    big = _put(env, data=b"\x00" * (5 * 1024 * 1024 + 10))
    assert big.status_code == 413
    assert big.json()["detail"].isascii()
    assert _files(env) == []
    env["db"].expire_all()
    assert env["db"].get(Pharmacy, env["pid"]).photo_version == 0


def test_photo_requires_login(env):
    c = env["client"]
    assert c.get(f"/pharmacy/{env['pid']}/photo").status_code == 401
    assert c.put(f"/pharmacy/{env['pid']}/photo",
                 files={"file": ("p.png", _png(50, 50), "image/png")}).status_code == 401
    assert c.delete(f"/pharmacy/{env['pid']}/photo").status_code == 401


def test_photo_roles(env):
    assert _put(env, "admin").status_code == 200
    for role in ("admin", "Assistant", "ToxicoManager", "secretaire"):
        assert env["client"].get(f"/pharmacy/{env['pid']}/photo", headers=env["h"][role]).status_code == 200, role
    assert env["client"].get(f"/pharmacy/{env['pid']}/photo", headers=env["h"]["StockController"]).status_code == 403
    for role in ("secretaire", "StockController"):
        assert _put(env, role, _png(50, 50)).status_code == 403, role
        assert env["client"].delete(f"/pharmacy/{env['pid']}/photo", headers=env["h"][role]).status_code == 403, role
    for role in ("Assistant", "ToxicoManager"):
        assert _put(env, role, _png(50, 50)).status_code == 200, role
        assert env["client"].delete(f"/pharmacy/{env['pid']}/photo", headers=env["h"][role]).status_code == 200, role


def test_replace_bumps_version_and_removes_old_file(env):
    assert _put(env).json()["photo_version"] == 1
    first = _files(env)
    r = _put(env, data=_png(900, 900))
    assert r.json()["photo_version"] == 2
    second = _files(env)
    assert len(second) == 1 and second != first


def test_delete_photo(env):
    _put(env)
    r = env["client"].delete(f"/pharmacy/{env['pid']}/photo", headers=env["h"]["admin"])
    assert r.status_code == 200
    assert r.json()["has_photo"] is False and r.json()["photo_version"] == 2
    assert _files(env) == []
    assert env["client"].get(f"/pharmacy/{env['pid']}/photo", headers=env["h"]["admin"]).status_code == 404


def test_get_without_photo_404_and_unknown_product_404(env):
    h = env["h"]["secretaire"]
    assert env["client"].get(f"/pharmacy/{env['pid']}/photo", headers=h).status_code == 404
    assert env["client"].get("/pharmacy/99999999/photo", headers=h).status_code == 404
    assert _put(env, pid=99999999).status_code == 404


def test_product_response_has_photo_fields_and_stock_untouched(env):
    r = env["client"].get(f"/pharmacy/{env['pid']}", headers=env["h"]["secretaire"]).json()
    assert r["has_photo"] is False and r["photo_version"] == 0
    _put(env)
    r = env["client"].get(f"/pharmacy/{env['pid']}", headers=env["h"]["secretaire"]).json()
    assert r["has_photo"] is True and r["quantity"] == 3


def test_pixel_bomb_refused_without_writing(env, monkeypatch):
    from api_backend.backend_app.utils import product_photos
    monkeypatch.setattr(product_photos, "PHOTO_MAX_PIXELS", 1000)
    r = _put(env, data=_png(100, 100))
    assert r.status_code == 400 and r.json()["detail"].isascii()
    assert _files(env) == []


def test_declared_huge_png_refused_cheaply(env):
    import struct
    import zlib

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)

    ihdr = struct.pack(">IIBBBBB", 100000, 100000, 8, 2, 0, 0, 0)
    bomb = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"\x00" * 10)) + chunk(b"IEND", b"")
    r = _put(env, data=bomb)
    assert r.status_code == 400 and _files(env) == []


def test_valid_header_corrupt_data_is_400(env):
    data = _png(200, 200)
    r = _put(env, data=data[:100] + b"\x00" * 400)
    assert r.status_code == 400 and _files(env) == []


def test_exif_failure_is_400_not_500(env, monkeypatch):
    from api_backend.backend_app.utils import product_photos
    calls = []

    def boom(img):
        calls.append(1)
        raise ValueError("malformed exif")

    monkeypatch.setattr(product_photos.ImageOps, "exif_transpose", boom)
    r = _put(env, data=_png(100, 100))
    assert calls, "exif_transpose was not reached"
    assert r.status_code == 400 and r.json()["detail"].isascii()
    assert _files(env) == []


def test_concurrent_decodes_keep_truncated_flag(monkeypatch):
    import threading
    from PIL import ImageFile
    from api_backend.backend_app.utils.product_photos import shrink_to_jpeg
    monkeypatch.setattr(ImageFile, "LOAD_TRUNCATED_IMAGES", True)
    data = _png(300, 300)
    errors = []

    def run():
        try:
            for _ in range(5):
                shrink_to_jpeg(data)
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=run) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert ImageFile.LOAD_TRUNCATED_IMAGES is True


def test_delete_product_removes_photo_file(env):
    assert _put(env).status_code == 200
    assert len(_files(env)) == 1
    r = env["client"].delete(f"/pharmacy/{env['pid']}", headers=env["h"]["admin"])
    assert r.status_code == 204, r.text
    assert _files(env) == []


def test_failed_product_delete_keeps_photo_file(env, monkeypatch):
    from repositories.pharmacy_repo import PharmacyRepository
    assert _put(env).status_code == 200

    def boom(self, medication_id):
        raise RuntimeError("commit failed")

    monkeypatch.setattr(PharmacyRepository, "delete", boom)
    r = env["client"].delete(f"/pharmacy/{env['pid']}", headers=env["h"]["admin"])
    assert r.status_code == 500
    assert len(_files(env)) == 1
