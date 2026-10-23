# alembic/versions/023_fabrication.py
"""fabrication: fab_intrants, fab_intrant_purchases, fab_batches, fab_consumptions, fab_settings, role ProductionManager

Revision ID: 023_fabrication
Revises: 022_toxico_stays
Create Date: 2026-10-23

"""
from alembic import op

revision = '023_fabrication'
down_revision = '022_toxico_stays'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.fab_intrants (
            id serial PRIMARY KEY,
            name varchar(150) NOT NULL,
            unit varchar(20) NOT NULL,
            is_container boolean NOT NULL DEFAULT false,
            alert_threshold numeric(12,3) NOT NULL DEFAULT 0,
            is_active boolean NOT NULL DEFAULT true,
            CONSTRAINT fab_intrants_threshold_check CHECK (alert_threshold >= 0)
        );

        CREATE TABLE IF NOT EXISTS public.fab_intrant_purchases (
            id serial PRIMARY KEY,
            intrant_id integer NOT NULL REFERENCES public.fab_intrants(id),
            supplier varchar(150),
            delivery_ref varchar(100),
            purchase_date date NOT NULL,
            quantity numeric(12,3) NOT NULL,
            unit_cost numeric(12,2) NOT NULL,
            remaining_qty numeric(12,3) NOT NULL,
            status varchar(20) NOT NULL DEFAULT 'actif',
            cancel_reason text,
            created_by integer NOT NULL REFERENCES public.users(user_id),
            created_at timestamp NOT NULL DEFAULT now(),
            CONSTRAINT fab_intrant_purchases_quantity_check CHECK (quantity > 0),
            CONSTRAINT fab_intrant_purchases_unit_cost_check CHECK (unit_cost >= 0),
            CONSTRAINT fab_intrant_purchases_remaining_check
                CHECK (remaining_qty >= 0 AND remaining_qty <= quantity),
            CONSTRAINT fab_intrant_purchases_status_check
                CHECK (status IN ('actif','annule'))
        );
        CREATE INDEX IF NOT EXISTS idx_fab_intrant_purchases_status
            ON public.fab_intrant_purchases (status);
        CREATE INDEX IF NOT EXISTS idx_fab_intrant_purchases_intrant
            ON public.fab_intrant_purchases (intrant_id);

        CREATE TABLE IF NOT EXISTS public.fab_batches (
            id serial PRIMARY KEY,
            batch_number varchar(30) NOT NULL,
            product_id integer NOT NULL REFERENCES public.pharmacy(medication_id),
            status varchar(20) NOT NULL DEFAULT 'brouillon',
            production_date date NOT NULL,
            producer_name varchar(150),
            qty_good integer NOT NULL DEFAULT 0,
            qty_damaged integer NOT NULL DEFAULT 0,
            qty_rejected integer NOT NULL DEFAULT 0,
            liquid_lost numeric(12,3) NOT NULL DEFAULT 0,
            expected_qty integer,
            found_qty integer,
            missing_qty integer,
            missing_pct numeric(6,2),
            tolerance_applied numeric(5,2),
            out_of_tolerance boolean NOT NULL DEFAULT false,
            justification text,
            total_cost numeric(12,2),
            unit_cost numeric(12,2),
            delivery_date date,
            expiry_date date,
            production_lot_id integer REFERENCES public.production_lots(id),
            cancel_reason text,
            created_by integer NOT NULL REFERENCES public.users(user_id),
            created_at timestamp NOT NULL DEFAULT now(),
            started_at timestamp,
            finished_at timestamp,
            expedited_at timestamp,
            expedited_by integer REFERENCES public.users(user_id),
            CONSTRAINT fab_batches_batch_number_key UNIQUE (batch_number),
            CONSTRAINT fab_batches_status_check
                CHECK (status IN ('brouillon','en_production','termine','expedie','annule')),
            CONSTRAINT fab_batches_qty_good_check CHECK (qty_good >= 0),
            CONSTRAINT fab_batches_qty_damaged_check CHECK (qty_damaged >= 0),
            CONSTRAINT fab_batches_qty_rejected_check CHECK (qty_rejected >= 0),
            CONSTRAINT fab_batches_liquid_lost_check CHECK (liquid_lost >= 0)
        );
        CREATE INDEX IF NOT EXISTS idx_fab_batches_status
            ON public.fab_batches (status);

        CREATE TABLE IF NOT EXISTS public.fab_consumptions (
            id serial PRIMARY KEY,
            batch_id integer NOT NULL REFERENCES public.fab_batches(id),
            purchase_id integer NOT NULL REFERENCES public.fab_intrant_purchases(id),
            quantity numeric(12,3) NOT NULL,
            unit_cost_snapshot numeric(12,2),
            restored_at timestamp,
            CONSTRAINT fab_consumptions_quantity_check CHECK (quantity > 0),
            CONSTRAINT fab_consumptions_cost_check
                CHECK (unit_cost_snapshot IS NULL OR unit_cost_snapshot >= 0)
        );
        CREATE INDEX IF NOT EXISTS idx_fab_consumptions_batch
            ON public.fab_consumptions (batch_id);
        CREATE INDEX IF NOT EXISTS idx_fab_consumptions_purchase
            ON public.fab_consumptions (purchase_id);

        CREATE TABLE IF NOT EXISTS public.fab_settings (
            id integer PRIMARY KEY,
            tolerance_pct numeric(5,2) NOT NULL DEFAULT 2.00,
            stale_days integer NOT NULL DEFAULT 7,
            updated_by integer REFERENCES public.users(user_id),
            updated_at timestamp,
            CONSTRAINT fab_settings_single_row_check CHECK (id = 1),
            CONSTRAINT fab_settings_tolerance_check CHECK (tolerance_pct >= 0),
            CONSTRAINT fab_settings_stale_days_check CHECK (stale_days > 0)
        );
        INSERT INTO public.fab_settings (id, tolerance_pct, stale_days)
        VALUES (1, 2.00, 7)
        ON CONFLICT (id) DO NOTHING;

        INSERT INTO public.application_roles (role_name)
        SELECT 'ProductionManager'
        WHERE NOT EXISTS (
            SELECT 1 FROM public.application_roles WHERE role_name = 'ProductionManager'
        );
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS public.fab_consumptions;
        DROP TABLE IF EXISTS public.fab_batches;
        DROP TABLE IF EXISTS public.fab_intrant_purchases;
        DROP TABLE IF EXISTS public.fab_intrants;
        DROP TABLE IF EXISTS public.fab_settings;
        DELETE FROM public.application_roles
        WHERE role_name = 'ProductionManager'
          AND NOT EXISTS (
              SELECT 1 FROM public.users u
              JOIN public.application_roles ar ON ar.role_id = u.role_id
              WHERE ar.role_name = 'ProductionManager'
          );
    """)
