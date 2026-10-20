# alembic/versions/018_staff_discount.py
"""staff discount: patients.is_staff, caisse staff_discount columns, staff_discount_rules

Revision ID: 018_staff_discount
Revises: 017_triage_infirmiere_medecin
Create Date: 2026-10-20

"""
from alembic import op

revision = '018_staff_discount'
down_revision = '017_triage_infirmiere_medecin'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.patients
            ADD COLUMN IF NOT EXISTS is_staff boolean NOT NULL DEFAULT false;

        ALTER TABLE public.caisse
            ADD COLUMN IF NOT EXISTS staff_discount_amount numeric(10,2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS staff_discount_details jsonb;

        CREATE TABLE IF NOT EXISTS public.staff_discount_rules (
            id serial PRIMARY KEY,
            category varchar(30) NOT NULL,
            min_invoice_amount numeric(10,2) NOT NULL DEFAULT 0,
            rate_percent integer NOT NULL,
            is_active boolean NOT NULL DEFAULT true,
            created_by integer REFERENCES public.users(user_id),
            created_at timestamp NOT NULL DEFAULT now(),
            updated_by integer REFERENCES public.users(user_id),
            updated_at timestamp NOT NULL DEFAULT now(),
            CONSTRAINT staff_discount_rules_category_check
                CHECK (category IN ('medicament','examen','consultation','carnet','autre_soin')),
            CONSTRAINT staff_discount_rules_rate_check
                CHECK (rate_percent BETWEEN 1 AND 100),
            CONSTRAINT staff_discount_rules_min_amount_check
                CHECK (min_invoice_amount >= 0)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_staff_discount_rules_active_category
            ON public.staff_discount_rules (category) WHERE is_active;
    """)


def downgrade():
    op.execute("""
        DROP INDEX IF EXISTS public.uq_staff_discount_rules_active_category;
        DROP TABLE IF EXISTS public.staff_discount_rules;
        ALTER TABLE public.caisse
            DROP COLUMN IF EXISTS staff_discount_details,
            DROP COLUMN IF EXISTS staff_discount_amount;
        ALTER TABLE public.patients
            DROP COLUMN IF EXISTS is_staff;
    """)
