# alembic/versions/031_lab_param_order.py
"""labo : ordre d'affichage explicite des parametres d'un examen

parametres.ordre : position du parametre dans son examen (banc, detail, fiche imprimee,
catalogue). Les lignes existantes gardent leur ordre actuel (par id).

Revision ID: 031_lab_param_order
Revises: 030_lab_amend_invoice_link
Create Date: 2026-10-26

"""
from alembic import op

revision = '031_lab_param_order'
down_revision = '030_lab_amend_invoice_link'
branch_labels = None
depends_on = None

BACKFILL_SQL = """
    UPDATE public.parametres p SET ordre = r.rn
    FROM (SELECT id, row_number() OVER (PARTITION BY examen_id ORDER BY id) AS rn
          FROM public.parametres) r
    WHERE r.id = p.id
"""


def upgrade():
    op.execute("ALTER TABLE public.parametres ADD COLUMN IF NOT EXISTS ordre integer NOT NULL DEFAULT 0")
    op.execute(BACKFILL_SQL)


def downgrade():
    op.execute("ALTER TABLE public.parametres DROP COLUMN IF EXISTS ordre")
