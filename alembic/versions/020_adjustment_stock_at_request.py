# alembic/versions/020_adjustment_stock_at_request.py
"""stock_adjustment_requests.stock_at_request : stock du systeme lu a la creation de la demande

Une correction approuvee applique desormais l'ecart (quantite comptee - stock_at_request)
au stock actuel au lieu de fixer une valeur absolue. NULL = demande anterieure
(ancien comportement absolu).

Revision ID: 020_adjustment_stock_at_request
Revises: 019_stock_reception_avaries
Create Date: 2026-10-21

"""
from alembic import op

revision = '020_adjustment_stock_at_request'
down_revision = '019_stock_reception_avaries'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE public.stock_adjustment_requests ADD COLUMN IF NOT EXISTS stock_at_request integer")


def downgrade():
    op.execute("ALTER TABLE public.stock_adjustment_requests DROP COLUMN IF EXISTS stock_at_request")
