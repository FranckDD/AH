# alembic/versions/046_lab_sheet_variant.py
"""fiches du laboratoire : variante du titre et du bloc patient

organization_config.lab_sheet_title_variant : `centered_results` (defaut : titre « RESULTATS D'ANALYSES DE
BIOLOGIE CLINIQUE » centre, bloc patient centre en gras) ou `left_laboratory` (titre « LABORATOIRE D'ANALYSES DE
BIOLOGIE CLINIQUE » a gauche, ligne DOSSIER en italique bleu, lignes du patient a gauche).

Ajout seulement : aucune colonne existante n'est modifiee.

Revision ID: 046_lab_sheet_variant
Revises: 045_lab_norm_text_groups_notes
Create Date: 2026-10-31

"""
from alembic import op

revision = '046_lab_sheet_variant'
down_revision = '045_lab_norm_text_groups_notes'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE public.organization_config ADD COLUMN IF NOT EXISTS "
               "lab_sheet_title_variant varchar(20) NOT NULL DEFAULT 'centered_results'")
    op.execute("ALTER TABLE public.organization_config DROP CONSTRAINT IF EXISTS ck_organization_config_lab_sheet_variant")
    op.execute("ALTER TABLE public.organization_config ADD CONSTRAINT ck_organization_config_lab_sheet_variant "
               "CHECK (lab_sheet_title_variant IN ('centered_results', 'left_laboratory'))")


def downgrade():
    op.execute("ALTER TABLE public.organization_config DROP CONSTRAINT IF EXISTS ck_organization_config_lab_sheet_variant")
    op.execute("ALTER TABLE public.organization_config DROP COLUMN IF EXISTS lab_sheet_title_variant")
