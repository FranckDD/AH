"""add medical_records.appointment_id (chantier 7c)

Revision ID: 005_medrec_appointment_id
Revises: 004_appointments_uuid_unique
Create Date: 2026-09-21 00:00:00.000000

Note (2026-09-21, corrige par le controleur SDD) : l'identifiant de revision
original ('005_medical_records_appointment_id', 35 caracteres) depassait
la colonne alembic_version.version_num (varchar(32)) - alembic upgrade a
echoue sur l'UPDATE final, transaction annulee proprement (aucun etat
partiel), rien perdu. Renomme en '005_medrec_appointment_id' (25
caracteres) avant nouvel essai.

Chantier 7c (docs/superpowers/SUIVI-AVANCEMENT.md, registre L3c) : relie un
dossier medical au rendez-vous dont il decoule, quand il en vient un.
Nullable - une consultation spontanee (bouton "Nouvelle consultation" du
dossier patient, sans RDV d'origine) reste possible, appointment_id reste
NULL dans ce cas. ON DELETE SET NULL (pas CASCADE) : si un rendez-vous est
un jour supprime, le dossier medical qui en decoule doit survivre.

La procedure stockee public.create_medical_record est etendue avec un
nouveau parametre p_appointment_id, ajoute en dernier avec DEFAULT NULL -
tout appelant existant qui ne le fournit pas continue de fonctionner a
l'identique (aucun appelant PL/pgSQL direct connu en dehors de
repositories/medical_repo.py::create, deja mis a jour dans ce meme plan).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_medrec_appointment_id'
down_revision: Union[str, Sequence[str], None] = '004_appointments_uuid_unique'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        ALTER TABLE public.medical_records
            ADD COLUMN IF NOT EXISTS appointment_id integer
            REFERENCES public.appointments(id) ON DELETE SET NULL;
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


def downgrade() -> None:
    """Restaure la procedure a sa signature d'origine (sans
    p_appointment_id), puis retire la colonne. Aucune perte de donnees
    autre que le lien RDV<->dossier lui-meme, jamais la seule copie d'une
    information (le RDV et le dossier restent intacts independamment)."""
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
    op.execute("ALTER TABLE public.medical_records DROP COLUMN IF EXISTS appointment_id;")
