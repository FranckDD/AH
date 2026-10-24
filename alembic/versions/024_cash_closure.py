# alembic/versions/024_cash_closure.py
"""cloture de caisse: payment_modes, cash_closures, cash_closure_lines, cash_closure_corrections,
cash_closure_start, colonnes received_at (paiement_echelonne, caisse_retrait), trigger d'immuabilite

Revision ID: 024_cash_closure
Revises: 023_fabrication
Create Date: 2026-10-24

"""
from alembic import op

revision = '024_cash_closure'
down_revision = '023_fabrication'
branch_labels = None
depends_on = None

# Remplissage de l'historique. {table} est le nom de la table, {expr} la conversion de fuseau :
# paiement_echelonne.payment_date est en heure locale (Africa/Lagos), caisse_retrait.retrait_at en UTC.
BACKFILL_SQL = "UPDATE {table} SET received_at = {expr} WHERE received_at IS NULL"
PAIEMENT_EXPR = "payment_date AT TIME ZONE 'Africa/Lagos'"
RETRAIT_EXPR = "retrait_at AT TIME ZONE 'UTC'"


def upgrade():
    op.execute("""
        ALTER TABLE public.paiement_echelonne
            ADD COLUMN IF NOT EXISTS received_at timestamptz;
        ALTER TABLE public.caisse_retrait
            ADD COLUMN IF NOT EXISTS received_at timestamptz;
    """)
    op.execute(BACKFILL_SQL.format(table="public.paiement_echelonne", expr=PAIEMENT_EXPR))
    op.execute(BACKFILL_SQL.format(table="public.caisse_retrait", expr=RETRAIT_EXPR))
    op.execute("""
        ALTER TABLE public.paiement_echelonne
            ALTER COLUMN received_at SET DEFAULT now(),
            ALTER COLUMN received_at SET NOT NULL;
        ALTER TABLE public.caisse_retrait
            ALTER COLUMN received_at SET DEFAULT now(),
            ALTER COLUMN received_at SET NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_paiement_echelonne_received_at
            ON public.paiement_echelonne (received_at);
        CREATE INDEX IF NOT EXISTS idx_caisse_retrait_received_at
            ON public.caisse_retrait (received_at);

        CREATE TABLE IF NOT EXISTS public.payment_modes (
            code varchar(30) PRIMARY KEY,
            label varchar(80) NOT NULL,
            is_active boolean NOT NULL DEFAULT true,
            sort_order integer NOT NULL DEFAULT 0
        );
        INSERT INTO public.payment_modes (code, label, is_active, sort_order) VALUES
            ('especes', 'Especes', true, 1),
            ('orange_money', 'Orange Money', true, 2),
            ('mtn_money', 'MTN Money', true, 3),
            ('autre_mobile', 'Autre mobile', true, 4)
        ON CONFLICT (code) DO NOTHING;

        CREATE TABLE IF NOT EXISTS public.cash_closures (
            id serial PRIMARY KEY,
            period_start timestamptz NOT NULL,
            period_end timestamptz NOT NULL,
            business_date date NOT NULL,
            kind varchar(10) NOT NULL,
            closed_by integer REFERENCES public.users(user_id),
            closed_at timestamptz NOT NULL DEFAULT now(),
            opening_cash numeric(14,2) NOT NULL DEFAULT 0,
            expected_cash numeric(14,2) NOT NULL DEFAULT 0,
            counted_cash numeric(14,2),
            difference numeric(14,2),
            opening_from_auto boolean NOT NULL DEFAULT false,
            comment text,
            unsynced_ignored boolean NOT NULL DEFAULT false,
            CONSTRAINT cash_closures_kind_check CHECK (kind IN ('manual','auto')),
            CONSTRAINT cash_closures_period_check CHECK (period_end > period_start),
            CONSTRAINT cash_closures_counted_check CHECK (counted_cash IS NULL OR counted_cash >= 0),
            CONSTRAINT cash_closures_opening_check CHECK (opening_cash >= 0),
            CONSTRAINT cash_closures_closed_by_check CHECK (kind = 'auto' OR closed_by IS NOT NULL),
            CONSTRAINT cash_closures_period_end_key UNIQUE (period_end)
        );
        CREATE INDEX IF NOT EXISTS idx_cash_closures_business_date
            ON public.cash_closures (business_date);

        CREATE TABLE IF NOT EXISTS public.cash_closure_lines (
            id serial PRIMARY KEY,
            closure_id integer NOT NULL REFERENCES public.cash_closures(id),
            mode_code varchar(30) NOT NULL,
            source varchar(20) NOT NULL,
            opening numeric(14,2) NOT NULL DEFAULT 0,
            entries numeric(14,2) NOT NULL DEFAULT 0,
            exits numeric(14,2) NOT NULL DEFAULT 0,
            expected numeric(14,2) NOT NULL DEFAULT 0,
            counted numeric(14,2),
            difference numeric(14,2),
            comment text,
            CONSTRAINT cash_closure_lines_source_check
                CHECK (source IN ('physical','operator_statement')),
            CONSTRAINT cash_closure_lines_counted_check CHECK (counted IS NULL OR counted >= 0),
            CONSTRAINT cash_closure_lines_closure_mode_key UNIQUE (closure_id, mode_code)
        );
        CREATE INDEX IF NOT EXISTS idx_cash_closure_lines_closure
            ON public.cash_closure_lines (closure_id);

        CREATE TABLE IF NOT EXISTS public.cash_closure_corrections (
            id serial PRIMARY KEY,
            closure_id integer NOT NULL REFERENCES public.cash_closures(id),
            mode_code varchar(30) NOT NULL,
            amount_delta numeric(14,2) NOT NULL,
            reason text NOT NULL,
            status varchar(20) NOT NULL DEFAULT 'pending',
            requested_by integer NOT NULL REFERENCES public.users(user_id),
            requested_at timestamptz NOT NULL DEFAULT now(),
            decided_by integer REFERENCES public.users(user_id),
            decided_at timestamptz,
            CONSTRAINT cash_closure_corrections_status_check
                CHECK (status IN ('pending','approved','rejected')),
            CONSTRAINT cash_closure_corrections_reason_check CHECK (length(btrim(reason)) > 0)
        );
        CREATE INDEX IF NOT EXISTS idx_cash_closure_corrections_closure
            ON public.cash_closure_corrections (closure_id);

        CREATE TABLE IF NOT EXISTS public.cash_closure_start (
            id smallint PRIMARY KEY,
            started_at timestamptz NOT NULL,
            opening_cash numeric(14,2) NOT NULL,
            set_by integer REFERENCES public.users(user_id),
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT cash_closure_start_single_row_check CHECK (id = 1),
            CONSTRAINT cash_closure_start_opening_check CHECK (opening_cash >= 0)
        );

        CREATE OR REPLACE FUNCTION public.cash_closure_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'cash closure records are immutable (table %, operation %)',
                TG_TABLE_NAME, TG_OP USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_cash_closures_immutable ON public.cash_closures;
        CREATE TRIGGER trg_cash_closures_immutable
            BEFORE UPDATE OR DELETE ON public.cash_closures
            FOR EACH ROW EXECUTE FUNCTION public.cash_closure_immutable();
        DROP TRIGGER IF EXISTS trg_cash_closure_lines_immutable ON public.cash_closure_lines;
        CREATE TRIGGER trg_cash_closure_lines_immutable
            BEFORE UPDATE OR DELETE ON public.cash_closure_lines
            FOR EACH ROW EXECUTE FUNCTION public.cash_closure_immutable();
        DROP TRIGGER IF EXISTS trg_cash_closure_start_immutable ON public.cash_closure_start;
        CREATE TRIGGER trg_cash_closure_start_immutable
            BEFORE UPDATE OR DELETE ON public.cash_closure_start
            FOR EACH ROW EXECUTE FUNCTION public.cash_closure_immutable();
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS public.cash_closure_corrections;
        DROP TABLE IF EXISTS public.cash_closure_lines;
        DROP TABLE IF EXISTS public.cash_closures;
        DROP TABLE IF EXISTS public.cash_closure_start;
        DROP FUNCTION IF EXISTS public.cash_closure_immutable();
        DROP TABLE IF EXISTS public.payment_modes;
        DROP INDEX IF EXISTS public.idx_paiement_echelonne_received_at;
        DROP INDEX IF EXISTS public.idx_caisse_retrait_received_at;
        ALTER TABLE public.paiement_echelonne DROP COLUMN IF EXISTS received_at;
        ALTER TABLE public.caisse_retrait DROP COLUMN IF EXISTS received_at;
    """)
