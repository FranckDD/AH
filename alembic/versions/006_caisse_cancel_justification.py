"""add caisse cancellation columns (chantier 7b)

Revision ID: 006_caisse_cancel_justification
Revises: 005_medrec_appointment_id
Create Date: 2026-09-21 00:00:00.000000

Chantier 7b (docs/superpowers/SUIVI-AVANCEMENT.md, registre L3b) : ajoute
a la table caisse les 3 colonnes deja presentes sur caisse_retrait
(cancelled_by, cancelled_at, cancel_justification), pour que l'annulation
d'une transaction Caisse exige et enregistre une justification, comme le
fait deja l'annulation d'un retrait.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_caisse_cancel_justification'
down_revision: Union[str, Sequence[str], None] = '005_medrec_appointment_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        ALTER TABLE public.caisse
            ADD COLUMN IF NOT EXISTS cancelled_by integer
                REFERENCES public.users(user_id),
            ADD COLUMN IF NOT EXISTS cancelled_at timestamp without time zone,
            ADD COLUMN IF NOT EXISTS cancel_justification text;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        ALTER TABLE public.caisse
            DROP COLUMN IF EXISTS cancelled_by,
            DROP COLUMN IF EXISTS cancelled_at,
            DROP COLUMN IF EXISTS cancel_justification;
    """)
