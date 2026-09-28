"""drop dead 19-param create_medical_record overload (chantier L4b-e)

Revision ID: 007_drop_medrec_19param
Revises: 006_caisse_cancel_justification
Create Date: 2026-09-21 00:00:00.000000

Chantier 7c (migration 005) a etendu create_medical_record de 19 a 20
parametres (ajout de p_appointment_id) via CREATE OR REPLACE PROCEDURE.
PostgreSQL ne remplace une procedure que si l'arite est identique - un
changement d'arite cree une NOUVELLE surcharge au lieu de remplacer
l'ancienne. Les deux ont coexiste depuis (verifie par grep exhaustif :
seul repositories/medical_repo.py::create appelle cette procedure,
toujours avec 20 arguments - l'ancienne surcharge a 19 est inatteignable
mais physiquement presente en base). Parquee au chantier 7c pour
nettoyage au chantier L4b-e (registre "gardes de role" - dette technique
liee aux procedures stockees, traitee dans le meme chantier que le reste
du nettoyage de dette parquee).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_drop_medrec_19param'
down_revision: Union[str, Sequence[str], None] = '006_caisse_cancel_justification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        DROP PROCEDURE IF EXISTS public.create_medical_record(
            integer, timestamp without time zone, character varying,
            character varying, numeric, numeric, numeric, text, text, text,
            text, text, character varying, text, character varying,
            integer, character varying, integer, character varying
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        CREATE OR REPLACE PROCEDURE public.create_medical_record(
            IN p_patient_id integer,
            IN p_consultation_date timestamp without time zone,
            IN p_marital_status character varying,
            IN p_bp character varying,
            IN p_temperature numeric,
            IN p_weight numeric,
            IN p_height numeric,
            IN p_medical_history text,
            IN p_allergies text,
            IN p_symptoms text,
            IN p_diagnosis text,
            IN p_treatment text,
            IN p_severity character varying,
            IN p_notes text,
            IN p_motif_code character varying,
            IN p_created_by integer DEFAULT NULL::integer,
            IN p_created_by_name character varying DEFAULT NULL::character varying,
            IN p_last_updated_by integer DEFAULT NULL::integer,
            IN p_last_updated_by_name character varying DEFAULT NULL::character varying
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO public.medical_records (
                patient_id, consultation_date, marital_status, bp, temperature,
                weight, height, medical_history, allergies, symptoms, diagnosis,
                treatment, severity, notes, motif_code, created_by, created_by_name,
                last_updated_by, last_updated_by_name
            ) VALUES (
                p_patient_id, p_consultation_date, p_marital_status, p_bp, p_temperature,
                p_weight, p_height, p_medical_history, p_allergies, p_symptoms, p_diagnosis,
                p_treatment, p_severity, p_notes, p_motif_code, p_created_by, p_created_by_name,
                p_last_updated_by, p_last_updated_by_name
            );
        END;
        $$;
    """)
