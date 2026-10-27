# alembic/versions/035_spiritual_notes.py
"""notes du conseiller spirituel

Table spiritual_notes : liste commune de notes de rencontres, sans lien avec un patient.

Revision ID: 035_spiritual_notes
Revises: 034_product_photo_label_size
Create Date: 2026-10-28

"""
from alembic import op

revision = '035_spiritual_notes'
down_revision = '034_product_photo_label_size'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.spiritual_notes (
            id serial PRIMARY KEY,
            author_id integer NOT NULL REFERENCES public.users(user_id),
            meeting_date date NOT NULL,
            counsel boolean NOT NULL DEFAULT false,
            prayer boolean NOT NULL DEFAULT false,
            verse_read boolean NOT NULL DEFAULT false,
            discussion boolean NOT NULL DEFAULT false,
            text_given boolean NOT NULL DEFAULT false,
            qa boolean NOT NULL DEFAULT false,
            verse_reference varchar(120),
            no_one_spoke boolean NOT NULL DEFAULT false,
            content text,
            created_at timestamp NOT NULL DEFAULT now(),
            updated_at timestamp NOT NULL DEFAULT now(),
            CONSTRAINT spiritual_notes_content_len_check
                CHECK (content IS NULL OR char_length(content) <= 5000)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_spiritual_notes_order "
               "ON public.spiritual_notes (meeting_date DESC, created_at DESC, id DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_spiritual_notes_author "
               "ON public.spiritual_notes (author_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS public.spiritual_notes")
