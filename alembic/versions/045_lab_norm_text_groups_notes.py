# alembic/versions/045_lab_norm_text_groups_notes.py
"""catalogue du laboratoire : textes imprimes des normes, sous-titres et notes fixes

parametres.group_label : sous-titre de la fiche (NUMERATION GLOBULAIRE, ECBU...), <= 80 caracteres.
parametres.norm_text : texte de norme tel qu'imprime pour tout le parametre (« H: 4,0 - 5,5   F: 4,0 - 5,0 »,
    « VN > 20 M/ml »), <= 200 caracteres.
reference_ranges.display_text : texte imprime d'UNE plage (« 4,0 - 5,5 », zeros de precision gardes), <= 60.
examens.fixed_notes : liste ordonnee de blocs de texte fixe de la fiche
    [{"position": "before_body|after_body|after_conclusion", "text": "...", "style": "normal|bold|italic"}].

Ajout seulement : aucune colonne existante n'est modifiee ; tout est facultatif (NULL).

Revision ID: 045_lab_norm_text_groups_notes
Revises: 044_lab_result_snapshot
Create Date: 2026-10-31

"""
from alembic import op

revision = '045_lab_norm_text_groups_notes'
down_revision = '044_lab_result_snapshot'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE public.parametres ADD COLUMN IF NOT EXISTS group_label text")
    op.execute("ALTER TABLE public.parametres ADD COLUMN IF NOT EXISTS norm_text text")
    op.execute("ALTER TABLE public.reference_ranges ADD COLUMN IF NOT EXISTS display_text text")
    op.execute("ALTER TABLE public.examens ADD COLUMN IF NOT EXISTS fixed_notes jsonb")
    op.execute("ALTER TABLE public.parametres DROP CONSTRAINT IF EXISTS ck_parametres_group_label_length")
    op.execute("ALTER TABLE public.parametres ADD CONSTRAINT ck_parametres_group_label_length "
               "CHECK (group_label IS NULL OR length(group_label) <= 80)")
    op.execute("ALTER TABLE public.parametres DROP CONSTRAINT IF EXISTS ck_parametres_norm_text_length")
    op.execute("ALTER TABLE public.parametres ADD CONSTRAINT ck_parametres_norm_text_length "
               "CHECK (norm_text IS NULL OR length(norm_text) <= 200)")
    op.execute("ALTER TABLE public.reference_ranges DROP CONSTRAINT IF EXISTS ck_reference_ranges_display_text_length")
    op.execute("ALTER TABLE public.reference_ranges ADD CONSTRAINT ck_reference_ranges_display_text_length "
               "CHECK (display_text IS NULL OR length(display_text) <= 60)")
    op.execute("ALTER TABLE public.examens DROP CONSTRAINT IF EXISTS ck_examens_fixed_notes_array")
    op.execute("ALTER TABLE public.examens ADD CONSTRAINT ck_examens_fixed_notes_array "
               "CHECK (fixed_notes IS NULL OR jsonb_typeof(fixed_notes) = 'array')")


def downgrade():
    op.execute("ALTER TABLE public.examens DROP CONSTRAINT IF EXISTS ck_examens_fixed_notes_array")
    op.execute("ALTER TABLE public.reference_ranges DROP CONSTRAINT IF EXISTS ck_reference_ranges_display_text_length")
    op.execute("ALTER TABLE public.parametres DROP CONSTRAINT IF EXISTS ck_parametres_norm_text_length")
    op.execute("ALTER TABLE public.parametres DROP CONSTRAINT IF EXISTS ck_parametres_group_label_length")
    op.execute("ALTER TABLE public.examens DROP COLUMN IF EXISTS fixed_notes")
    op.execute("ALTER TABLE public.reference_ranges DROP COLUMN IF EXISTS display_text")
    op.execute("ALTER TABLE public.parametres DROP COLUMN IF EXISTS norm_text")
    op.execute("ALTER TABLE public.parametres DROP COLUMN IF EXISTS group_label")
