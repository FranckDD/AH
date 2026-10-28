import pytest

from api_backend.backend_app.config import (
    DEFAULT_DEV_CORS_ORIGINS,
    parse_cors_origins,
)


def test_parse_cors_origins_default_keeps_dev_list():
    expected = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]
    assert parse_cors_origins(None) == expected
    assert parse_cors_origins("") == expected
    assert parse_cors_origins("  ") == expected
    assert DEFAULT_DEV_CORS_ORIGINS == expected


def test_parse_cors_origins_splits_trims_and_drops_empty():
    assert parse_cors_origins(" https://app.x.org , ,http://a ") == [
        "https://app.x.org",
        "http://a",
    ]


def test_parse_cors_origins_rejects_wildcard_in_prod():
    with pytest.raises(ValueError):
        parse_cors_origins("*", is_prod=True)


def test_parse_cors_origins_allows_wildcard_outside_prod():
    assert parse_cors_origins("*", is_prod=False) == ["*"]
