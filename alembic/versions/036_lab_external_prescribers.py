# alembic/versions/036_lab_external_prescribers.py
"""prescripteurs externes du laboratoire

Table lab_external_prescribers : memoire des prescripteurs saisis librement pour un patient externe.

Revision ID: 036_lab_external_prescribers
Revises: 035_spiritual_notes
Create Date: 2026-10-31

"""
from alembic import op

revision = '036_lab_external_prescribers'
down_revision = '035_spiritual_notes'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.lab_external_prescribers (
            id serial PRIMARY KEY,
            title varchar(20) NOT NULL,
            name varchar(80) NOT NULL DEFAULT '',
            last_used_at timestamp NOT NULL DEFAULT now(),
            CONSTRAINT lab_external_prescribers_title_check
                CHECK (title IN ('Dr', 'I.D.E.', 'Fr', 'Br', 'M.', 'Mme', 'Volontaire', 'Autre'))
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_lab_external_prescribers_title_name "
               "ON public.lab_external_prescribers (title, lower(name))")
    op.execute("CREATE INDEX IF NOT EXISTS idx_lab_external_prescribers_recent "
               "ON public.lab_external_prescribers (last_used_at DESC)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS public.lab_external_prescribers")
