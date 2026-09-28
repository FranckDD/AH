"""add uuid to caisse/caisse_retrait/paiement_echelonne + caisse.upload_error (chantier 4 sous-projet 3)

Revision ID: 009_caisse_uuid_and_upload_error
Revises: 008_medrec_uuid_param
Create Date: 2026-09-23 00:00:00.000000

Aucune des 3 tables (caisse, caisse_retrait, paiement_echelonne) n'avait de
colonne uuid avant ce chantier - contrairement a appointments/medical_records/
prescriptions, qui l'avaient deja avant meme le premier chantier PowerSync.
Meme motif que 004_appointments_uuid_unique.py : DEFAULT gen_random_uuid(),
index unique par table, aucun impact sur les lignes existantes (le defaut
s'applique aussi aux lignes deja en base via ALTER TABLE ... ADD COLUMN
... DEFAULT, PostgreSQL 11+ le fait sans reecrire la table).

caisse.upload_error (text, nullable) : garde-fou anti-perte-silencieuse
(chantier exports/impressions puis ce chantier) - le connecteur PowerSync
(DossierConnector.js) traite aujourd'hui tout echec 400/404/409/422 comme
definitivement fatal et abandonne l'operation sans autre trace qu'un
console.error. Une vente reellement effectuee au guichet, rejetee au moment
de l'upload (ex. stock insuffisant entre-temps), ne doit jamais disparaitre
silencieusement - cette colonne recoit le message d'erreur, affiche comme
badge visible dans l'ecran caisse (Tache 9).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009_caisse_uuid_and_upload_error'
down_revision: Union[str, Sequence[str], None] = '008_medrec_uuid_param'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        ALTER TABLE public.caisse
            ADD COLUMN IF NOT EXISTS uuid uuid DEFAULT gen_random_uuid() NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS caisse_uuid_key ON public.caisse (uuid);

        ALTER TABLE public.caisse
            ADD COLUMN IF NOT EXISTS upload_error text;

        ALTER TABLE public.caisse_retrait
            ADD COLUMN IF NOT EXISTS uuid uuid DEFAULT gen_random_uuid() NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS caisse_retrait_uuid_key ON public.caisse_retrait (uuid);

        ALTER TABLE public.paiement_echelonne
            ADD COLUMN IF NOT EXISTS uuid uuid DEFAULT gen_random_uuid() NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS paiement_echelonne_uuid_key ON public.paiement_echelonne (uuid);
    """)


def downgrade() -> None:
    """Downgrade schema. Aucune perte de donnees metier - uuid/upload_error
    sont des colonnes ajoutees par ce chantier, jamais lues par le code
    existant avant ce chantier."""
    op.execute("""
        DROP INDEX IF EXISTS caisse_uuid_key;
        ALTER TABLE public.caisse DROP COLUMN IF EXISTS uuid;
        ALTER TABLE public.caisse DROP COLUMN IF EXISTS upload_error;

        DROP INDEX IF EXISTS caisse_retrait_uuid_key;
        ALTER TABLE public.caisse_retrait DROP COLUMN IF EXISTS uuid;

        DROP INDEX IF EXISTS paiement_echelonne_uuid_key;
        ALTER TABLE public.paiement_echelonne DROP COLUMN IF EXISTS uuid;
    """)
