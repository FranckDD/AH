# alembic/versions/043_user_is_head_lab.py
"""users.is_head_lab : cheffe du laboratoire (droit d'editer le catalogue des examens)

Drapeau booleen (faux par defaut) pose par l'admin sur un compte du role laborantin, comme
users.is_head_nurse pour la rotation des infirmiers. Ajout seulement.

Revision ID: 043_user_is_head_lab
Revises: 042_lab_pregnancy_separation
Create Date: 2026-10-31

"""
from alembic import op

revision = '043_user_is_head_lab'
down_revision = '042_lab_pregnancy_separation'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_head_lab boolean NOT NULL DEFAULT false")


def downgrade():
    op.execute("ALTER TABLE public.users DROP COLUMN IF EXISTS is_head_lab")
