# alembic/versions/017_triage_infirmiere_medecin.py
"""medical_records triage fields + appointments.doctor_id nullable

Revision ID: 017_triage_infirmiere_medecin
Revises: 016_nurse_shifts
Create Date: 2026-09-29

"""
from alembic import op

revision = '017_triage_infirmiere_medecin'
down_revision = '016_nurse_shifts'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.medical_records
            ADD COLUMN IF NOT EXISTS needs_doctor_review boolean NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS assigned_doctor_id integer REFERENCES users(user_id),
            ADD COLUMN IF NOT EXISTS reviewed_by integer REFERENCES users(user_id),
            ADD COLUMN IF NOT EXISTS reviewed_at timestamp;

        CREATE INDEX IF NOT EXISTS ix_medical_records_pending_review
            ON medical_records (needs_doctor_review, reviewed_at)
            WHERE needs_doctor_review = true AND reviewed_at IS NULL;

        ALTER TABLE public.appointments
            ALTER COLUMN doctor_id DROP NOT NULL;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE public.appointments
            ALTER COLUMN doctor_id SET NOT NULL;

        DROP INDEX IF EXISTS ix_medical_records_pending_review;
        ALTER TABLE public.medical_records
            DROP COLUMN IF EXISTS reviewed_at,
            DROP COLUMN IF EXISTS reviewed_by,
            DROP COLUMN IF EXISTS assigned_doctor_id,
            DROP COLUMN IF EXISTS needs_doctor_review;
    """)
