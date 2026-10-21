# alembic/versions/021_lab_stock.py
"""stock labo : lab_stock_products, receipts(+lines), counts(+lines), movements, requests

Revision ID: 021_lab_stock
Revises: 020_adjustment_stock_at_request
Create Date: 2026-10-21

"""
from alembic import op

revision = '021_lab_stock'
down_revision = '020_adjustment_stock_at_request'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.lab_stock_products (
            id serial PRIMARY KEY,
            name varchar(150) NOT NULL,
            packaging varchar(100),
            alert_threshold integer NOT NULL DEFAULT 0,
            supplier varchar(150),
            quantity integer NOT NULL DEFAULT 0,
            last_counted_at timestamp,
            is_active boolean NOT NULL DEFAULT true,
            created_by integer NOT NULL REFERENCES public.users(user_id),
            created_at timestamp NOT NULL DEFAULT now(),
            CONSTRAINT lab_stock_products_threshold_check CHECK (alert_threshold >= 0),
            CONSTRAINT lab_stock_products_quantity_check CHECK (quantity >= 0)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_lab_stock_products_name_active
            ON public.lab_stock_products (lower(name)) WHERE is_active;

        CREATE TABLE IF NOT EXISTS public.lab_stock_receipts (
            id serial PRIMARY KEY,
            invoice_number varchar(100) NOT NULL,
            supplier varchar(150) NOT NULL,
            delivery_date date NOT NULL,
            total_amount numeric(10,2) NOT NULL DEFAULT 0,
            status varchar(20) NOT NULL DEFAULT 'valide',
            cancel_reason text,
            created_by integer NOT NULL REFERENCES public.users(user_id),
            created_at timestamp NOT NULL DEFAULT now(),
            cancelled_by integer REFERENCES public.users(user_id),
            cancelled_at timestamp,
            CONSTRAINT lab_stock_receipts_total_check CHECK (total_amount >= 0),
            CONSTRAINT lab_stock_receipts_status_check
                CHECK (status IN ('valide','annule'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_lab_stock_receipts_supplier_invoice
            ON public.lab_stock_receipts (lower(supplier), lower(invoice_number))
            WHERE status = 'valide';

        CREATE TABLE IF NOT EXISTS public.lab_stock_receipt_lines (
            id serial PRIMARY KEY,
            receipt_id integer NOT NULL
                REFERENCES public.lab_stock_receipts(id) ON DELETE CASCADE,
            product_id integer NOT NULL REFERENCES public.lab_stock_products(id),
            ordered_qty integer,
            received_qty integer NOT NULL,
            unit_price numeric(10,2) NOT NULL DEFAULT 0,
            line_total numeric(10,2) NOT NULL DEFAULT 0,
            lot_number varchar(50) NOT NULL,
            expiry_date date NOT NULL,
            note text,
            CONSTRAINT lab_stock_receipt_lines_ordered_check
                CHECK (ordered_qty IS NULL OR ordered_qty >= 0),
            CONSTRAINT lab_stock_receipt_lines_received_check CHECK (received_qty > 0),
            CONSTRAINT lab_stock_receipt_lines_price_check CHECK (unit_price >= 0),
            CONSTRAINT lab_stock_receipt_lines_total_check CHECK (line_total >= 0)
        );
        CREATE INDEX IF NOT EXISTS idx_lab_stock_receipt_lines_receipt
            ON public.lab_stock_receipt_lines (receipt_id);

        CREATE TABLE IF NOT EXISTS public.lab_stock_counts (
            id serial PRIMARY KEY,
            counted_by integer NOT NULL REFERENCES public.users(user_id),
            counted_at timestamp NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS public.lab_stock_count_lines (
            id serial PRIMARY KEY,
            count_id integer NOT NULL
                REFERENCES public.lab_stock_counts(id) ON DELETE CASCADE,
            product_id integer NOT NULL REFERENCES public.lab_stock_products(id),
            previous_qty integer NOT NULL,
            counted_qty integer NOT NULL,
            CONSTRAINT lab_stock_count_lines_previous_check CHECK (previous_qty >= 0),
            CONSTRAINT lab_stock_count_lines_counted_check CHECK (counted_qty >= 0)
        );
        CREATE INDEX IF NOT EXISTS idx_lab_stock_count_lines_count
            ON public.lab_stock_count_lines (count_id);

        CREATE TABLE IF NOT EXISTS public.lab_stock_movements (
            id serial PRIMARY KEY,
            product_id integer NOT NULL REFERENCES public.lab_stock_products(id),
            change_qty integer NOT NULL,
            movement_type varchar(30) NOT NULL,
            ref_type varchar(30),
            ref_id integer,
            quantity_after integer NOT NULL,
            created_by integer NOT NULL REFERENCES public.users(user_id),
            created_at timestamp NOT NULL DEFAULT now(),
            CONSTRAINT lab_stock_movements_type_check
                CHECK (movement_type IN ('reception','comptage','annulation_reception')),
            CONSTRAINT lab_stock_movements_after_check CHECK (quantity_after >= 0)
        );
        CREATE INDEX IF NOT EXISTS idx_lab_stock_movements_product_date
            ON public.lab_stock_movements (product_id, created_at);

        CREATE TABLE IF NOT EXISTS public.lab_stock_requests (
            id serial PRIMARY KEY,
            product_id integer NOT NULL REFERENCES public.lab_stock_products(id),
            origin varchar(20) NOT NULL,
            level varchar(20),
            status varchar(20) NOT NULL DEFAULT 'a_commander',
            requested_by integer REFERENCES public.users(user_id),
            ordered_by integer REFERENCES public.users(user_id),
            expected_date date,
            closed_by_receipt_id integer REFERENCES public.lab_stock_receipts(id),
            cancel_reason text,
            created_at timestamp NOT NULL DEFAULT now(),
            ordered_at timestamp,
            closed_at timestamp,
            CONSTRAINT lab_stock_requests_origin_check
                CHECK (origin IN ('signalement','seuil','peremption')),
            CONSTRAINT lab_stock_requests_level_check
                CHECK (level IS NULL OR level IN ('bientot_fini','fini')),
            CONSTRAINT lab_stock_requests_status_check
                CHECK (status IN ('a_commander','commande','recu','annule'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_lab_stock_requests_open_product
            ON public.lab_stock_requests (product_id)
            WHERE status IN ('a_commander','commande');

        CREATE INDEX IF NOT EXISTS idx_lab_stock_receipt_lines_product
            ON public.lab_stock_receipt_lines (product_id);
        CREATE INDEX IF NOT EXISTS idx_lab_stock_receipts_delivery_date
            ON public.lab_stock_receipts (delivery_date);
        CREATE INDEX IF NOT EXISTS idx_lab_stock_requests_status
            ON public.lab_stock_requests (status);
        CREATE INDEX IF NOT EXISTS idx_lab_stock_requests_product
            ON public.lab_stock_requests (product_id);
        CREATE INDEX IF NOT EXISTS idx_lab_stock_requests_closed_receipt
            ON public.lab_stock_requests (closed_by_receipt_id);
        CREATE INDEX IF NOT EXISTS idx_lab_stock_count_lines_product
            ON public.lab_stock_count_lines (product_id);
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS public.lab_stock_requests;
        DROP TABLE IF EXISTS public.lab_stock_movements;
        DROP TABLE IF EXISTS public.lab_stock_count_lines;
        DROP TABLE IF EXISTS public.lab_stock_counts;
        DROP TABLE IF EXISTS public.lab_stock_receipt_lines;
        DROP TABLE IF EXISTS public.lab_stock_receipts;
        DROP TABLE IF EXISTS public.lab_stock_products;
    """)
