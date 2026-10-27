# alembic/versions/034_product_photo_label_size.py
"""photo du produit et taille d'etiquette

pharmacy.photo_path / photo_version : photo optionnelle (fichier sur disque).
organization_config.label_width_mm / label_height_mm : taille des etiquettes.

Revision ID: 034_product_photo_label_size
Revises: 033_product_barcodes
Create Date: 2026-10-27

"""
from alembic import op

revision = '034_product_photo_label_size'
down_revision = '033_product_barcodes'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE public.pharmacy ADD COLUMN IF NOT EXISTS photo_path varchar(255)")
    op.execute("ALTER TABLE public.pharmacy ADD COLUMN IF NOT EXISTS photo_version integer NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE public.organization_config ADD COLUMN IF NOT EXISTS label_width_mm integer NOT NULL DEFAULT 50")
    op.execute("ALTER TABLE public.organization_config ADD COLUMN IF NOT EXISTS label_height_mm integer NOT NULL DEFAULT 30")


def downgrade():
    op.execute("ALTER TABLE public.organization_config DROP COLUMN IF EXISTS label_height_mm")
    op.execute("ALTER TABLE public.organization_config DROP COLUMN IF EXISTS label_width_mm")
    op.execute("ALTER TABLE public.pharmacy DROP COLUMN IF EXISTS photo_version")
    op.execute("ALTER TABLE public.pharmacy DROP COLUMN IF EXISTS photo_path")
