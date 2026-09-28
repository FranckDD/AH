# tests/test_config_controller.py
import sys
import os
import io
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from controller.config_controller import _generate_safe_filename, _validate_image_content


def test_generate_safe_filename_strips_path_traversal():
    result = _generate_safe_filename("../../etc/passwd.png")
    assert "/" not in result
    assert ".." not in result
    assert result.endswith(".png")


def test_generate_safe_filename_rejects_disallowed_extension():
    with pytest.raises(ValueError):
        _generate_safe_filename("script.svg")


def test_generate_safe_filename_rejects_double_extension_trick():
    with pytest.raises(ValueError):
        _generate_safe_filename("logo.png.exe")


def test_validate_image_content_accepts_real_png():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format="PNG")
    buf.seek(0)
    _validate_image_content(buf)  # ne doit pas lever


def test_validate_image_content_rejects_non_image_bytes():
    buf = io.BytesIO(b"ceci n'est pas une image")
    with pytest.raises(ValueError):
        _validate_image_content(buf)


def test_save_uploaded_image_rejects_oversized_file(tmp_path, monkeypatch):
    from controller.config_controller import ConfigController, MAX_UPLOAD_SIZE_BYTES
    import io

    class FakeUploadFile:
        filename = "big.png"
        def __init__(self, data):
            self.file = io.BytesIO(data)

    monkeypatch.chdir(tmp_path)
    ctrl = ConfigController(repo=None)
    oversized = FakeUploadFile(b"0" * (MAX_UPLOAD_SIZE_BYTES + 1))
    with pytest.raises(ValueError, match="taille maximale"):
        ctrl._save_uploaded_image(oversized, "static/uploads/ticket_logos")


def test_generate_ticket_print_token_returns_url_safe_random_string():
    from controller.config_controller import ConfigController
    ctrl = ConfigController(repo=None)
    token = ctrl.generate_ticket_print_token()
    assert isinstance(token, str)
    assert len(token) >= 32
    # genere deux fois -> jamais le meme jeton (evite un token constant par accident)
    assert token != ctrl.generate_ticket_print_token()
