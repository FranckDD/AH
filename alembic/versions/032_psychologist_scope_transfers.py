# alembic/versions/032_psychologist_scope_transfers.py
"""psychologue limite a ses patients + journal des transferts de dossier toxico

users.sees_own_toxico_only : le psychologue ne voit que ses propres dossiers.
toxico_psychologist_transfers : un transfert de dossier d'un psychologue a un autre.

Revision ID: 032_psy_scope_transfers
Revises: 031_lab_param_order
Create Date: 2026-10-27

"""
from alembic import op

revision = '032_psy_scope_transfers'
down_revision = '031_lab_param_order'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS "
               "sees_own_toxico_only boolean NOT NULL DEFAULT false")
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.toxico_psychologist_transfers (
            id serial PRIMARY KEY,
            dossier_id integer NOT NULL REFERENCES public.toxico_dossiers(id) ON DELETE CASCADE,
            from_psychologist_id integer REFERENCES public.users(user_id),
            to_psychologist_id integer NOT NULL REFERENCES public.users(user_id),
            decided_by integer NOT NULL REFERENCES public.users(user_id),
            decided_at timestamp without time zone NOT NULL,
            reason text NOT NULL,
            stay_id integer REFERENCES public.toxico_stays(id) ON DELETE SET NULL,
            CONSTRAINT toxico_transfers_reason_check CHECK (length(btrim(reason)) > 0),
            CONSTRAINT toxico_transfers_distinct_check
                CHECK (from_psychologist_id IS DISTINCT FROM to_psychologist_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_toxico_transfers_dossier "
               "ON public.toxico_psychologist_transfers (dossier_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_toxico_transfers_from "
               "ON public.toxico_psychologist_transfers (from_psychologist_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_toxico_transfers_to "
               "ON public.toxico_psychologist_transfers (to_psychologist_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS public.toxico_psychologist_transfers")
    op.execute("ALTER TABLE public.users DROP COLUMN IF EXISTS sees_own_toxico_only")
