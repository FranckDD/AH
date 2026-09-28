import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import text
from tests.conftest import create_test_user, create_test_patient


def test_hospitalizations_table_has_partial_unique_index(db_session):
    """La contrainte 'un seul sejour ouvert par patient' doit exister
    reellement en base, pas seulement etre verifiee cote applicatif -
    sinon une course entre deux requetes concurrentes pourrait creer deux
    sejours ouverts pour le meme patient (voir Global Constraints)."""
    row = db_session.execute(text("""
        SELECT indexdef FROM pg_indexes
        WHERE indexname = 'ux_hospitalizations_one_open_per_patient'
    """)).fetchone()
    assert row is not None
    assert "discharged_at IS NULL" in row[0]


def test_hospitalization_status_updates_status_check_constraint(db_session):
    """Les 3 valeurs autorisees pour status sont une vraie contrainte
    CHECK en base, pas seulement une validation Pydantic contournable
    par un appel direct a l'API avec un schema different demain. Un
    vrai sejour valide est cree d'abord, pour que l'echec attendu soit
    bien celui de la contrainte CHECK et non une violation de cle
    etrangere sans rapport."""
    medecin = create_test_user(db_session, "schema_test_medecin", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="SchemaCheck")
    row = db_session.execute(text("""
        INSERT INTO hospitalizations (patient_id, admitted_by)
        VALUES (:patient_id, :admitted_by) RETURNING id
    """), {"patient_id": patient_id, "admitted_by": medecin.user_id}).fetchone()
    hospitalization_id = row[0]
    db_session.flush()

    with pytest.raises(Exception):
        db_session.execute(text("""
            INSERT INTO hospitalization_status_updates
                (hospitalization_id, status, created_by)
            VALUES (:hospitalization_id, 'VALEUR_INVALIDE', :created_by)
        """), {"hospitalization_id": hospitalization_id, "created_by": medecin.user_id})
        db_session.flush()
    db_session.rollback()
