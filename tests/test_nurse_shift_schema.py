import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import text
from tests.conftest import create_test_user


def test_nurse_shifts_table_has_unique_index(db_session):
    row = db_session.execute(text("""
        SELECT indexdef FROM pg_indexes
        WHERE indexname = 'ux_nurse_shifts_no_duplicate'
    """)).fetchone()
    assert row is not None
    assert "shift_date" in row[0] and "shift_type" in row[0] and "nurse_id" in row[0]


def test_nurse_shifts_shift_type_check_constraint(db_session):
    """La contrainte CHECK sur shift_type doit exister reellement en base,
    pas seulement etre validee cote Pydantic - un vrai infirmier est cree
    d'abord pour que l'echec attendu soit bien celui du CHECK et non une
    violation de cle etrangere sans rapport."""
    nurse = create_test_user(db_session, "schema_test_nurse", "nurse")
    admin = create_test_user(db_session, "schema_test_admin_nsh", "admin")

    with pytest.raises(Exception):
        db_session.execute(text("""
            INSERT INTO nurse_shifts (shift_date, shift_type, nurse_id, created_by)
            VALUES (CURRENT_DATE, 'VALEUR_INVALIDE', :nurse_id, :created_by)
        """), {"nurse_id": nurse.user_id, "created_by": admin.user_id})
        db_session.flush()
    db_session.rollback()


def test_users_is_head_nurse_defaults_false(db_session):
    nurse = create_test_user(db_session, "schema_test_nurse2", "nurse")
    assert nurse.is_head_nurse is False
