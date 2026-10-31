# alembic/versions/044_lab_result_snapshot.py
"""lab_results : copie figee d'impression a la validation, conclusion libre

print_snapshot jsonb : copie versionnee (libelles, unites, normes, ordre, famille, signature) ecrite UNE fois
    par le serveur quand le resultat devient valide ; immuable ensuite. NULL = ancien resultat, imprime par
    l'ancien chemin PDF (pas de remplissage retroactif).
print_snapshot_at / print_snapshot_by : quand (heure de Douala, naive) et par qui la copie courante a ete faite.
print_snapshot_history jsonb : liste des copies remplacees par des corrections (amendements), la plus ancienne
    en premier ; chaque element {snapshot, replaced_at, replaced_by, replaced_by_name, reason}.
conclusion text : texte libre CONCLUSION (<= 5000 caracteres) ; la colonne note continue de servir de NB.

Ajout seulement.

Revision ID: 044_lab_result_snapshot
Revises: 043_user_is_head_lab
Create Date: 2026-10-31

"""
from alembic import op

revision = '044_lab_result_snapshot'
down_revision = '043_user_is_head_lab'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.lab_results
            ADD COLUMN IF NOT EXISTS print_snapshot jsonb,
            ADD COLUMN IF NOT EXISTS print_snapshot_at timestamp without time zone,
            ADD COLUMN IF NOT EXISTS print_snapshot_by integer,
            ADD COLUMN IF NOT EXISTS print_snapshot_history jsonb,
            ADD COLUMN IF NOT EXISTS conclusion text
    """)
    op.execute("ALTER TABLE public.lab_results DROP CONSTRAINT IF EXISTS ck_lab_results_conclusion_length")
    op.execute("ALTER TABLE public.lab_results ADD CONSTRAINT ck_lab_results_conclusion_length "
               "CHECK (conclusion IS NULL OR length(conclusion) <= 5000)")


def downgrade():
    op.execute("ALTER TABLE public.lab_results DROP CONSTRAINT IF EXISTS ck_lab_results_conclusion_length")
    op.execute("""
        ALTER TABLE public.lab_results
            DROP COLUMN IF EXISTS conclusion,
            DROP COLUMN IF EXISTS print_snapshot_history,
            DROP COLUMN IF EXISTS print_snapshot_by,
            DROP COLUMN IF EXISTS print_snapshot_at,
            DROP COLUMN IF EXISTS print_snapshot
    """)
