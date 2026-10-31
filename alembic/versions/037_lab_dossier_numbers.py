# alembic/versions/037_lab_dossier_numbers.py
"""numero de dossier du laboratoire (NNN/NN du JJ/MM/AAAA)

lab_dossier_days  : un compteur annuel par jour d'activite (avance au premier dossier du jour).
lab_dossier_ranks : un rang par patient et par jour, unique (annee, compteur, rang).
lab_results       : dossier_year / dossier_counter / dossier_rank (nuls tant que non attribues)
                    et patient_key (cle stable du patient pour partager le rang).

Revision ID: 037_lab_dossier_numbers
Revises: 036_lab_external_prescribers
Create Date: 2026-10-31

"""
from alembic import op

revision = '037_lab_dossier_numbers'
down_revision = '036_lab_external_prescribers'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.lab_dossier_days (
            year integer NOT NULL,
            day date NOT NULL,
            counter integer NOT NULL CHECK (counter >= 1),
            PRIMARY KEY (year, day),
            CONSTRAINT uq_lab_dossier_days_counter UNIQUE (year, counter)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.lab_dossier_ranks (
            year integer NOT NULL,
            counter integer NOT NULL,
            rank integer NOT NULL CHECK (rank >= 1),
            patient_key text NOT NULL,
            day date NOT NULL,
            PRIMARY KEY (year, counter, rank),
            CONSTRAINT uq_lab_dossier_ranks_patient_day UNIQUE (year, day, patient_key),
            CONSTRAINT fk_lab_dossier_ranks_day FOREIGN KEY (year, counter)
                REFERENCES public.lab_dossier_days (year, counter)
        )
    """)
    op.execute("ALTER TABLE public.lab_results ADD COLUMN IF NOT EXISTS dossier_year integer")
    op.execute("ALTER TABLE public.lab_results ADD COLUMN IF NOT EXISTS dossier_counter integer")
    op.execute("ALTER TABLE public.lab_results ADD COLUMN IF NOT EXISTS dossier_rank integer")
    op.execute("ALTER TABLE public.lab_results ADD COLUMN IF NOT EXISTS patient_key text")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_lab_results_dossier') THEN
                ALTER TABLE public.lab_results ADD CONSTRAINT fk_lab_results_dossier
                    FOREIGN KEY (dossier_year, dossier_counter, dossier_rank)
                    REFERENCES public.lab_dossier_ranks (year, counter, rank);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_lab_results_dossier_all_or_none') THEN
                ALTER TABLE public.lab_results ADD CONSTRAINT ck_lab_results_dossier_all_or_none
                    CHECK ((dossier_year IS NULL) = (dossier_counter IS NULL)
                       AND (dossier_year IS NULL) = (dossier_rank IS NULL));
            END IF;
        END $$
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_lab_results_dossier "
               "ON public.lab_results (dossier_year, dossier_counter, dossier_rank)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS public.idx_lab_results_dossier")
    op.execute("ALTER TABLE public.lab_results DROP CONSTRAINT IF EXISTS ck_lab_results_dossier_all_or_none")
    op.execute("ALTER TABLE public.lab_results DROP CONSTRAINT IF EXISTS fk_lab_results_dossier")
    for col in ("patient_key", "dossier_rank", "dossier_counter", "dossier_year"):
        op.execute(f"ALTER TABLE public.lab_results DROP COLUMN IF EXISTS {col}")
    op.execute("DROP TABLE IF EXISTS public.lab_dossier_ranks")
    op.execute("DROP TABLE IF EXISTS public.lab_dossier_days")
