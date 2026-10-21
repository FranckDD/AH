# alembic/versions/022_toxico_stays.py
"""sejours toxico : toxico_stays, stay_id sur phases/evaluations, remplissage de l'existant

Revision ID: 022_toxico_stays
Revises: 021_lab_stock
Create Date: 2026-10-22

"""
from alembic import op

from utils.toxico_stays_backfill import BACKFILL_STATEMENTS

revision = '022_toxico_stays'
down_revision = '021_lab_stock'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.toxico_stays (
            id serial PRIMARY KEY,
            dossier_id integer NOT NULL
                REFERENCES public.toxico_dossiers(id) ON DELETE CASCADE,
            stay_number integer NOT NULL,
            admission_date date NOT NULL,
            psychologist_id integer REFERENCES public.users(user_id) ON DELETE SET NULL,
            substance varchar(100) NOT NULL,
            discharge_date date,
            discharge_reason varchar(20),
            discharge_note text,
            discharged_by integer REFERENCES public.users(user_id) ON DELETE SET NULL,
            created_at timestamp NOT NULL DEFAULT now(),
            CONSTRAINT toxico_stays_number_check CHECK (stay_number >= 1),
            CONSTRAINT toxico_stays_reason_check
                CHECK (discharge_reason IS NULL
                       OR discharge_reason IN ('guerison','abandon','exclusion','autre')),
            CONSTRAINT toxico_stays_discharge_consistency_check
                CHECK ((discharge_date IS NULL) = (discharge_reason IS NULL)),
            CONSTRAINT toxico_stays_dates_check
                CHECK (discharge_date IS NULL OR discharge_date >= admission_date),
            CONSTRAINT uq_toxico_stays_dossier_number UNIQUE (dossier_id, stay_number)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_toxico_stays_one_open
            ON public.toxico_stays (dossier_id) WHERE discharge_date IS NULL;
        CREATE INDEX IF NOT EXISTS idx_toxico_stays_psychologist
            ON public.toxico_stays (psychologist_id);

        ALTER TABLE public.toxico_phase_history
            ADD COLUMN IF NOT EXISTS stay_id integer REFERENCES public.toxico_stays(id);
        ALTER TABLE public.toxico_evaluations
            ADD COLUMN IF NOT EXISTS stay_id integer REFERENCES public.toxico_stays(id);
        CREATE INDEX IF NOT EXISTS idx_toxico_phase_history_stay
            ON public.toxico_phase_history (stay_id);
        CREATE INDEX IF NOT EXISTS idx_toxico_evaluations_stay
            ON public.toxico_evaluations (stay_id);
    """)
    for statement in BACKFILL_STATEMENTS:
        op.execute(statement)


def downgrade():
    op.execute("""
        ALTER TABLE public.toxico_evaluations DROP COLUMN IF EXISTS stay_id;
        ALTER TABLE public.toxico_phase_history DROP COLUMN IF EXISTS stay_id;
        DROP TABLE IF EXISTS public.toxico_stays;
    """)
