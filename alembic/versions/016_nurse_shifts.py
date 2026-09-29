"""users.is_head_nurse + nurse_shifts

Revision ID: 016_nurse_shifts
Revises: 015_hospitalizations
Create Date: 2026-09-29

"""
from alembic import op

revision = '016_nurse_shifts'
down_revision = '015_hospitalizations'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.users
            ADD COLUMN IF NOT EXISTS is_head_nurse boolean NOT NULL DEFAULT false;

        CREATE TABLE IF NOT EXISTS nurse_shifts (
            id SERIAL PRIMARY KEY,
            shift_date DATE NOT NULL,
            shift_type VARCHAR(20) NOT NULL
                CHECK (shift_type IN ('MATIN', 'APRES_MIDI', 'NUIT')),
            nurse_id INTEGER NOT NULL REFERENCES users(user_id),
            created_by INTEGER NOT NULL REFERENCES users(user_id),
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_nurse_shifts_no_duplicate
            ON nurse_shifts (shift_date, shift_type, nurse_id);
        CREATE INDEX IF NOT EXISTS ix_nurse_shifts_date
            ON nurse_shifts (shift_date);
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS nurse_shifts;
        ALTER TABLE public.users DROP COLUMN IF EXISTS is_head_nurse;
    """)
