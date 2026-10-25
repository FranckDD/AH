# alembic/versions/027_stock_count_line_times.py
"""comptage du stock : heure de comptage par ligne (counted_at) et mouvements nets apres comptage

Revision ID: 027_stock_count_line_times
Revises: 026_stock_counts
Create Date: 2026-10-25

"""
from alembic import op

revision = '027_stock_count_line_times'
down_revision = '026_stock_counts'
branch_labels = None
depends_on = None


def upgrade():
    # Les lignes sont immuables (trigger) : le trigger est suspendu le temps du remplissage
    # des lignes existantes, dans la meme transaction de migration.
    op.execute("""
        ALTER TABLE public.stock_count_lines ADD COLUMN IF NOT EXISTS counted_at timestamp;
        ALTER TABLE public.stock_count_lines ADD COLUMN IF NOT EXISTS movements_net integer NOT NULL DEFAULT 0;
        ALTER TABLE public.stock_count_lines DISABLE TRIGGER trg_stock_count_lines_immutable;
        UPDATE public.stock_count_lines l
           SET counted_at = COALESCE(c.submitted_at, c.started_at)
          FROM public.stock_counts c
         WHERE c.id = l.count_id AND l.counted_at IS NULL;
        ALTER TABLE public.stock_count_lines ENABLE TRIGGER trg_stock_count_lines_immutable;
        ALTER TABLE public.stock_count_lines ALTER COLUMN counted_at SET NOT NULL;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE public.stock_count_lines DROP COLUMN IF EXISTS movements_net;
        ALTER TABLE public.stock_count_lines DROP COLUMN IF EXISTS counted_at;
    """)
