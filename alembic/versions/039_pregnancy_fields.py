# alembic/versions/039_pregnancy_fields.py
"""suivi de grossesse : fiche patient et resultats de laboratoire

patients    : pregnancy_status (enceinte / non_enceinte / inconnu, defaut inconnu),
              expected_delivery_date (date presumee d'accouchement), pregnancy_program_number.
lab_results : gestational_age_weeks (semaines d'amenorrhee au prelevement, 0 a 45).

Donnee de sante sensible : jamais lue ni ecrite par le secretariat (voir utils/pregnancy_visibility.py).

Revision ID: 039_pregnancy_fields
Revises: 038_lab_dossier_day_consistency
Create Date: 2026-10-31

"""
from alembic import op

revision = '039_pregnancy_fields'
down_revision = '038_lab_dossier_day_consistency'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE public.patients ADD COLUMN IF NOT EXISTS pregnancy_status varchar(20) NOT NULL DEFAULT 'inconnu'")
    op.execute("ALTER TABLE public.patients ADD COLUMN IF NOT EXISTS expected_delivery_date date")
    op.execute("ALTER TABLE public.patients ADD COLUMN IF NOT EXISTS pregnancy_program_number varchar(50)")
    op.execute("ALTER TABLE public.lab_results ADD COLUMN IF NOT EXISTS gestational_age_weeks smallint")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_patients_pregnancy_status') THEN
                ALTER TABLE public.patients ADD CONSTRAINT ck_patients_pregnancy_status
                    CHECK (pregnancy_status IN ('enceinte', 'non_enceinte', 'inconnu'));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_lab_results_gestational_age_weeks') THEN
                ALTER TABLE public.lab_results ADD CONSTRAINT ck_lab_results_gestational_age_weeks
                    CHECK (gestational_age_weeks IS NULL OR gestational_age_weeks BETWEEN 0 AND 45);
            END IF;
        END $$
    """)


def downgrade():
    op.execute("ALTER TABLE public.lab_results DROP CONSTRAINT IF EXISTS ck_lab_results_gestational_age_weeks")
    op.execute("ALTER TABLE public.patients DROP CONSTRAINT IF EXISTS ck_patients_pregnancy_status")
    op.execute("ALTER TABLE public.lab_results DROP COLUMN IF EXISTS gestational_age_weeks")
    op.execute("ALTER TABLE public.patients DROP COLUMN IF EXISTS pregnancy_program_number")
    op.execute("ALTER TABLE public.patients DROP COLUMN IF EXISTS expected_delivery_date")
    op.execute("ALTER TABLE public.patients DROP COLUMN IF EXISTS pregnancy_status")
