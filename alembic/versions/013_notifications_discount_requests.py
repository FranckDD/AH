"""notifications + discount_requests

Revision ID: 013_notif_discount
Revises: 012_lab_results_uuid
Create Date: 2026-09-25

"""
from alembic import op

revision = '013_notif_discount'
down_revision = '012_lab_results_uuid'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            recipient_user_id INTEGER NOT NULL REFERENCES users(user_id),
            type VARCHAR(50) NOT NULL,
            payload JSONB,
            status VARCHAR(20) NOT NULL DEFAULT 'unread',
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            read_at TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS ix_notifications_recipient_status
            ON notifications (recipient_user_id, status);

        CREATE TABLE IF NOT EXISTS discount_requests (
            id SERIAL PRIMARY KEY,
            transaction_id INTEGER NOT NULL REFERENCES caisse(transaction_id),
            requested_by INTEGER NOT NULL REFERENCES users(user_id),
            requested_to INTEGER NOT NULL REFERENCES users(user_id),
            original_amount NUMERIC(10,2) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            decision_percent INTEGER,
            decision_echelonne_deadline DATE,
            decided_by INTEGER REFERENCES users(user_id),
            decided_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_discount_requests_transaction
            ON discount_requests (transaction_id);
        CREATE INDEX IF NOT EXISTS ix_discount_requests_requested_to_status
            ON discount_requests (requested_to, status);
    """)
    op.execute("""
        ALTER TABLE caisse DROP CONSTRAINT IF EXISTS ck_caisse_status;
        ALTER TABLE caisse ADD CONSTRAINT ck_caisse_status
            CHECK (status IN ('active', 'cancelled', 'refunded', 'pending_approval'));
    """)


def downgrade():
    op.execute("""
        ALTER TABLE caisse DROP CONSTRAINT IF EXISTS ck_caisse_status;
        ALTER TABLE caisse ADD CONSTRAINT ck_caisse_status
            CHECK (status IN ('active', 'cancelled', 'refunded'));
    """)
    op.execute("""
        DROP TABLE IF EXISTS discount_requests;
        DROP TABLE IF EXISTS notifications;
    """)
