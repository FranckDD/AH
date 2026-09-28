"""unique medical_records.uuid

Revision ID: 011_medrec_uuid_unique
Revises: 010_patients_uuid_motifs_pk
Create Date: 2026-09-24 00:00:00.000000

Correctif Critical de la revue finale du chantier 4 sous-projet 4 : une
prescription creee hors ligne et liee a une consultation elle-meme creee
hors ligne dans le meme geste etait perdue silencieusement a l'envoi (le
server_id local de la consultation n'est jamais dispo au moment ou
PowerSync traite la prescription dans la meme vidange de file). Le
serveur doit desormais pouvoir resoudre la consultation par son uuid,
comme il le fait deja pour le patient (migration 010) - meme motif,
meme prudence : verifie avant ecriture qu'aucun doublon d'uuid n'existe
(colonne deja NOT NULL avec defaut gen_random_uuid(), donc improbable,
mais verifier reste gratuit). IF NOT EXISTS : rejouable sans risque.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011_medrec_uuid_unique'
down_revision: Union[str, Sequence[str], None] = '010_patients_uuid_motifs_pk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS medical_records_uuid_key
            ON public.medical_records (uuid);
    """)


def downgrade() -> None:
    """Reversible sans risque - retire uniquement la garantie d'unicite,
    ne modifie ni ne supprime aucune donnee."""
    op.execute("""
        DROP INDEX IF EXISTS public.medical_records_uuid_key;
    """)
