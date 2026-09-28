"""organization_config ticket_logo_url + ticket_print_token

Revision ID: 014_ticket_logo_token
Revises: 013_notif_discount
Create Date: 2026-09-28

"""
from alembic import op

revision = '014_ticket_logo_token'
down_revision = '013_notif_discount'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.organization_config
            ADD COLUMN IF NOT EXISTS ticket_logo_url varchar,
            ADD COLUMN IF NOT EXISTS ticket_print_token varchar;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE public.organization_config
            DROP COLUMN IF EXISTS ticket_print_token,
            DROP COLUMN IF EXISTS ticket_logo_url;
    """)
