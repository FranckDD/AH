"""add p_uuid param to create_medical_record (chantier 4 sous-projet 2)

Revision ID: 008_medrec_uuid_param
Revises: 007_drop_medrec_19param
Create Date: 2026-09-23 00:00:00.000000

Le dossier patient hors-ligne (PowerSync) doit pouvoir creer une
consultation medicale avec un uuid genere cote client, pour que la ligne
locale (creee hors connexion) matche exactement la ligne confirmee par
le serveur une fois synchronisee - meme motif que appointments.uuid
(migration 004_appointments_uuid_unique). Nouveau parametre p_uuid en
dernier avec DEFAULT NULL (meme convention que p_appointment_id,
migration 005) : tout appelant existant qui ne le fournit pas continue
de fonctionner a l'identique. COALESCE(p_uuid, gen_random_uuid())
preserve le comportement actuel (uuid genere par Postgres) quand le
parametre est absent - la colonne a deja un DEFAULT gen_random_uuid()
mais un INSERT qui nomme explicitement la colonne avec une valeur NULL
ignore ce defaut, d'ou le COALESCE explicite.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_medrec_uuid_param'
down_revision: Union[str, Sequence[str], None] = '007_drop_medrec_19param'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
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
            IN p_last_updated_by_name character varying DEFAULT NULL::character varying,
            IN p_appointment_id integer DEFAULT NULL::integer,
            IN p_uuid uuid DEFAULT NULL::uuid
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO public.medical_records (
                patient_id, consultation_date, marital_status, bp, temperature,
                weight, height, medical_history, allergies, symptoms, diagnosis,
                treatment, severity, notes, motif_code, created_by, created_by_name,
                last_updated_by, last_updated_by_name, appointment_id, uuid
            ) VALUES (
                p_patient_id, p_consultation_date, p_marital_status, p_bp, p_temperature,
                p_weight, p_height, p_medical_history, p_allergies, p_symptoms, p_diagnosis,
                p_treatment, p_severity, p_notes, p_motif_code, p_created_by, p_created_by_name,
                p_last_updated_by, p_last_updated_by_name, p_appointment_id,
                COALESCE(p_uuid, gen_random_uuid())
            );
        END;
        $$;
    """)


def downgrade() -> None:
    """Restaure la procedure a 20 parametres (sans p_uuid) - la colonne
    uuid garde son DEFAULT gen_random_uuid(), aucune perte de donnees
    autre que la possibilite de fournir un uuid client explicite."""
    op.execute("""
        DROP PROCEDURE IF EXISTS public.create_medical_record(
            integer, timestamp without time zone, character varying,
            character varying, numeric, numeric, numeric, text, text, text,
            text, text, character varying, text, character varying,
            integer, character varying, integer, character varying,
            integer, uuid
        );
    """)
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
            IN p_last_updated_by_name character varying DEFAULT NULL::character varying,
            IN p_appointment_id integer DEFAULT NULL::integer
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO public.medical_records (
                patient_id, consultation_date, marital_status, bp, temperature,
                weight, height, medical_history, allergies, symptoms, diagnosis,
                treatment, severity, notes, motif_code, created_by, created_by_name,
                last_updated_by, last_updated_by_name, appointment_id
            ) VALUES (
                p_patient_id, p_consultation_date, p_marital_status, p_bp, p_temperature,
                p_weight, p_height, p_medical_history, p_allergies, p_symptoms, p_diagnosis,
                p_treatment, p_severity, p_notes, p_motif_code, p_created_by, p_created_by_name,
                p_last_updated_by, p_last_updated_by_name, p_appointment_id
            );
        END;
        $$;
    """)
