"""add missing stored procedures, trigger functions and triggers

Revision ID: 002_add_missing_procs
Revises: 001_fix_delete_patient
Create Date: 2026-08-12 00:00:00.000000

Ces objets existent depuis longtemps sur la base AH2 reelle (crees hors
Alembic, avant que ce projet ne track les procedures/fonctions/triggers)
mais n'avaient jamais ete integres a l'historique de migration. Consequence
directe : `alembic upgrade head` contre une base neuve ne les cree pas, ce
qui casse les modules patients/prescriptions/caisse/users (chantier 2b,
registre D2).

Definitions extraites directement de la base AH2 locale via
pg_get_functiondef()/pg_get_triggerdef() (source live, verifiee a jour) --
et non du dump `ah2_v3_dashmedical.sql` tracke a la racine du depot, qui
s'est revele perime (ex. update_patient/create_patient y manquent les
parametres p_is_clinical/p_is_toxicology/p_is_spiritual presents sur la
base reelle).

Tout est ecrit en CREATE OR REPLACE (PROCEDURE/FUNCTION/TRIGGER, supporte
depuis PG 14) : idempotent, aucun DROP, sans risque meme execute contre
la base AH2 reelle qui possede deja ces objets.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_missing_procs'
down_revision: Union[str, Sequence[str], None] = '001_fix_delete_patient'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # current_user_id() : dependance cachee de track_patient_changes() ci-dessous,
    # jamais suivie par Alembic non plus (confirme via grep sur alembic/versions/).
    op.execute("""
        CREATE OR REPLACE FUNCTION public.current_user_id()
         RETURNS integer
         LANGUAGE plpgsql
         SECURITY DEFINER
        AS $function$
        DECLARE
          user_id INT;
        BEGIN
          SELECT u.user_id INTO user_id
          FROM users u
          WHERE u.username = current_user;

          RETURN user_id;
        END;
        $function$;
    """)

    # create_patient : FUNCTION, 18 arguments, utilisee par repositories/patient_repo.py
    op.execute("""
        CREATE OR REPLACE FUNCTION public.create_patient(
            p_code_patient character varying,
            p_first_name character varying,
            p_last_name character varying,
            p_birth_date date,
            p_gender character varying,
            p_contact_phone character varying,
            p_residence text,
            p_national_id character varying DEFAULT NULL::character varying,
            p_assurance character varying DEFAULT NULL::character varying,
            p_father_name character varying DEFAULT NULL::character varying,
            p_mother_name character varying DEFAULT NULL::character varying,
            p_created_by integer DEFAULT NULL::integer,
            p_created_by_name character varying DEFAULT NULL::character varying,
            p_last_updated_by integer DEFAULT NULL::integer,
            p_last_updated_by_name character varying DEFAULT NULL::character varying,
            p_is_clinical boolean DEFAULT false,
            p_is_toxicology boolean DEFAULT false,
            p_is_spiritual boolean DEFAULT false
        )
         RETURNS TABLE(new_patient_id integer, new_patient_code character varying)
         LANGUAGE plpgsql
        AS $function$
        DECLARE
            v_new_id INT;
            v_final_code VARCHAR;
            v_seq_val INT;
        BEGIN
            v_seq_val := nextval('patients_patient_id_seq');
            v_final_code := p_code_patient;

            INSERT INTO public.patients (
                patient_id,
                code_patient, first_name, last_name, birth_date, gender,
                national_id, contact_phone, assurance, residence,
                father_name, mother_name,
                created_at, created_by, created_by_name,
                last_updated_at, last_updated_by, last_updated_by_name,
                is_clinical, is_toxicology, is_spiritual,
                is_deleted, deleted_at, deleted_by
            ) VALUES (
                v_seq_val,
                v_final_code, p_first_name, p_last_name, p_birth_date, p_gender,
                p_national_id, p_contact_phone, p_assurance, p_residence,
                p_father_name, p_mother_name,
                now(), p_created_by, p_created_by_name,
                now(), p_last_updated_by, p_last_updated_by_name,
                p_is_clinical, p_is_toxicology, p_is_spiritual,
                false, NULL, NULL
            )
            RETURNING patient_id INTO v_new_id;

            RETURN QUERY SELECT v_new_id, v_final_code;
        END;
        $function$;
    """)

    # update_patient : PROCEDURE, 16 arguments, utilisee par repositories/patient_repo.py
    op.execute("""
        CREATE OR REPLACE PROCEDURE public.update_patient(
            IN p_patient_id integer,
            IN p_first_name character varying DEFAULT NULL::character varying,
            IN p_last_name character varying DEFAULT NULL::character varying,
            IN p_birth_date date DEFAULT NULL::date,
            IN p_gender character varying DEFAULT NULL::character varying,
            IN p_national_id character varying DEFAULT NULL::character varying,
            IN p_contact_phone character varying DEFAULT NULL::character varying,
            IN p_assurance character varying DEFAULT NULL::character varying,
            IN p_residence text DEFAULT NULL::text,
            IN p_father_name character varying DEFAULT NULL::character varying,
            IN p_mother_name character varying DEFAULT NULL::character varying,
            IN p_last_updated_by integer DEFAULT NULL::integer,
            IN p_last_updated_by_name character varying DEFAULT NULL::character varying,
            IN p_is_clinical boolean DEFAULT NULL::boolean,
            IN p_is_toxicology boolean DEFAULT NULL::boolean,
            IN p_is_spiritual boolean DEFAULT NULL::boolean
        )
         LANGUAGE plpgsql
        AS $procedure$
        BEGIN
            UPDATE public.patients
            SET
                first_name          = COALESCE(p_first_name, first_name),
                last_name           = COALESCE(p_last_name, last_name),
                birth_date          = COALESCE(p_birth_date, birth_date),
                gender              = COALESCE(p_gender, gender),
                national_id         = COALESCE(p_national_id, national_id),
                contact_phone       = COALESCE(p_contact_phone, contact_phone),
                assurance           = COALESCE(p_assurance, assurance),
                residence           = COALESCE(p_residence, residence),
                father_name         = COALESCE(p_father_name, father_name),
                mother_name         = COALESCE(p_mother_name, mother_name),
                last_updated_at     = now(),
                last_updated_by     = p_last_updated_by,
                last_updated_by_name = p_last_updated_by_name,
                is_clinical         = COALESCE(p_is_clinical, is_clinical),
                is_toxicology       = COALESCE(p_is_toxicology, is_toxicology),
                is_spiritual        = COALESCE(p_is_spiritual, is_spiritual)
            WHERE patient_id = p_patient_id;
        END;
        $procedure$;
    """)

    # create_prescription : PROCEDURE, 11 arguments
    op.execute("""
        CREATE OR REPLACE PROCEDURE public.create_prescription(
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
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM patients WHERE patient_id = p_patient_id) THEN
                RAISE EXCEPTION 'Aucun patient avec l''ID % n''existe.', p_patient_id;
            END IF;

            IF p_medical_record_id IS NOT NULL THEN
                IF NOT EXISTS (SELECT 1 FROM medical_records WHERE record_id = p_medical_record_id) THEN
                    RAISE EXCEPTION 'Aucun dossier medical avec l''ID % n''existe.', p_medical_record_id;
                END IF;
            END IF;

            IF p_end_date IS NOT NULL AND p_end_date < p_start_date THEN
                RAISE EXCEPTION 'La date de fin ne peut pas etre anterieure a la date de debut';
            END IF;

            INSERT INTO public.prescriptions (
                patient_id,
                medical_record_id,
                medication,
                dosage,
                frequency,
                duration,
                start_date,
                end_date,
                notes,
                prescribed_by,
                prescribed_by_name
            ) VALUES (
                p_patient_id,
                p_medical_record_id,
                p_medication,
                p_dosage,
                p_frequency,
                p_duration,
                p_start_date,
                p_end_date,
                p_notes,
                p_prescribed_by,
                p_prescribed_by_name
            );
        END;
        $procedure$;
    """)

    # update_prescription : PROCEDURE, 12 arguments
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
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM prescriptions WHERE prescription_id = p_prescription_id) THEN
                RAISE EXCEPTION 'Aucune prescription avec l''ID % n''existe.', p_prescription_id;
            END IF;

            IF NOT EXISTS (SELECT 1 FROM patients WHERE patient_id = p_patient_id) THEN
                RAISE EXCEPTION 'Aucun patient avec l''ID % n''existe.', p_patient_id;
            END IF;

            IF p_medical_record_id IS NOT NULL THEN
                IF NOT EXISTS (SELECT 1 FROM medical_records WHERE record_id = p_medical_record_id) THEN
                    RAISE EXCEPTION 'Aucun dossier medical avec l''ID % n''existe.', p_medical_record_id;
                END IF;
            END IF;

            IF p_end_date IS NOT NULL AND p_end_date < p_start_date THEN
                RAISE EXCEPTION 'La date de fin ne peut pas etre anterieure a la date de debut';
            END IF;

            UPDATE public.prescriptions
               SET patient_id         = p_patient_id,
                   medical_record_id  = p_medical_record_id,
                   medication         = p_medication,
                   dosage             = p_dosage,
                   frequency          = p_frequency,
                   duration           = p_duration,
                   start_date         = p_start_date,
                   end_date           = p_end_date,
                   notes              = p_notes,
                   prescribed_by      = p_prescribed_by,
                   prescribed_by_name = p_prescribed_by_name
             WHERE prescription_id = p_prescription_id;
        END;
        $procedure$;
    """)

    # Fonctions de trigger + leurs triggers (CREATE OR REPLACE TRIGGER, PG >= 14)
    op.execute("""
        CREATE OR REPLACE FUNCTION public.fn_caisse_protect_cancelled()
         RETURNS trigger
         LANGUAGE plpgsql
        AS $function$
        BEGIN
          IF OLD.status = 'cancelled' THEN
            IF NEW.status <> 'active' THEN
              RAISE EXCEPTION 'Impossible de modifier une transaction annulee (ID=%).', OLD.transaction_id;
            END IF;
          END IF;
          RETURN NEW;
        END;
        $function$;
    """)
    op.execute("""
        CREATE OR REPLACE TRIGGER trg_caisse_protect_cancelled
        BEFORE UPDATE ON public.caisse
        FOR EACH ROW EXECUTE FUNCTION fn_caisse_protect_cancelled();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.set_default_specialty()
         RETURNS trigger
         LANGUAGE plpgsql
        AS $function$
        BEGIN
            IF NEW.postgres_role = 'app_medical' AND NEW.specialty_id IS NULL THEN
                NEW.specialty_id := (SELECT specialty_id FROM medical_specialties WHERE name = 'Generaliste');
            END IF;
            RETURN NEW;
        END;
        $function$;
    """)
    op.execute("""
        CREATE OR REPLACE TRIGGER trg_default_specialty
        BEFORE INSERT ON public.users
        FOR EACH ROW EXECUTE FUNCTION set_default_specialty();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.track_patient_changes()
         RETURNS trigger
         LANGUAGE plpgsql
        AS $function$
        BEGIN
          IF TG_OP = 'INSERT' THEN
            IF NEW.created_by IS NULL THEN
               NEW.created_by := current_user_id();
            END IF;
            NEW.last_updated_by := current_user_id();
          ELSIF TG_OP = 'UPDATE' THEN
            NEW.last_updated_by := current_user_id();
          END IF;
          RETURN NEW;
        END;
        $function$;
    """)
    op.execute("""
        CREATE OR REPLACE TRIGGER trg_patient_tracking
        BEFORE INSERT OR UPDATE ON public.patients
        FOR EACH ROW EXECUTE FUNCTION track_patient_changes();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.update_prescribed_names()
         RETURNS trigger
         LANGUAGE plpgsql
        AS $function$
        BEGIN
          IF NEW.prescribed_by IS NOT NULL THEN
            SELECT username INTO NEW.prescribed_by_name
              FROM users WHERE user_id = NEW.prescribed_by;
          END IF;
          RETURN NEW;
        END;
        $function$;
    """)
    op.execute("""
        CREATE OR REPLACE TRIGGER trg_prescription_names
        BEFORE INSERT OR UPDATE ON public.prescriptions
        FOR EACH ROW EXECUTE FUNCTION update_prescribed_names();
    """)


def downgrade() -> None:
    """
    Irreversible par choix : ces procedures/fonctions/triggers existaient deja
    sur AH2 avant cette migration (crees hors Alembic) et restent utilises par
    le code applicatif (repositories/patient_repo.py, prescriptions_endpoints.py,
    triggers caisse/users/patients/prescriptions). Un DROP casserait ces modules
    sans aucun recours, exactement comme documente dans
    001_fix_delete_patient_procedure.py pour delete_patient. Voir
    docs/superpowers/SUIVI-AVANCEMENT.md, chantier 2b, registre D2.
    """
    pass
