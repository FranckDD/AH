# alembic/versions/029_daily_control_notify.py
"""controle quotidien : decision d'envoi stockee avec l'instantane (notify_reason et compteurs)

Une notification est EN ATTENTE ssi notify_reason IS NOT NULL AND notified_at IS NULL ; la
relance envoie exactement la decision stockee.

Revision ID: 029_daily_control_notify
Revises: 028_reports_control
Create Date: 2026-10-25

"""
from alembic import op

revision = '029_daily_control_notify'
down_revision = '028_reports_control'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.daily_controls ADD COLUMN IF NOT EXISTS notify_reason text;
        ALTER TABLE public.daily_controls
            ADD COLUMN IF NOT EXISTS notify_new_count integer NOT NULL DEFAULT 0;
        ALTER TABLE public.daily_controls
            ADD COLUMN IF NOT EXISTS notify_open_count integer NOT NULL DEFAULT 0;
        ALTER TABLE public.daily_controls DROP CONSTRAINT IF EXISTS daily_controls_notify_reason_check;
        ALTER TABLE public.daily_controls ADD CONSTRAINT daily_controls_notify_reason_check
            CHECK (notify_reason IN ('nouveau', 'rappel'));
    """)


def downgrade():
    op.execute("""
        ALTER TABLE public.daily_controls DROP CONSTRAINT IF EXISTS daily_controls_notify_reason_check;
        ALTER TABLE public.daily_controls DROP COLUMN IF EXISTS notify_open_count;
        ALTER TABLE public.daily_controls DROP COLUMN IF EXISTS notify_new_count;
        ALTER TABLE public.daily_controls DROP COLUMN IF EXISTS notify_reason;
    """)
