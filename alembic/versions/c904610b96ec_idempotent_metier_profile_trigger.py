"""idempotent_metier_profile_trigger

Revision ID: c904610b96ec
Revises: 6ea9b46b7a65
Create Date: 2026-08-11 00:11:43.655693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c904610b96ec'
down_revision: Union[str, Sequence[str], None] = '6ea9b46b7a65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE OR REPLACE FUNCTION public.create_metier_profile()
         RETURNS trigger
         LANGUAGE plpgsql
        AS $function$
        DECLARE
          role_nom TEXT;
        BEGIN
          SELECT ar.role_name
            INTO role_nom
            FROM public.application_roles ar
           WHERE ar.role_id = NEW.role_id;

          IF role_nom = 'medecin' THEN
            INSERT INTO public.doctor(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          ELSIF role_nom = 'nurse' THEN
            INSERT INTO public.nurse(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          ELSIF role_nom = 'secretaire' THEN
            INSERT INTO public.secretaire(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          ELSIF role_nom = 'admin' THEN
            INSERT INTO public.admin(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          ELSIF role_nom = 'laborantin' THEN
            INSERT INTO public.laborantin(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          END IF;

          RETURN NEW;
        END;
        $function$
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        CREATE OR REPLACE FUNCTION public.create_metier_profile()
         RETURNS trigger
         LANGUAGE plpgsql
        AS $function$
        DECLARE
          role_nom TEXT;
        BEGIN
          SELECT ar.role_name
            INTO role_nom
            FROM public.application_roles ar
           WHERE ar.role_id = NEW.role_id;

          IF role_nom = 'medecin' THEN
            INSERT INTO public.doctor(user_id) VALUES (NEW.user_id);
          ELSIF role_nom = 'nurse' THEN
            INSERT INTO public.nurse(user_id) VALUES (NEW.user_id);
          ELSIF role_nom = 'secretaire' THEN
            INSERT INTO public.secretaire(user_id) VALUES (NEW.user_id);
          ELSIF role_nom = 'admin' THEN
            INSERT INTO public.admin(user_id) VALUES (NEW.user_id);
          ELSIF role_nom = 'laborantin' THEN
            INSERT INTO public.laborantin(user_id) VALUES (NEW.user_id);
          END IF;

          RETURN NEW;
        END;
        $function$
    """)
