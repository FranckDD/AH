"""add real UNIQUE constraint on appointments.uuid

Revision ID: 004_appointments_uuid_unique
Revises: 003_prescription_coalesce
Create Date: 2026-09-15 00:00:00.000000

Corrige K1 (docs/superpowers/SUIVI-AVANCEMENT.md, registre K) :
models/appointment.py declare `uuid = Column(UUID(as_uuid=True),
unique=True, ...)`, mais aucune contrainte UNIQUE n'existe reellement en
base - verifie via `\\d appointments`, aucun index unique sur `uuid`.
Deux inserts avec le meme uuid client reussissaient silencieusement.

Le connecteur PowerSync du pilote Rendez-vous (chantier 4,
`AppointmentConnector.js::uploadData`) s'appuie sur cette contrainte pour
traiter un retry d'upload apres timeout reseau comme un succes deja
acquis (409 attendu, catch via `isFatalUploadError`) plutot que de
recreer un rendez-vous en double.

Verifie avant application (aucun doublon, aucun NULL sur les 28 lignes
existantes) - contrainte applicable sans nettoyage de donnees prealable.

CREATE UNIQUE INDEX ... : idempotent via IF NOT EXISTS, sans risque si
rejouee contre une base qui possede deja cet index.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_appointments_uuid_unique'
down_revision: Union[str, Sequence[str], None] = '003_prescription_coalesce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS appointments_uuid_key
            ON public.appointments (uuid);
    """)


def downgrade() -> None:
    """Reversible sans risque - retire uniquement la garantie d'unicite,
    ne modifie ni ne supprime aucune donnee."""
    op.execute("""
        DROP INDEX IF EXISTS public.appointments_uuid_key;
    """)
