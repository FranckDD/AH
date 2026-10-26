# alembic/versions/030_lab_amend_invoice_link.py
"""labo : correction tracee d'un resultat valide + lien ligne de facture -> dossier labo

- lab_results.corrected / corrected_at : un resultat valide ne se modifie plus, il se corrige
  (action explicite avec motif) ; l'ancien contenu reste dans lab_result_amendments.
- lab_results.origin_caisse_item_id : ligne de facture (examen facture a la caisse) deja recue au
  labo ; l'index unique empeche de recevoir deux fois la meme ligne.

Revision ID: 030_lab_amend_invoice_link
Revises: 029_daily_control_notify
Create Date: 2026-10-26

"""
from alembic import op

revision = '030_lab_amend_invoice_link'
down_revision = '029_daily_control_notify'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.lab_results ADD COLUMN IF NOT EXISTS corrected boolean NOT NULL DEFAULT false;
        ALTER TABLE public.lab_results ADD COLUMN IF NOT EXISTS corrected_at timestamp;
        ALTER TABLE public.lab_results ADD COLUMN IF NOT EXISTS origin_caisse_item_id integer
            REFERENCES public.caisse_item(item_id) ON DELETE SET NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS uq_lab_results_origin_caisse_item
            ON public.lab_results (origin_caisse_item_id) WHERE origin_caisse_item_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS public.lab_result_amendments (
            amendment_id serial PRIMARY KEY,
            result_id integer NOT NULL REFERENCES public.lab_results(result_id) ON DELETE CASCADE,
            amended_by integer,
            amended_by_name text,
            amended_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'Africa/Douala'),
            reason text NOT NULL,
            previous_values jsonb NOT NULL DEFAULT '[]'::jsonb,
            previous_note text,
            CONSTRAINT lab_result_amendments_reason_check CHECK (length(btrim(reason)) > 0)
        );
        CREATE INDEX IF NOT EXISTS idx_lab_result_amendments_result
            ON public.lab_result_amendments (result_id);
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS public.lab_result_amendments;
        DROP INDEX IF EXISTS public.uq_lab_results_origin_caisse_item;
        ALTER TABLE public.lab_results DROP COLUMN IF EXISTS origin_caisse_item_id;
        ALTER TABLE public.lab_results DROP COLUMN IF EXISTS corrected_at;
        ALTER TABLE public.lab_results DROP COLUMN IF EXISTS corrected;
    """)
