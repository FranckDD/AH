# alembic/versions/041_lab_catalogue_extended.py
"""catalogue du laboratoire etendu (fiches fideles) + champs des fiches dans organization_config

examens : section, method, layout_family (CHECK table / three_columns / label_value / narrative /
boxed, defaut label_value), signature_label, print_title, sort_order (0), is_active (vrai).
parametres : print_label, result_kind (CHECK numeric / text / choice / pos_neg ; rempli a partir de
type_valeur / input_type existants), choices (jsonb), is_active (vrai).
organization_config : agrement_number, footer_text, signature_label_default.

Ajout seulement : aucune colonne existante n'est modifiee ni supprimee. Les donnees du catalogue
(examens des fiches, libelles, plages) sont chargees par scripts/seed_lab_catalogue.py.

Revision ID: 041_lab_catalogue_extended
Revises: 040_reference_ranges_days_ga
Create Date: 2026-10-31

"""
from alembic import op

revision = '041_lab_catalogue_extended'
down_revision = '040_reference_ranges_days_ga'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE public.examens ADD COLUMN IF NOT EXISTS section text")
    op.execute("ALTER TABLE public.examens ADD COLUMN IF NOT EXISTS method text")
    op.execute("ALTER TABLE public.examens ADD COLUMN IF NOT EXISTS layout_family varchar(20) NOT NULL DEFAULT 'label_value'")
    op.execute("ALTER TABLE public.examens ADD COLUMN IF NOT EXISTS signature_label text")
    op.execute("ALTER TABLE public.examens ADD COLUMN IF NOT EXISTS print_title text")
    op.execute("ALTER TABLE public.examens ADD COLUMN IF NOT EXISTS sort_order integer NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE public.examens ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true")

    op.execute("ALTER TABLE public.parametres ADD COLUMN IF NOT EXISTS print_label text")
    op.execute("ALTER TABLE public.parametres ADD COLUMN IF NOT EXISTS result_kind varchar(10) NOT NULL DEFAULT 'numeric'")
    op.execute("ALTER TABLE public.parametres ADD COLUMN IF NOT EXISTS choices jsonb")
    op.execute("ALTER TABLE public.parametres ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true")
    # Type de resultat derive des colonnes existantes (conservees) : select -> choice, texte -> text.
    op.execute("""
        UPDATE public.parametres
           SET result_kind = CASE
                 WHEN lower(coalesce(input_type, '')) = 'select' THEN 'choice'
                 WHEN lower(coalesce(type_valeur, '')) IN ('text', 'texte') THEN 'text'
                 WHEN lower(coalesce(input_type, '')) IN ('text', 'area') THEN 'text'
                 ELSE 'numeric' END
    """)

    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_examens_layout_family') THEN
                ALTER TABLE public.examens ADD CONSTRAINT ck_examens_layout_family
                    CHECK (layout_family IN ('table', 'three_columns', 'label_value', 'narrative', 'boxed'));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_parametres_result_kind') THEN
                ALTER TABLE public.parametres ADD CONSTRAINT ck_parametres_result_kind
                    CHECK (result_kind IN ('numeric', 'text', 'choice', 'pos_neg'));
            END IF;
        END $$
    """)

    op.execute("ALTER TABLE public.organization_config ADD COLUMN IF NOT EXISTS agrement_number varchar(200)")
    op.execute("ALTER TABLE public.organization_config ADD COLUMN IF NOT EXISTS footer_text text")
    op.execute("ALTER TABLE public.organization_config ADD COLUMN IF NOT EXISTS signature_label_default varchar(120)")


def downgrade():
    op.execute("ALTER TABLE public.organization_config DROP COLUMN IF EXISTS signature_label_default")
    op.execute("ALTER TABLE public.organization_config DROP COLUMN IF EXISTS footer_text")
    op.execute("ALTER TABLE public.organization_config DROP COLUMN IF EXISTS agrement_number")
    op.execute("ALTER TABLE public.parametres DROP CONSTRAINT IF EXISTS ck_parametres_result_kind")
    op.execute("ALTER TABLE public.examens DROP CONSTRAINT IF EXISTS ck_examens_layout_family")
    for col in ("is_active", "choices", "result_kind", "print_label"):
        op.execute("ALTER TABLE public.parametres DROP COLUMN IF EXISTS %s" % col)
    for col in ("is_active", "sort_order", "print_title", "signature_label", "layout_family", "method", "section"):
        op.execute("ALTER TABLE public.examens DROP COLUMN IF EXISTS %s" % col)
