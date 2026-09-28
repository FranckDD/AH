"""unique patients.uuid + primary key motif_translations.code

Revision ID: 010_patients_uuid_motifs_pk
Revises: 009_caisse_uuid_and_upload_error
Create Date: 2026-09-24 00:00:00.000000

Chantier 4, sous-projet 4 (formulaires hors ligne) :

1. patients.uuid existe deja (NOT NULL, defaut gen_random_uuid()) et
   models/patient.py le declare unique=True, mais aucun index unique
   n'existe reellement en base - meme situation que K1 (migration 004,
   appointments). Le serveur doit desormais resoudre un patient par son
   uuid (consultation/prescription creees hors ligne pour un patient
   lui-meme cree hors ligne) et rendre idempotent le rejeu d'un
   POST /patients : l'unicite doit etre garantie par la base.

2. motif_translations n'a aucune cle primaire. La replication logique
   PowerSync (stream reference_motifs) a besoin d'une identite de
   replique pour suivre les mises a jour de cette table.

Verifie avant ecriture (2026-09-24) : 102 patients / 102 uuid distincts,
6 motifs / 6 codes distincts - applicable sans nettoyage prealable.
IF NOT EXISTS / verification pg_constraint : rejouable sans risque.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_patients_uuid_motifs_pk'
down_revision: Union[str, Sequence[str], None] = '009_caisse_uuid_and_upload_error'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS patients_uuid_key
            ON public.patients (uuid);
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'motif_translations_pkey'
            ) THEN
                ALTER TABLE public.motif_translations
                    ADD CONSTRAINT motif_translations_pkey PRIMARY KEY (code);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Reversible sans risque - retire uniquement les garanties, ne modifie
    ni ne supprime aucune donnee."""
    op.execute("""
        ALTER TABLE public.motif_translations
            DROP CONSTRAINT IF EXISTS motif_translations_pkey;
    """)
    op.execute("""
        DROP INDEX IF EXISTS public.patients_uuid_key;
    """)
