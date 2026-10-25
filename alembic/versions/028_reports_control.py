# alembic/versions/028_reports_control.py
"""rapports / controle quotidien : daily_controls (anomalies du jour) et report_settings (seuils)

Revision ID: 028_reports_control
Revises: 027_stock_count_line_times
Create Date: 2026-10-25

"""
from alembic import op

revision = '028_reports_control'
down_revision = '027_stock_count_line_times'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.daily_controls (
            id serial PRIMARY KEY,
            business_date date NOT NULL,
            anomalies jsonb NOT NULL DEFAULT '[]'::jsonb,
            new_count integer NOT NULL DEFAULT 0,
            open_count integer NOT NULL DEFAULT 0,
            computed_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
            notified_at timestamp,
            reminder_sent_at timestamp,
            recomputed boolean NOT NULL DEFAULT false,
            CONSTRAINT daily_controls_business_date_key UNIQUE (business_date),
            CONSTRAINT daily_controls_anomalies_array_check CHECK (jsonb_typeof(anomalies) = 'array'),
            CONSTRAINT daily_controls_new_count_check CHECK (new_count >= 0),
            CONSTRAINT daily_controls_open_count_check CHECK (open_count >= 0)
        );
        CREATE INDEX IF NOT EXISTS idx_daily_controls_business_date
            ON public.daily_controls (business_date);

        CREATE TABLE IF NOT EXISTS public.report_settings (
            id smallint PRIMARY KEY,
            cancelled_sales_threshold integer NOT NULL DEFAULT 3,
            adjustment_pending_days integer NOT NULL DEFAULT 3,
            updated_by integer REFERENCES public.users(user_id),
            updated_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
            CONSTRAINT report_settings_single_row_check CHECK (id = 1),
            CONSTRAINT report_settings_cancelled_threshold_check
                CHECK (cancelled_sales_threshold BETWEEN 1 AND 1000),
            CONSTRAINT report_settings_adjustment_days_check
                CHECK (adjustment_pending_days BETWEEN 1 AND 365)
        );
        INSERT INTO public.report_settings (id, cancelled_sales_threshold, adjustment_pending_days)
        VALUES (1, 3, 3)
        ON CONFLICT (id) DO NOTHING;
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS public.report_settings;
        DROP TABLE IF EXISTS public.daily_controls;
    """)
