"""add COALESCE to update_prescription to stop nulling omitted fields

Revision ID: 003_prescription_coalesce
Revises: 002_add_missing_procs
Create Date: 2026-08-12 00:00:00.000000

Corrige E4 (docs/superpowers/SUIVI-AVANCEMENT.md, registre E) :
public.update_prescription reecrivait toutes les colonnes de facon
inconditionnelle. Un PUT avec un payload partiel (champs omis envoyes
comme NULL par le client Python) effacait donc silencieusement les
champs nullable, ou declenchait une violation NOT NULL (409) sur les
champs obligatoires (medication/dosage/frequency/duration/start_date).

Applique le meme pattern COALESCE(param, colonne_actuelle) que
public.update_patient (deja idempotent depuis la migration 002),
alignant les deux procedures de mise a jour sur la meme convention.

CREATE OR REPLACE PROCEDURE : idempotent, aucun DROP, sans risque meme
execute contre une base qui possede deja cette procedure.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_prescription_coalesce'
down_revision: Union[str, Sequence[str], None] = '002_add_missing_procs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE OR REPLACE PROCEDURE public.update_prescription(
            IN p_prescription_id integer,
            IN p_patient_id integer,
            IN p_medication character varying,
            IN p_dosage character varying,
            IN p_frequency character varying,
            IN p_duration character varying,
            IN p_medical_record_id integer DEFAULT NULL::integer,
            IN p_start_date date DEFAULT CURRENT_DATE,
            IN p_end_date date DEFAULT NULL::date,
            IN p_notes text DEFAULT NULL::text,
            IN p_prescribed_by integer DEFAULT NULL::integer,
            IN p_prescribed_by_name character varying DEFAULT NULL::character varying
        )
         LANGUAGE plpgsql
        AS $procedure$
        DECLARE
            v_patient_id  integer;
            v_start_date  date;
            v_end_date    date;
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM prescriptions WHERE prescription_id = p_prescription_id) THEN
                RAISE EXCEPTION 'Aucune prescription avec l''ID % n''existe.', p_prescription_id;
            END IF;

            SELECT COALESCE(p_patient_id, patient_id),
                   COALESCE(p_start_date, start_date),
                   COALESCE(p_end_date, end_date)
              INTO v_patient_id, v_start_date, v_end_date
              FROM prescriptions
             WHERE prescription_id = p_prescription_id;

            IF NOT EXISTS (SELECT 1 FROM patients WHERE patient_id = v_patient_id) THEN
                RAISE EXCEPTION 'Aucun patient avec l''ID % n''existe.', v_patient_id;
            END IF;

            IF p_medical_record_id IS NOT NULL THEN
                IF NOT EXISTS (SELECT 1 FROM medical_records WHERE record_id = p_medical_record_id) THEN
                    RAISE EXCEPTION 'Aucun dossier medical avec l''ID % n''existe.', p_medical_record_id;
                END IF;
            END IF;

            IF v_end_date IS NOT NULL AND v_end_date < v_start_date THEN
                RAISE EXCEPTION 'La date de fin ne peut pas etre anterieure a la date de debut';
            END IF;

            UPDATE public.prescriptions
               SET patient_id         = v_patient_id,
                   medical_record_id  = COALESCE(p_medical_record_id, medical_record_id),
                   medication         = COALESCE(p_medication, medication),
                   dosage             = COALESCE(p_dosage, dosage),
                   frequency          = COALESCE(p_frequency, frequency),
                   duration           = COALESCE(p_duration, duration),
                   start_date         = v_start_date,
                   end_date           = v_end_date,
                   notes              = COALESCE(p_notes, notes),
                   prescribed_by      = COALESCE(p_prescribed_by, prescribed_by),
                   prescribed_by_name = COALESCE(p_prescribed_by_name, prescribed_by_name)
             WHERE prescription_id = p_prescription_id;
        END;
        $procedure$;
    """)


def downgrade() -> None:
    """
    Irreversible par choix : revenir a la version sans COALESCE
    reintroduirait le bug E4 (perte de donnees silencieuse sur payload
    partiel). Meme principe que 001_fix_delete_patient_procedure.py et
    002_add_missing_procedures_triggers.py. Voir
    docs/superpowers/SUIVI-AVANCEMENT.md, registre E, item E4.
    """
    pass
