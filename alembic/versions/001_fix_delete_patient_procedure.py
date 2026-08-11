"""fix delete_patient procedure

Revision ID: 001_fix_delete_patient
Revises: c904610b96ec
Create Date: 2026-08-11 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_fix_delete_patient'
down_revision: Union[str, Sequence[str], None] = 'c904610b96ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE OR REPLACE PROCEDURE public.delete_patient(p_patient_id INTEGER, p_deleted_by INTEGER)
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_user_name VARCHAR(100);
        BEGIN
            -- Get user name for audit trail
            SELECT username INTO v_user_name FROM public.users WHERE user_id = p_deleted_by;

            -- Soft delete the patient
            UPDATE public.patients
            SET is_deleted = true, deleted_by = p_deleted_by, deleted_at = NOW()
            WHERE patient_id = p_patient_id;

            -- Log the action to audit_user_actions using correct column name
            INSERT INTO public.audit_user_actions(user_id, resource_type, resource_id, action_performed, username)
            VALUES (p_deleted_by, 'Patient', p_patient_id, 'SOFT DELETE', COALESCE(v_user_name, 'Unknown'));
        END;
        $$;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        DROP PROCEDURE IF EXISTS public.delete_patient(INTEGER, INTEGER);
    """)
