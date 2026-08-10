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
