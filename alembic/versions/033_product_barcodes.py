# alembic/versions/033_product_barcodes.py
"""code-barres des produits de la pharmacie

pharmacy.barcode : 8 chiffres, commence par 1, jamais reutilise ni modifie.
Genere par la sequence pharmacy_barcode_seq (defaut serveur) : tout chemin
d'insertion, y compris la fabrication, obtient un code.

Revision ID: 033_product_barcodes
Revises: 032_psy_scope_transfers
Create Date: 2026-10-27

"""
from alembic import op

revision = '033_product_barcodes'
down_revision = '032_psy_scope_transfers'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SEQUENCE IF NOT EXISTS public.pharmacy_barcode_seq "
               "START WITH 10000000 MINVALUE 10000000 MAXVALUE 19999999 NO CYCLE")
    # Valeur par defaut volatile : PostgreSQL remplit chaque ligne existante.
    op.execute("ALTER TABLE public.pharmacy ADD COLUMN IF NOT EXISTS barcode varchar(12) "
               "NOT NULL DEFAULT nextval('public.pharmacy_barcode_seq')::text")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'pharmacy_barcode_key') THEN
                ALTER TABLE public.pharmacy ADD CONSTRAINT pharmacy_barcode_key UNIQUE (barcode);
            END IF;
        END $$;
    """)


def downgrade():
    op.execute("ALTER TABLE public.pharmacy DROP CONSTRAINT IF EXISTS pharmacy_barcode_key")
    op.execute("ALTER TABLE public.pharmacy DROP COLUMN IF EXISTS barcode")
    op.execute("DROP SEQUENCE IF EXISTS public.pharmacy_barcode_seq")
