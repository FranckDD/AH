"""Durcissement du filtre grossesse (revue B1-B3) : echec ferme, epellations, JSON dans une chaine,
verification d'ecriture profonde."""
import json

import pytest
from fastapi import HTTPException
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from starlette.testclient import TestClient

from api_backend.backend_app.security.pregnancy_filter import PregnancyFilterMiddleware
from utils.pregnancy_visibility import (
    clean_external_pregnancy, contains_pregnancy_input, is_pregnancy_key, require_pregnancy_write,
    strip_pregnancy_fields_always,
)

RAW = b'{"nom":"A","pregnancy_status":"enceinte","gestational_age_weeks":NaN,"x":Infinity,"y":-Infinity,"z":1e999}'


def _client(body: bytes):
    async def endpoint(request: Request):
        request.state.pregnancy_visible = request.headers.get("x-viewer") == "1"
        return Response(body, media_type="application/json")

    app = Starlette(routes=[Route("/t", endpoint)])
    app.add_middleware(PregnancyFilterMiddleware)
    return TestClient(app)


def test_nan_and_infinity_secretary_fail_safe_no_leak():
    r = _client(RAW).get("/t")
    assert b"enceinte" not in r.content and b"pregnancy" not in r.content
    # lecture tolerante : NaN / Infinity deviennent null, le reste est conserve
    assert r.status_code == 200
    assert r.json() == {"nom": "A", "x": None, "y": None, "z": None}


def test_viewer_untouched_even_with_nan():
    r = _client(RAW).get("/t", headers={"x-viewer": "1"})
    assert r.content == RAW


def test_unparseable_body_with_needle_fails_closed():
    r = _client(b'{"pregnancy_status":"enceinte", broken').get("/t")
    assert r.status_code == 500
    assert b"enceinte" not in r.content
    assert r.json() == {"detail": "Internal Server Error"}


def test_too_deep_body_fails_closed():
    deep = b"[" * 5000 + b'{"pregnancy_status":"enceinte"}' + b"]" * 5000
    r = _client(deep).get("/t")
    assert r.status_code == 500 and b"enceinte" not in r.content


@pytest.mark.parametrize("key", [
    "pregnancy_status", "Pregnancy_Status", "PREGNANCY STATUS", "pregnancy-status", "expected_delivery_date",
    "Expected Delivery Date", "pregnancy_program_number", "gestational_age_weeks", "GestationalAgeWeeks",
    "grossesse", "Grossesse", "enceinte", "ENCEINTE", "dpa", "DPA", "pregnancy", "pregnant_x".replace("pregnant", "pregnancy"),
    "gestational", "gestational_age", "grossesse_en_cours", "enceinte_oui",
])
def test_key_variants_are_pregnancy_keys(key):
    assert is_pregnancy_key(key)
    assert strip_pregnancy_fields_always({key: "v", "keep": 1}) == {"keep": 1}


@pytest.mark.parametrize("key", [
    "prenatal_note", "pregnant", "age", "nom", "sexe", "gender", "update", "ga", "weeks", "expected", "delivery_date",
    "status", "program_number", "consultation_note", "dpar", "d_p_a_x",
])
def test_unrelated_keys_are_kept(key):
    assert not is_pregnancy_key(key)
    assert strip_pregnancy_fields_always({key: "v"}) == {key: "v"}


def test_strip_nested_and_json_strings():
    payload = {
        "external_patient_info": {"Grossesse": "oui", "nom": "A", "deep": [{"DPA": "2026-01-01", "ok": 1}]},
        "blob": json.dumps({"pregnancy_status": "enceinte", "ok": 2}),
        "plain": "texte sans json",
        "list_blob": json.dumps([{"enceinte": True}]),
    }
    out = strip_pregnancy_fields_always(payload)
    assert out["external_patient_info"] == {"nom": "A", "deep": [{"ok": 1}]}
    assert json.loads(out["blob"]) == {"ok": 2}
    assert json.loads(out["list_blob"]) == [{}]
    assert out["plain"] == "texte sans json"
    assert "enceinte" not in json.dumps(out)


def test_middleware_strips_spellings_unicode_escapes_and_strings():
    body = json.dumps({"a": {"Grossesse": "oui"}, "b": json.dumps({"dpa": "x"}), "ok": 1}).encode()
    assert _client(body).get("/t").json() == {"a": {}, "b": "{}", "ok": 1}
    escaped = b'{"\u0070regnancy_status":"enceinte","ok":1}'
    assert _client(escaped).get("/t").json() == {"ok": 1}
    assert _client(b'{"enceinte":true}').get("/t", headers={"x-viewer": "1"}).json() == {"enceinte": True}


class U:
    def __init__(self, role):
        self.roles = [role]


@pytest.mark.parametrize("payload", [
    {"pregnancy_status": "enceinte"},
    {"Pregnancy_Status": "enceinte"},
    {"grossesse": "oui"},
    {"enceinte": True},
    {"dpa": "2026-01-01"},
    {"gestational_age_weeks": 12},
    {"external_patient_info": {"Grossesse": "oui"}},
    {"external_patient_info": {"nested": {"deeper": [{"DPA": "2026-01-01"}]}}},
    {"other": [{"x": {"expected-delivery-date": "2026-01-01"}}]},
    {"external_patient_info": {"blob": json.dumps({"enceinte": True})}},
])
def test_non_writer_deep_write_rejected(payload):
    with pytest.raises(HTTPException) as e:
        require_pregnancy_write(U("secretaire"), payload)
    assert e.value.status_code == 403
    require_pregnancy_write(U("medecin"), payload)  # un ecrivain passe


def test_non_writer_clean_payloads_pass():
    require_pregnancy_write(U("secretaire"), {"nom": "A", "pregnancy_status": None,
                                              "external_patient_info": {"prenatal_note": "x", "age": 3}})
    assert not contains_pregnancy_input({"a": {"b": [1, 2, {"c": None}]}})


def test_absurdly_deep_payload_is_rejected_for_non_writer():
    obj = cur = {}
    for _ in range(30):
        cur["n"] = {}
        cur = cur["n"]
    with pytest.raises(HTTPException):
        require_pregnancy_write(U("secretaire"), obj)


def test_clean_external_drops_noncanonical_spellings_keeps_canonical():
    out = clean_external_pregnancy({"nom": "A", "Grossesse": "oui", "DPA": "x", "pregnancy_status": "enceinte",
                                    "gestational_age_weeks": 12})
    assert out == {"nom": "A", "pregnancy_status": "enceinte", "gestational_age_weeks": 12}
