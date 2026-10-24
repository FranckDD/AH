# alembic/versions/025_fab_batch_outputs.py
"""sorties declarees de fabrication: fab_batch_outputs

Revision ID: 025_fab_batch_outputs
Revises: 024_cash_closure
Create Date: 2026-10-24

"""
from alembic import op

revision = '025_fab_batch_outputs'
down_revision = '024_cash_closure'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.fab_batch_outputs (
            id serial PRIMARY KEY,
            batch_id integer NOT NULL REFERENCES public.fab_batches(id),
            reason varchar(20) NOT NULL,
            quantity integer NOT NULL,
            note text,
            status varchar(20) NOT NULL DEFAULT 'active',
            declared_by integer NOT NULL REFERENCES public.users(user_id),
            declared_at timestamp NOT NULL DEFAULT now(),
            cancelled_by integer REFERENCES public.users(user_id),
            cancelled_at timestamp,
            cancel_reason text,
            CONSTRAINT fab_batch_outputs_quantity_check CHECK (quantity > 0),
            CONSTRAINT fab_batch_outputs_reason_check
                CHECK (reason IN ('echantillon','autre')),
            CONSTRAINT fab_batch_outputs_status_check
                CHECK (status IN ('active','annulee')),
            CONSTRAINT fab_batch_outputs_autre_note_check
                CHECK (reason <> 'autre' OR length(trim(coalesce(note,''))) > 0),
            CONSTRAINT fab_batch_outputs_cancel_check
                CHECK (status <> 'annulee'
                       OR (cancelled_by IS NOT NULL
                           AND length(trim(coalesce(cancel_reason,''))) > 0))
        );
        CREATE INDEX IF NOT EXISTS idx_fab_batch_outputs_batch
            ON public.fab_batch_outputs (batch_id);
        CREATE INDEX IF NOT EXISTS idx_fab_batch_outputs_status
            ON public.fab_batch_outputs (status);
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS public.fab_batch_outputs;
    """)
