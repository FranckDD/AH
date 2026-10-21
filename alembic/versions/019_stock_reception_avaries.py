# alembic/versions/019_stock_reception_avaries.py
"""stock: production_lots, stock_receipts(+lines), stock_incidents, stock_adjustment_requests, role StockController

Revision ID: 019_stock_reception_avaries
Revises: 018_staff_discount
Create Date: 2026-10-20

"""
from alembic import op

revision = '019_stock_reception_avaries'
down_revision = '018_staff_discount'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.production_lots (
            id serial PRIMARY KEY,
            lot_number varchar(30) NOT NULL,
            product_id integer NOT NULL REFERENCES public.pharmacy(medication_id),
            quantity_produced integer NOT NULL,
            production_date date NOT NULL,
            delivery_date date,
            expiry_date date,
            producer varchar(150),
            status varchar(20) NOT NULL DEFAULT 'produit',
            created_by integer NOT NULL REFERENCES public.users(user_id),
            created_at timestamp NOT NULL DEFAULT now(),
            CONSTRAINT production_lots_lot_number_key UNIQUE (lot_number),
            CONSTRAINT production_lots_quantity_check CHECK (quantity_produced > 0),
            CONSTRAINT production_lots_status_check
                CHECK (status IN ('produit','livre','recu','annule'))
        );
        CREATE INDEX IF NOT EXISTS idx_production_lots_status
            ON public.production_lots (status);

        CREATE TABLE IF NOT EXISTS public.stock_receipts (
            id serial PRIMARY KEY,
            receipt_number varchar(30) NOT NULL,
            origin varchar(20) NOT NULL,
            production_lot_id integer REFERENCES public.production_lots(id),
            supplier varchar(150),
            delivery_ref varchar(100),
            received_date date NOT NULL,
            status varchar(20) NOT NULL DEFAULT 'a_controler',
            created_by integer NOT NULL REFERENCES public.users(user_id),
            created_at timestamp NOT NULL DEFAULT now(),
            controlled_by integer REFERENCES public.users(user_id),
            controlled_at timestamp,
            reject_reason text,
            CONSTRAINT stock_receipts_receipt_number_key UNIQUE (receipt_number),
            CONSTRAINT stock_receipts_origin_check
                CHECK (origin IN ('fabrication','fournisseur')),
            CONSTRAINT stock_receipts_status_check
                CHECK (status IN ('a_controler','valide','rejete')),
            CONSTRAINT stock_receipts_origin_lot_check CHECK (
                (origin = 'fabrication' AND production_lot_id IS NOT NULL) OR
                (origin = 'fournisseur' AND production_lot_id IS NULL))
        );
        CREATE INDEX IF NOT EXISTS idx_stock_receipts_status
            ON public.stock_receipts (status);

        CREATE TABLE IF NOT EXISTS public.stock_receipt_lines (
            id serial PRIMARY KEY,
            receipt_id integer NOT NULL
                REFERENCES public.stock_receipts(id) ON DELETE CASCADE,
            product_id integer NOT NULL REFERENCES public.pharmacy(medication_id),
            qty_expected integer,
            qty_good integer NOT NULL DEFAULT 0,
            qty_damaged integer NOT NULL DEFAULT 0,
            qty_lost integer NOT NULL DEFAULT 0,
            qty_defective integer NOT NULL DEFAULT 0,
            lot_number varchar(30),
            expiry_date date,
            CONSTRAINT stock_receipt_lines_qty_good_check CHECK (qty_good >= 0),
            CONSTRAINT stock_receipt_lines_qty_damaged_check CHECK (qty_damaged >= 0),
            CONSTRAINT stock_receipt_lines_qty_lost_check CHECK (qty_lost >= 0),
            CONSTRAINT stock_receipt_lines_qty_defective_check CHECK (qty_defective >= 0)
        );
        CREATE INDEX IF NOT EXISTS idx_stock_receipt_lines_receipt
            ON public.stock_receipt_lines (receipt_id);

        CREATE TABLE IF NOT EXISTS public.stock_incidents (
            id serial PRIMARY KEY,
            product_id integer NOT NULL REFERENCES public.pharmacy(medication_id),
            kind varchar(20) NOT NULL,
            quantity integer NOT NULL,
            reason text NOT NULL,
            incident_date date NOT NULL,
            status varchar(20) NOT NULL DEFAULT 'a_controler',
            created_by integer NOT NULL REFERENCES public.users(user_id),
            created_at timestamp NOT NULL DEFAULT now(),
            controlled_by integer REFERENCES public.users(user_id),
            controlled_at timestamp,
            reject_reason text,
            CONSTRAINT stock_incidents_kind_check
                CHECK (kind IN ('endommage','perdu','defectueux')),
            CONSTRAINT stock_incidents_quantity_check CHECK (quantity > 0),
            CONSTRAINT stock_incidents_status_check
                CHECK (status IN ('a_controler','valide','rejete'))
        );
        CREATE INDEX IF NOT EXISTS idx_stock_incidents_status
            ON public.stock_incidents (status);

        CREATE TABLE IF NOT EXISTS public.stock_adjustment_requests (
            id serial PRIMARY KEY,
            product_id integer NOT NULL REFERENCES public.pharmacy(medication_id),
            kind varchar(20) NOT NULL,
            quantity integer NOT NULL,
            reason text NOT NULL,
            status varchar(20) NOT NULL DEFAULT 'en_attente',
            requested_by integer NOT NULL REFERENCES public.users(user_id),
            requested_at timestamp NOT NULL DEFAULT now(),
            decided_by integer REFERENCES public.users(user_id),
            decided_at timestamp,
            decision_note text,
            stock_before integer,
            stock_after integer,
            CONSTRAINT stock_adjustment_requests_kind_check
                CHECK (kind IN ('reapprovisionnement','correction')),
            CONSTRAINT stock_adjustment_requests_quantity_check CHECK (quantity >= 0),
            CONSTRAINT stock_adjustment_requests_reappro_qty_check
                CHECK (kind <> 'reapprovisionnement' OR quantity > 0),
            CONSTRAINT stock_adjustment_requests_status_check
                CHECK (status IN ('en_attente','approuve','refuse','annule'))
        );
        CREATE INDEX IF NOT EXISTS idx_stock_adjustment_requests_status
            ON public.stock_adjustment_requests (status);

        INSERT INTO public.application_roles (role_name)
        SELECT 'StockController'
        WHERE NOT EXISTS (
            SELECT 1 FROM public.application_roles WHERE role_name = 'StockController'
        );
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS public.stock_adjustment_requests;
        DROP TABLE IF EXISTS public.stock_incidents;
        DROP TABLE IF EXISTS public.stock_receipt_lines;
        DROP TABLE IF EXISTS public.stock_receipts;
        DROP TABLE IF EXISTS public.production_lots;
        DELETE FROM public.application_roles
        WHERE role_name = 'StockController'
          AND NOT EXISTS (
              SELECT 1 FROM public.users u
              JOIN public.application_roles ar ON ar.role_id = u.role_id
              WHERE ar.role_name = 'StockController'
          );
    """)
