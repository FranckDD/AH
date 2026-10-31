# alembic/versions/038_lab_dossier_day_consistency.py
"""lab_dossier_ranks.day lie au jour de son compteur (cle etrangere composite)

Revision ID: 038_lab_dossier_day_consistency
Revises: 037_lab_dossier_numbers
Create Date: 2026-10-31

"""
from alembic import op

revision = '038_lab_dossier_day_consistency'
down_revision = '037_lab_dossier_numbers'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_lab_dossier_days_counter_day') THEN
                ALTER TABLE public.lab_dossier_days
                    ADD CONSTRAINT uq_lab_dossier_days_counter_day UNIQUE (year, counter, day);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_lab_dossier_ranks_counter_day') THEN
                ALTER TABLE public.lab_dossier_ranks
                    ADD CONSTRAINT fk_lab_dossier_ranks_counter_day FOREIGN KEY (year, counter, day)
                    REFERENCES public.lab_dossier_days (year, counter, day);
            END IF;
        END $$
    """)


def downgrade():
    op.execute("ALTER TABLE public.lab_dossier_ranks DROP CONSTRAINT IF EXISTS fk_lab_dossier_ranks_counter_day")
    op.execute("ALTER TABLE public.lab_dossier_days DROP CONSTRAINT IF EXISTS uq_lab_dossier_days_counter_day")
