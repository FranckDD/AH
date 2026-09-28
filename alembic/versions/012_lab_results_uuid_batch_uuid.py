"""lab_results uuid + batch_uuid

Revision ID: 012_lab_results_uuid
Revises: 011_medrec_uuid_unique
Create Date: 2026-09-24

"""
from alembic import op

revision = '012_lab_results_uuid'
down_revision = '011_medrec_uuid_unique'
branch_labels = None
depends_on = None


def upgrade():
    # Étape 1 : colonne nullable d'abord (les lignes existantes n'ont pas
    # encore de valeur) - même motif que la migration 009 (caisse.uuid).
    # Étape 2 : backfill uuid with gen_random_uuid() (naturally idempotent)
    # Étape 3 : convert to NOT NULL with server default and unique index
    op.execute("""
        ALTER TABLE public.lab_results
            ADD COLUMN IF NOT EXISTS uuid uuid;
    """)
    op.execute("UPDATE lab_results SET uuid = gen_random_uuid() WHERE uuid IS NULL")
    op.execute("""
        ALTER TABLE public.lab_results
            ALTER COLUMN uuid SET NOT NULL,
            ALTER COLUMN uuid SET DEFAULT gen_random_uuid();
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_lab_results_uuid ON public.lab_results (uuid);
    """)

    # batch_uuid : volontairement NON unique (partagé par toutes les lignes
    # d'une même réception à plusieurs examens - voir spec section 2).
    op.execute("""
        ALTER TABLE public.lab_results
            ADD COLUMN IF NOT EXISTS batch_uuid varchar(36);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_lab_results_batch_uuid ON public.lab_results (batch_uuid);
    """)


def downgrade():
    op.execute("""
        DROP INDEX IF EXISTS public.ix_lab_results_batch_uuid;
    """)
    op.execute("""
        ALTER TABLE public.lab_results DROP COLUMN IF EXISTS batch_uuid;
    """)
    op.execute("""
        DROP INDEX IF EXISTS public.ix_lab_results_uuid;
    """)
    op.execute("""
        ALTER TABLE public.lab_results DROP COLUMN IF EXISTS uuid;
    """)
