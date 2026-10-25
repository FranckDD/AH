# alembic/versions/026_stock_counts.py
"""comptage physique du stock de la pharmacie: stock_counts, stock_count_lines, stock_count_settings,
triggers d'immuabilite

Revision ID: 026_stock_counts
Revises: 025_fab_batch_outputs
Create Date: 2026-10-24

"""
from alembic import op

revision = '026_stock_counts'
down_revision = '025_fab_batch_outputs'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.stock_counts (
            id serial PRIMARY KEY,
            status varchar(20) NOT NULL DEFAULT 'en_cours',
            started_by integer NOT NULL REFERENCES public.users(user_id),
            started_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
            submitted_at timestamp,
            scope varchar(20) NOT NULL DEFAULT 'tous',
            CONSTRAINT stock_counts_status_check CHECK (status IN ('en_cours','valide','abandonne')),
            CONSTRAINT stock_counts_scope_check CHECK (scope IN ('tous','selection'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_stock_counts_one_open_per_user
            ON public.stock_counts (started_by) WHERE status = 'en_cours';
        CREATE INDEX IF NOT EXISTS idx_stock_counts_status
            ON public.stock_counts (status);

        CREATE TABLE IF NOT EXISTS public.stock_count_lines (
            id serial PRIMARY KEY,
            count_id integer NOT NULL REFERENCES public.stock_counts(id) ON DELETE CASCADE,
            product_id integer NOT NULL REFERENCES public.pharmacy(medication_id),
            counted_qty integer NOT NULL,
            previous_qty integer NOT NULL,
            difference integer NOT NULL,
            observation text,
            movements_during integer NOT NULL DEFAULT 0,
            adjustment_request_id integer REFERENCES public.stock_adjustment_requests(id),
            CONSTRAINT stock_count_lines_counted_check CHECK (counted_qty >= 0),
            CONSTRAINT stock_count_lines_previous_check CHECK (previous_qty >= 0),
            CONSTRAINT stock_count_lines_movements_check CHECK (movements_during >= 0),
            CONSTRAINT stock_count_lines_count_product_key UNIQUE (count_id, product_id)
        );
        CREATE INDEX IF NOT EXISTS idx_stock_count_lines_count
            ON public.stock_count_lines (count_id);

        CREATE TABLE IF NOT EXISTS public.stock_count_settings (
            id smallint PRIMARY KEY,
            interval_days integer NOT NULL DEFAULT 30,
            updated_by integer REFERENCES public.users(user_id),
            updated_at timestamp NOT NULL DEFAULT now(),
            CONSTRAINT stock_count_settings_single_row_check CHECK (id = 1),
            CONSTRAINT stock_count_settings_interval_check CHECK (interval_days BETWEEN 1 AND 365)
        );
        INSERT INTO public.stock_count_settings (id, interval_days) VALUES (1, 30)
        ON CONFLICT (id) DO NOTHING;

        CREATE OR REPLACE FUNCTION public.stock_count_lines_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'stock count lines are immutable (operation %)', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;

        CREATE OR REPLACE FUNCTION public.stock_counts_final_immutable() RETURNS trigger AS $$
        BEGIN
            IF OLD.status IN ('valide','abandonne') THEN
                RAISE EXCEPTION 'a closed stock count is immutable (status %, operation %)',
                    OLD.status, TG_OP USING ERRCODE = 'restrict_violation';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_stock_count_lines_immutable ON public.stock_count_lines;
        CREATE TRIGGER trg_stock_count_lines_immutable
            BEFORE UPDATE OR DELETE ON public.stock_count_lines
            FOR EACH ROW EXECUTE FUNCTION public.stock_count_lines_immutable();
        DROP TRIGGER IF EXISTS trg_stock_counts_final_immutable ON public.stock_counts;
        CREATE TRIGGER trg_stock_counts_final_immutable
            BEFORE UPDATE OR DELETE ON public.stock_counts
            FOR EACH ROW EXECUTE FUNCTION public.stock_counts_final_immutable();
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS public.stock_count_lines;
        DROP TABLE IF EXISTS public.stock_counts;
        DROP TABLE IF EXISTS public.stock_count_settings;
        DROP FUNCTION IF EXISTS public.stock_count_lines_immutable();
        DROP FUNCTION IF EXISTS public.stock_counts_final_immutable();
    """)
