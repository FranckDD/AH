# alembic/versions/040_reference_ranges_days_ga.py
"""plages de reference : bornes d'age en jours et en semaines d'amenorrhee

Ajoute age_min_days / age_max_days (jours, inclusifs, NULL = borne ouverte) et
ga_min_weeks / ga_max_weeks (SA, 0 a 45, NULL = pas de critere). Les anciennes colonnes
age_min / age_max (annees entieres) sont conservees et deviennent nullables : une ligne
ancienne reste lisible (conversion en jours a la lecture), une ligne nouvelle peut les omettre.

Donnees existantes : age_min_days = age_min*365 ; age_max_days = (age_max+1)*365-1.
Aucune valeur medicale n'est ajoutee ici (le catalogue arrive avec la tache C1).

Revision ID: 040_reference_ranges_days_ga
Revises: 039_pregnancy_fields
Create Date: 2026-10-31

"""
from alembic import op

revision = '040_reference_ranges_days_ga'
down_revision = '039_pregnancy_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE public.reference_ranges ADD COLUMN IF NOT EXISTS age_min_days integer")
    op.execute("ALTER TABLE public.reference_ranges ADD COLUMN IF NOT EXISTS age_max_days integer")
    op.execute("ALTER TABLE public.reference_ranges ADD COLUMN IF NOT EXISTS ga_min_weeks smallint")
    op.execute("ALTER TABLE public.reference_ranges ADD COLUMN IF NOT EXISTS ga_max_weeks smallint")
    op.execute("""
        UPDATE public.reference_ranges
           SET age_min_days = CASE WHEN age_min IS NULL THEN NULL ELSE age_min * 365 END,
               age_max_days = CASE WHEN age_max IS NULL THEN NULL ELSE (age_max + 1) * 365 - 1 END
         WHERE age_min_days IS NULL AND age_max_days IS NULL
    """)
    op.execute("ALTER TABLE public.reference_ranges ALTER COLUMN age_min DROP NOT NULL")
    op.execute("ALTER TABLE public.reference_ranges ALTER COLUMN age_max DROP NOT NULL")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_reference_ranges_ga_weeks') THEN
                ALTER TABLE public.reference_ranges ADD CONSTRAINT ck_reference_ranges_ga_weeks
                    CHECK ((ga_min_weeks IS NULL OR ga_min_weeks BETWEEN 0 AND 45)
                       AND (ga_max_weeks IS NULL OR ga_max_weeks BETWEEN 0 AND 45)
                       AND (ga_min_weeks IS NULL OR ga_max_weeks IS NULL OR ga_min_weeks <= ga_max_weeks));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_reference_ranges_age_days') THEN
                ALTER TABLE public.reference_ranges ADD CONSTRAINT ck_reference_ranges_age_days
                    CHECK ((age_min_days IS NULL OR age_min_days >= 0)
                       AND (age_max_days IS NULL OR age_max_days >= 0)
                       AND (age_min_days IS NULL OR age_max_days IS NULL OR age_min_days <= age_max_days));
            END IF;
        END $$
    """)


def downgrade():
    op.execute("ALTER TABLE public.reference_ranges DROP CONSTRAINT IF EXISTS ck_reference_ranges_age_days")
    op.execute("ALTER TABLE public.reference_ranges DROP CONSTRAINT IF EXISTS ck_reference_ranges_ga_weeks")
    # Les lignes sans bornes en annees (nouvelles) recoivent 0..150 pour pouvoir remettre NOT NULL.
    op.execute("UPDATE public.reference_ranges SET age_min = COALESCE(age_min, COALESCE(age_min_days, 0) / 365)")
    op.execute("UPDATE public.reference_ranges SET age_max = COALESCE(age_max, CASE WHEN age_max_days IS NULL THEN 150 ELSE age_max_days / 365 END)")
    op.execute("ALTER TABLE public.reference_ranges ALTER COLUMN age_min SET NOT NULL")
    op.execute("ALTER TABLE public.reference_ranges ALTER COLUMN age_max SET NOT NULL")
    op.execute("ALTER TABLE public.reference_ranges DROP COLUMN IF EXISTS ga_max_weeks")
    op.execute("ALTER TABLE public.reference_ranges DROP COLUMN IF EXISTS ga_min_weeks")
    op.execute("ALTER TABLE public.reference_ranges DROP COLUMN IF EXISTS age_max_days")
    op.execute("ALTER TABLE public.reference_ranges DROP COLUMN IF EXISTS age_min_days")
