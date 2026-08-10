# tests/test_role_map.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.security.role_map import normalize_role_name, normalize_roles_list


def test_normalizes_the_five_original_roles():
    assert normalize_role_name("admin") == "admin"
    assert normalize_role_name("médecin") == "medecin"
    assert normalize_role_name("infirmiere") == "nurse"
    assert normalize_role_name("secrétaire") == "secretaire"
    assert normalize_role_name("laboratory_technician") == "laborantin"


def test_normalizes_the_four_db_roles_previously_uncovered():
    assert normalize_role_name("Psychologist") == "psychologist"
    assert normalize_role_name("psychologue") == "psychologist"
    assert normalize_role_name("SpiritualCounsellor") == "spiritualcounsellor"
    assert normalize_role_name("conseiller_spirituel") == "spiritualcounsellor"
    assert normalize_role_name("ToxicoManager") == "toxicomanager"
    assert normalize_role_name("toxico_manager") == "toxicomanager"
    assert normalize_role_name("Assistant") == "assistant"
    assert normalize_role_name("assistante") == "assistant"


def test_normalizes_the_reserved_manager_role():
    assert normalize_role_name("manager") == "manager"
    assert normalize_role_name("Manager") == "manager"


def test_unknown_role_returns_none():
    assert normalize_role_name("biologiste") is None
    assert normalize_role_name("role_qui_nexiste_pas") is None


def test_normalize_roles_list_dedupes_and_drops_unknown():
    result = normalize_roles_list(["Psychologist", "psychologue", "biologiste", None, ""])
    assert result == ["psychologist"]
