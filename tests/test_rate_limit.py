# tests/test_rate_limit.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.rate_limit import limiter


def test_limiter_is_configured_with_ip_key_func():
    from slowapi.util import get_remote_address
    assert limiter._key_func is get_remote_address


def test_limiter_has_no_default_limits():
    # Les limites sont appliquees par route via le decorateur, pas globalement
    assert limiter._default_limits == []
