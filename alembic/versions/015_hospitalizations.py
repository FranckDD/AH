"""hospitalizations + hospitalization_status_updates

Revision ID: 015_hospitalizations
Revises: 014_ticket_logo_token
Create Date: 2026-09-28

"""
from alembic import op

revision = '015_hospitalizations'
down_revision = '014_ticket_logo_token'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS hospitalizations (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES patients(patient_id),
            admitted_at TIMESTAMP NOT NULL DEFAULT now(),
            admitted_by INTEGER NOT NULL REFERENCES users(user_id),
            admission_reason TEXT,
            discharged_at TIMESTAMP,
            discharge_disposition VARCHAR(30)
                CHECK (discharge_disposition IN ('GUERI', 'TRANSFERE', 'SORTIE_CONTRE_AVIS_MEDICAL', 'DECES')),
            discharge_note TEXT,
            discharged_by INTEGER REFERENCES users(user_id),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_hospitalizations_one_open_per_patient
            ON hospitalizations (patient_id)
            WHERE discharged_at IS NULL;
        CREATE INDEX IF NOT EXISTS ix_hospitalizations_patient
            ON hospitalizations (patient_id);

        CREATE TABLE IF NOT EXISTS hospitalization_status_updates (
            id SERIAL PRIMARY KEY,
            hospitalization_id INTEGER NOT NULL REFERENCES hospitalizations(id),
            status VARCHAR(20) NOT NULL
                CHECK (status IN ('AMELIORATION', 'STABLE', 'AGGRAVATION')),
            note TEXT,
            created_by INTEGER NOT NULL REFERENCES users(user_id),
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_hospitalization_status_updates_hospitalization
            ON hospitalization_status_updates (hospitalization_id);
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS hospitalization_status_updates;
        DROP TABLE IF EXISTS hospitalizations;
    """)
