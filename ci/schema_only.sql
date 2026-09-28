--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: consultation_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.consultation_type AS ENUM (
    'medical',
    'spirituel'
);


ALTER TYPE public.consultation_type OWNER TO postgres;

--
-- Name: motif_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.motif_enum AS ENUM (
    'consultation',
    'rendez-vous',
    'suivi_prenatal',
    'hospitalisation',
    'urgence',
    'gratuite'
);


ALTER TYPE public.motif_enum OWNER TO postgres;

--
-- Name: prescription_spirituel; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.prescription_spirituel AS ENUM (
    'miel',
    'message',
    'prieres'
);


ALTER TYPE public.prescription_spirituel OWNER TO postgres;

--
-- Name: role_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.role_enum AS ENUM (
    'admin',
    'personnel_medical',
    'medecin',
    'infirmier',
    'secretaire',
    'laborantin',
    'pharmacien'
);


ALTER TYPE public.role_enum OWNER TO postgres;

--
-- Name: type_sexe; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.type_sexe AS ENUM (
    'M',
    'F'
);


ALTER TYPE public.type_sexe OWNER TO postgres;

--
-- Name: check_technician_role(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.check_technician_role(p_technician_id integer) RETURNS boolean
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    IF p_technician_id IS NULL THEN
        RETURN TRUE;
    END IF;
    
    RETURN EXISTS (
        SELECT 1 FROM users 
        WHERE user_id = p_technician_id 
        AND postgres_role = 'app_laborantin'
    );
END;
$$;


ALTER FUNCTION public.check_technician_role(p_technician_id integer) OWNER TO postgres;

--
-- Name: create_appointment(integer, integer, timestamp without time zone, text); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.create_appointment(IN p_patient_id integer, IN p_doctor_id integer, IN p_appointment_date timestamp without time zone, IN p_reason text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (SELECT postgres_role FROM users WHERE user_id = current_user_id()) != 'app_medical' THEN
        RAISE EXCEPTION 'Seul le personnel médical peut créer un rendez-vous.';
    END IF;

    INSERT INTO appointments (patient_id, doctor_id, appointment_date, reason)
    VALUES (p_patient_id, p_doctor_id, p_appointment_date, p_reason);

    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'CREATE APPOINTMENT', p_patient_id);
END;
$$;


ALTER PROCEDURE public.create_appointment(IN p_patient_id integer, IN p_doctor_id integer, IN p_appointment_date timestamp without time zone, IN p_reason text) OWNER TO postgres;

--
-- Name: create_lab_result(integer, character varying, jsonb, integer, text); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.create_lab_result(IN p_patient_id integer, IN p_test_type character varying, IN p_result_value jsonb, IN p_prescribed_by integer, IN p_note text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO lab_results (
        patient_id, test_type, result_value,
        prescribed_by, note
    ) VALUES (
        p_patient_id, p_test_type, p_result_value,
        p_prescribed_by, p_note
    );

    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'CREATE LAB RESULT', p_patient_id);
END;
$$;


ALTER PROCEDURE public.create_lab_result(IN p_patient_id integer, IN p_test_type character varying, IN p_result_value jsonb, IN p_prescribed_by integer, IN p_note text) OWNER TO postgres;

--
-- Name: create_medical_record(integer, timestamp without time zone, character varying, character varying, numeric, numeric, numeric, text, text, text, text, text, character varying, text, character varying, integer, character varying, integer, character varying, integer); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.create_medical_record(IN p_patient_id integer, IN p_consultation_date timestamp without time zone, IN p_marital_status character varying, IN p_bp character varying, IN p_temperature numeric, IN p_weight numeric, IN p_height numeric, IN p_medical_history text, IN p_allergies text, IN p_symptoms text, IN p_diagnosis text, IN p_treatment text, IN p_severity character varying, IN p_notes text, IN p_motif_code character varying, IN p_created_by integer DEFAULT NULL::integer, IN p_created_by_name character varying DEFAULT NULL::character varying, IN p_last_updated_by integer DEFAULT NULL::integer, IN p_last_updated_by_name character varying DEFAULT NULL::character varying, IN p_appointment_id integer DEFAULT NULL::integer)
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


ALTER PROCEDURE public.create_medical_record(IN p_patient_id integer, IN p_consultation_date timestamp without time zone, IN p_marital_status character varying, IN p_bp character varying, IN p_temperature numeric, IN p_weight numeric, IN p_height numeric, IN p_medical_history text, IN p_allergies text, IN p_symptoms text, IN p_diagnosis text, IN p_treatment text, IN p_severity character varying, IN p_notes text, IN p_motif_code character varying, IN p_created_by integer, IN p_created_by_name character varying, IN p_last_updated_by integer, IN p_last_updated_by_name character varying, IN p_appointment_id integer) OWNER TO postgres;

--
-- Name: create_medical_record(integer, timestamp without time zone, character varying, character varying, numeric, numeric, numeric, text, text, text, text, text, character varying, text, character varying, integer, character varying, integer, character varying, integer, uuid); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.create_medical_record(IN p_patient_id integer, IN p_consultation_date timestamp without time zone, IN p_marital_status character varying, IN p_bp character varying, IN p_temperature numeric, IN p_weight numeric, IN p_height numeric, IN p_medical_history text, IN p_allergies text, IN p_symptoms text, IN p_diagnosis text, IN p_treatment text, IN p_severity character varying, IN p_notes text, IN p_motif_code character varying, IN p_created_by integer DEFAULT NULL::integer, IN p_created_by_name character varying DEFAULT NULL::character varying, IN p_last_updated_by integer DEFAULT NULL::integer, IN p_last_updated_by_name character varying DEFAULT NULL::character varying, IN p_appointment_id integer DEFAULT NULL::integer, IN p_uuid uuid DEFAULT NULL::uuid)
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


ALTER PROCEDURE public.create_medical_record(IN p_patient_id integer, IN p_consultation_date timestamp without time zone, IN p_marital_status character varying, IN p_bp character varying, IN p_temperature numeric, IN p_weight numeric, IN p_height numeric, IN p_medical_history text, IN p_allergies text, IN p_symptoms text, IN p_diagnosis text, IN p_treatment text, IN p_severity character varying, IN p_notes text, IN p_motif_code character varying, IN p_created_by integer, IN p_created_by_name character varying, IN p_last_updated_by integer, IN p_last_updated_by_name character varying, IN p_appointment_id integer, IN p_uuid uuid) OWNER TO postgres;

--
-- Name: create_metier_profile(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.create_metier_profile() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
        $$;


ALTER FUNCTION public.create_metier_profile() OWNER TO postgres;

--
-- Name: create_patient(character varying, character varying, character varying, date, character varying, character varying, text, character varying, character varying, character varying, character varying); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.create_patient(IN p_code_patient character varying, IN p_first_name character varying, IN p_last_name character varying, IN p_birth_date date, IN p_gender character varying, IN p_contact_phone character varying, IN p_residence text, IN p_national_id character varying DEFAULT NULL::character varying, IN p_assurance character varying DEFAULT NULL::character varying, IN p_father_name character varying DEFAULT NULL::character varying, IN p_mother_name character varying DEFAULT NULL::character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Insertion du patient
    INSERT INTO patients (
        code_patient, first_name, last_name, birth_date, gender,
        national_id, contact_phone, assurance, residence,
        father_name, mother_name
    ) VALUES (
        p_code_patient, p_first_name, p_last_name, p_birth_date, p_gender,
        p_national_id, p_contact_phone, p_assurance, p_residence,
        p_father_name, p_mother_name
    );

    -- Insertion dans l'audit
    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'CREATE PATIENT', currval('patients_patient_id_seq'));
END;
$$;


ALTER PROCEDURE public.create_patient(IN p_code_patient character varying, IN p_first_name character varying, IN p_last_name character varying, IN p_birth_date date, IN p_gender character varying, IN p_contact_phone character varying, IN p_residence text, IN p_national_id character varying, IN p_assurance character varying, IN p_father_name character varying, IN p_mother_name character varying) OWNER TO postgres;

--
-- Name: create_patient(character varying, character varying, character varying, date, character varying, character varying, text, character varying, character varying, character varying, character varying, integer, character varying, integer, character varying, boolean, boolean, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.create_patient(p_code_patient character varying, p_first_name character varying, p_last_name character varying, p_birth_date date, p_gender character varying, p_contact_phone character varying, p_residence text, p_national_id character varying DEFAULT NULL::character varying, p_assurance character varying DEFAULT NULL::character varying, p_father_name character varying DEFAULT NULL::character varying, p_mother_name character varying DEFAULT NULL::character varying, p_created_by integer DEFAULT NULL::integer, p_created_by_name character varying DEFAULT NULL::character varying, p_last_updated_by integer DEFAULT NULL::integer, p_last_updated_by_name character varying DEFAULT NULL::character varying, p_is_clinical boolean DEFAULT false, p_is_toxicology boolean DEFAULT false, p_is_spiritual boolean DEFAULT false) RETURNS TABLE(new_patient_id integer, new_patient_code character varying)
    LANGUAGE plpgsql
    AS $$
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
        $$;


ALTER FUNCTION public.create_patient(p_code_patient character varying, p_first_name character varying, p_last_name character varying, p_birth_date date, p_gender character varying, p_contact_phone character varying, p_residence text, p_national_id character varying, p_assurance character varying, p_father_name character varying, p_mother_name character varying, p_created_by integer, p_created_by_name character varying, p_last_updated_by integer, p_last_updated_by_name character varying, p_is_clinical boolean, p_is_toxicology boolean, p_is_spiritual boolean) OWNER TO postgres;

--
-- Name: create_prescription(integer, character varying, character varying, character varying, character varying, integer, date, date, text); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.create_prescription(IN p_patient_id integer, IN p_medication character varying, IN p_dosage character varying, IN p_frequency character varying, IN p_duration character varying, IN p_medical_record_id integer DEFAULT NULL::integer, IN p_start_date date DEFAULT CURRENT_DATE, IN p_end_date date DEFAULT NULL::date, IN p_notes text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Vérification de l'existence du patient
    IF NOT EXISTS (
        SELECT 1 FROM patients WHERE patient_id = p_patient_id
    ) THEN
        RAISE EXCEPTION 'Aucun patient avec l''ID % n''existe.', p_patient_id;
    END IF;

    -- Vérification de l'existence du dossier médical (si fourni)
    IF p_medical_record_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM medical_records WHERE record_id = p_medical_record_id
        ) THEN
            RAISE EXCEPTION 'Aucun dossier médical avec l''ID % n''existe.', p_medical_record_id;
        END IF;
    END IF;

    -- Vérification des dates
    IF p_end_date IS NOT NULL AND p_end_date < p_start_date THEN
        RAISE EXCEPTION 'La date de fin (%) ne peut pas être antérieure à la date de début (%)',
            p_end_date, p_start_date;
    END IF;

    -- Insertion de l'ordonnance
    INSERT INTO prescriptions (
        patient_id, medical_record_id, medication,
        dosage, frequency, duration, start_date,
        end_date, notes
    ) VALUES (
        p_patient_id, p_medical_record_id, p_medication,
        p_dosage, p_frequency, p_duration, p_start_date,
        p_end_date, p_notes
    );

    -- Insertion dans l'audit
    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'CREATE PRESCRIPTION', p_patient_id);
END;
$$;


ALTER PROCEDURE public.create_prescription(IN p_patient_id integer, IN p_medication character varying, IN p_dosage character varying, IN p_frequency character varying, IN p_duration character varying, IN p_medical_record_id integer, IN p_start_date date, IN p_end_date date, IN p_notes text) OWNER TO postgres;

--
-- Name: create_prescription(integer, character varying, character varying, character varying, character varying, integer, date, date, text, integer, character varying); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.create_prescription(IN p_patient_id integer, IN p_medication character varying, IN p_dosage character varying, IN p_frequency character varying, IN p_duration character varying, IN p_medical_record_id integer DEFAULT NULL::integer, IN p_start_date date DEFAULT CURRENT_DATE, IN p_end_date date DEFAULT NULL::date, IN p_notes text DEFAULT NULL::text, IN p_prescribed_by integer DEFAULT NULL::integer, IN p_prescribed_by_name character varying DEFAULT NULL::character varying)
    LANGUAGE plpgsql
    AS $$
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
        $$;


ALTER PROCEDURE public.create_prescription(IN p_patient_id integer, IN p_medication character varying, IN p_dosage character varying, IN p_frequency character varying, IN p_duration character varying, IN p_medical_record_id integer, IN p_start_date date, IN p_end_date date, IN p_notes text, IN p_prescribed_by integer, IN p_prescribed_by_name character varying) OWNER TO postgres;

--
-- Name: create_spiritual_consultation(integer, character varying, text, timestamp without time zone); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.create_spiritual_consultation(IN p_patient_id integer, IN p_prescription character varying, IN p_notes text DEFAULT NULL::text, IN p_consultation_date timestamp without time zone DEFAULT NULL::timestamp without time zone)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_prescription_valid BOOLEAN;
BEGIN
    -- Vérification du rôle (secretaire ou medical)
    IF (SELECT postgres_role FROM users WHERE user_id = current_user_id()) NOT IN ('app_secretaire', 'app_medical') THEN
        RAISE EXCEPTION 'Accès refusé. Seuls le secrétariat et le personnel médical peuvent créer des consultations spirituelles.';
    END IF;

    -- Validation du type de prescription
    SELECT p_prescription IN ('Hony', 'Massage', 'Prayer') INTO v_prescription_valid;
    IF NOT v_prescription_valid THEN
        RAISE EXCEPTION 'Prescription invalide. Doit être Hony, Massage ou Prayer';
    END IF;

    -- Vérification de l'existence du patient
    IF NOT EXISTS (SELECT 1 FROM patients WHERE patient_id = p_patient_id) THEN
        RAISE EXCEPTION 'Patient ID % non trouvé', p_patient_id;
    END IF;

    -- Insertion avec gestion des valeurs par défaut
    INSERT INTO consultation_spirituel (
        patient_id,
        prescription,
        consultation_date,
        created_by,
        notes
    ) VALUES (
        p_patient_id,
        p_prescription,
        COALESCE(p_consultation_date, NOW()),
        current_user_id(),
        p_notes
    );

    -- Audit
    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'CREATE SPIRITUAL CONSULTATION', p_patient_id);
END;
$$;


ALTER PROCEDURE public.create_spiritual_consultation(IN p_patient_id integer, IN p_prescription character varying, IN p_notes text, IN p_consultation_date timestamp without time zone) OWNER TO postgres;

--
-- Name: create_user(character varying, text, character varying, character varying, integer, integer); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.create_user(IN p_username character varying, IN p_password_hash text, IN p_full_name character varying, IN p_postgres_role character varying, IN p_specialty_id integer DEFAULT NULL::integer, IN p_role_id integer DEFAULT NULL::integer)
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (SELECT role_name FROM application_roles WHERE role_id = 
        (SELECT role_id FROM users WHERE user_id = current_user_id())) != 'admin' THEN
        RAISE EXCEPTION 'Seul un administrateur peut créer des utilisateurs';
    END IF;

    INSERT INTO users (
        username, password_hash, full_name,
        postgres_role, specialty_id, role_id
    ) VALUES (
        p_username, p_password_hash, p_full_name,
        p_postgres_role, p_specialty_id, p_role_id
    );
END;
$$;


ALTER PROCEDURE public.create_user(IN p_username character varying, IN p_password_hash text, IN p_full_name character varying, IN p_postgres_role character varying, IN p_specialty_id integer, IN p_role_id integer) OWNER TO postgres;

--
-- Name: create_view_for_motif(character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.create_view_for_motif(motif_in character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    view_name VARCHAR;
BEGIN
    view_name := 'vue_' || motif_in;
    EXECUTE format(
      'CREATE OR REPLACE VIEW %I AS SELECT * FROM medical_records WHERE motif_code = %L',
      view_name, motif_in
    );
END;
$$;


ALTER FUNCTION public.create_view_for_motif(motif_in character varying) OWNER TO postgres;

--
-- Name: current_user_id(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.current_user_id() RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
        DECLARE
          user_id INT;
        BEGIN
          SELECT u.user_id INTO user_id
          FROM users u
          WHERE u.username = current_user;

          RETURN user_id;
        END;
        $$;


ALTER FUNCTION public.current_user_id() OWNER TO postgres;

--
-- Name: delete_appointment(integer); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.delete_appointment(IN p_appointment_id integer)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_patient_id INT;
BEGIN
    SELECT patient_id INTO v_patient_id FROM appointments WHERE appointment_id = p_appointment_id;
    
    DELETE FROM appointments WHERE appointment_id = p_appointment_id;

    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'DELETE APPOINTMENT', v_patient_id);
END;
$$;


ALTER PROCEDURE public.delete_appointment(IN p_appointment_id integer) OWNER TO postgres;

--
-- Name: delete_patient(integer, integer); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.delete_patient(IN p_patient_id integer, IN p_deleted_by integer)
    LANGUAGE plpgsql
    AS $$
        DECLARE
            v_user_name VARCHAR(100);
        BEGIN
            -- Get user name for audit trail
            SELECT username INTO v_user_name FROM public.users WHERE user_id = p_deleted_by;

            -- Soft delete the patient
            UPDATE public.patients
            SET is_deleted = true, deleted_by = p_deleted_by, deleted_at = NOW()
            WHERE patient_id = p_patient_id;

            -- Log the action to audit_user_actions using correct column name
            INSERT INTO public.audit_user_actions(user_id, resource_type, resource_id, action_performed, username)
            VALUES (p_deleted_by, 'Patient', p_patient_id, 'SOFT DELETE', COALESCE(v_user_name, 'Unknown'));
        END;
        $$;


ALTER PROCEDURE public.delete_patient(IN p_patient_id integer, IN p_deleted_by integer) OWNER TO postgres;

--
-- Name: fix_lab_names(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fix_lab_names() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Mise à jour du nom du TECHNICIEN (seulement si l'ID est là)
    -- On utilise uniquement 'full_name' car 'first_name' n'existe pas
    IF NEW.technician_id IS NOT NULL THEN
        SELECT full_name INTO NEW.technician_name 
        FROM public.users 
        WHERE user_id = NEW.technician_id;
    END IF;

    -- Mise à jour du nom du CRÉATEUR (seulement si l'ID est là)
    IF NEW.created_by IS NOT NULL THEN
        SELECT full_name INTO NEW.created_by_name 
        FROM public.users 
        WHERE user_id = NEW.created_by;
    END IF;

    -- NOTE : On ne touche PAS à prescribed_by (on garde juste l'ID)
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.fix_lab_names() OWNER TO postgres;

--
-- Name: fn_caisse_protect_cancelled(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_caisse_protect_cancelled() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
          IF OLD.status = 'cancelled' THEN
            IF NEW.status <> 'active' THEN
              RAISE EXCEPTION 'Impossible de modifier une transaction annulee (ID=%).', OLD.transaction_id;
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$;


ALTER FUNCTION public.fn_caisse_protect_cancelled() OWNER TO postgres;

--
-- Name: log_user_action(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.log_user_action() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    v_user_id INTEGER;
    v_resource_id INTEGER;
    v_action_performed VARCHAR(50);
    v_old_values JSONB := NULL;
    v_new_values JSONB := NULL;
BEGIN
    -- 1. Récupération de l'ID de la ressource (Adapté selon la table)
    IF TG_TABLE_NAME = 'patients' THEN
        v_resource_id := COALESCE(NEW.patient_id, OLD.patient_id);
    ELSIF TG_TABLE_NAME = 'medical_records' THEN
        v_resource_id := COALESCE(NEW.record_id, OLD.record_id); -- Vérifiez si c'est record_id ou patient_id
    ELSIF TG_TABLE_NAME = 'prescriptions' THEN
        v_resource_id := COALESCE(NEW.prescription_id, OLD.prescription_id);
    ELSE
        -- Fallback générique si possible, sinon NULL
        v_resource_id := NULL;
    END IF;

    -- 2. Détermination de l'Action et des Valeurs
    IF TG_OP = 'INSERT' THEN
        v_action_performed := 'CREATE';
        v_new_values := to_jsonb(NEW);
        -- Pour un insert, l'utilisateur est le créateur
        -- On tente de récupérer created_by si la colonne existe dans la table cible
        BEGIN
            v_user_id := NEW.created_by;
        EXCEPTION WHEN OTHERS THEN
            v_user_id := NULL; -- Si la colonne n'existe pas
        END;

    ELSIF TG_OP = 'UPDATE' THEN
        v_new_values := to_jsonb(NEW);
        v_old_values := to_jsonb(OLD);
        
        -- Détection du Soft Delete (Si on passe de is_deleted=false à true)
        -- On utilise to_jsonb pour vérifier l'existence de la clé sans erreur
        IF (v_new_values ? 'is_deleted') AND (CAST(v_new_values->>'is_deleted' AS BOOLEAN) = true) AND (CAST(v_old_values->>'is_deleted' AS BOOLEAN) = false) THEN
            v_action_performed := 'SOFT_DELETE';
            -- Pour un soft delete, l'utilisateur est celui qui a supprimé
            BEGIN
                v_user_id := NEW.deleted_by;
            EXCEPTION WHEN OTHERS THEN v_user_id := NULL; END;
        ELSE
            v_action_performed := 'UPDATE';
            -- Pour un update standard, l'utilisateur est celui qui a mis à jour
            BEGIN
                v_user_id := NEW.last_updated_by;
            EXCEPTION WHEN OTHERS THEN v_user_id := NULL; END;
        END IF;

    ELSIF TG_OP = 'DELETE' THEN
        v_action_performed := 'HARD_DELETE';
        v_old_values := to_jsonb(OLD);
        -- Difficile de savoir qui a fait un DELETE physique via le trigger seul
        -- On essaie de prendre l'ancien updater ou on laisse NULL
        v_user_id := NULL; 
    END IF;

    -- 3. Sécurité : Si v_user_id est NULL (ex: action via SQL direct), on essaie de trouver l'ID via le current_user postgres
    -- Cela évite l'erreur de contrainte NOT NULL si votre application n'a pas rempli created_by/updated_by
    IF v_user_id IS NULL THEN
        SELECT user_id INTO v_user_id FROM public.users WHERE username = current_user LIMIT 1;
        
        -- Si toujours NULL (cas rare ou utilisateur système non mappé), on met une valeur par défaut ou on lève une alerte.
        -- Pour l'instant, on suppose que l'appli envoie toujours un user valide.
    END IF;

    -- 4. Insertion dans la table d'audit (Correspondance exacte des colonnes)
    INSERT INTO public.audit_user_actions (
        user_id,
        resource_type,
        resource_id,
        action_performed,
        old_values,
        new_values,
        ip_address -- Optionnel: peut être récupéré via inet_client_addr() si dispo
    ) VALUES (
        v_user_id,              -- Doit exister dans la table users !
        TG_TABLE_NAME,          -- resource_type
        v_resource_id,          -- resource_id
        v_action_performed,     -- action_performed
        v_old_values,           -- old_values (JSONB)
        v_new_values,           -- new_values (JSONB)
        inet_client_addr()::text -- Récupère l'IP du client si possible
    );

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.log_user_action() OWNER TO postgres;

--
-- Name: refresh_updated_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.refresh_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$;


ALTER FUNCTION public.refresh_updated_at() OWNER TO postgres;

--
-- Name: set_default_specialty(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.set_default_specialty() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.postgres_role = 'app_medical' AND NEW.specialty_id IS NULL THEN
                NEW.specialty_id := (SELECT specialty_id FROM medical_specialties WHERE name = 'Generaliste');
            END IF;
            RETURN NEW;
        END;
        $$;


ALTER FUNCTION public.set_default_specialty() OWNER TO postgres;

--
-- Name: track_patient_changes(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.track_patient_changes() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
        $$;


ALTER FUNCTION public.track_patient_changes() OWNER TO postgres;

--
-- Name: update_appointment(integer, integer, timestamp without time zone, integer, text, character varying, text); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.update_appointment(IN p_appointment_id integer, IN p_doctor_id integer DEFAULT NULL::integer, IN p_appointment_date timestamp without time zone DEFAULT NULL::timestamp without time zone, IN p_duration_min integer DEFAULT NULL::integer, IN p_reason text DEFAULT NULL::text, IN p_status character varying DEFAULT NULL::character varying, IN p_notes text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (SELECT postgres_role FROM users WHERE user_id = current_user_id()) != 'app_medical' THEN
        RAISE EXCEPTION 'Accès réservé au personnel médical';
    END IF;

    UPDATE appointments SET
        doctor_id = COALESCE(p_doctor_id, doctor_id),
        appointment_date = COALESCE(p_appointment_date, appointment_date),
        duration_min = COALESCE(p_duration_min, duration_min),
        reason = COALESCE(p_reason, reason),
        status = COALESCE(p_status, status),
        notes = COALESCE(p_notes, notes)
    WHERE appointment_id = p_appointment_id;

    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'UPDATE APPOINTMENT', (SELECT patient_id FROM appointments WHERE appointment_id = p_appointment_id));
END;
$$;


ALTER PROCEDURE public.update_appointment(IN p_appointment_id integer, IN p_doctor_id integer, IN p_appointment_date timestamp without time zone, IN p_duration_min integer, IN p_reason text, IN p_status character varying, IN p_notes text) OWNER TO postgres;

--
-- Name: update_medical_record(integer, character varying, character varying, numeric, numeric, numeric, text, text, text, text, text, character varying, text); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.update_medical_record(IN p_record_id integer, IN p_marital_status character varying DEFAULT NULL::character varying, IN p_bp character varying DEFAULT NULL::character varying, IN p_temperature numeric DEFAULT NULL::numeric, IN p_weight numeric DEFAULT NULL::numeric, IN p_height numeric DEFAULT NULL::numeric, IN p_medical_history text DEFAULT NULL::text, IN p_allergies text DEFAULT NULL::text, IN p_symptoms text DEFAULT NULL::text, IN p_diagnosis text DEFAULT NULL::text, IN p_treatment text DEFAULT NULL::text, IN p_severity character varying DEFAULT NULL::character varying, IN p_notes text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (SELECT postgres_role FROM users WHERE user_id = current_user_id()) != 'app_medical' THEN
        RAISE EXCEPTION 'Accès réservé au personnel médical';
    END IF;

    UPDATE medical_records SET
        marital_status = COALESCE(p_marital_status, marital_status),
        bp = COALESCE(p_bp, bp),
        temperature = COALESCE(p_temperature, temperature),
        weight = COALESCE(p_weight, weight),
        height = COALESCE(p_height, height),
        medical_history = COALESCE(p_medical_history, medical_history),
        allergies = COALESCE(p_allergies, allergies),
        symptoms = COALESCE(p_symptoms, symptoms),
        diagnosis = COALESCE(p_diagnosis, diagnosis),
        treatment = COALESCE(p_treatment, treatment),
        severity = COALESCE(p_severity, severity),
        notes = COALESCE(p_notes, notes),
        last_updated_by = current_user_id()
    WHERE record_id = p_record_id;

    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'UPDATE MEDICAL RECORD', (SELECT patient_id FROM medical_records WHERE record_id = p_record_id));
END;
$$;


ALTER PROCEDURE public.update_medical_record(IN p_record_id integer, IN p_marital_status character varying, IN p_bp character varying, IN p_temperature numeric, IN p_weight numeric, IN p_height numeric, IN p_medical_history text, IN p_allergies text, IN p_symptoms text, IN p_diagnosis text, IN p_treatment text, IN p_severity character varying, IN p_notes text) OWNER TO postgres;

--
-- Name: update_medical_record(integer, character varying, character varying, numeric, numeric, numeric, text, text, text, text, text, character varying, text, character varying, integer, character varying); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.update_medical_record(IN p_record_id integer, IN p_marital_status character varying DEFAULT NULL::character varying, IN p_bp character varying DEFAULT NULL::character varying, IN p_temperature numeric DEFAULT NULL::numeric, IN p_weight numeric DEFAULT NULL::numeric, IN p_height numeric DEFAULT NULL::numeric, IN p_medical_history text DEFAULT NULL::text, IN p_allergies text DEFAULT NULL::text, IN p_symptoms text DEFAULT NULL::text, IN p_diagnosis text DEFAULT NULL::text, IN p_treatment text DEFAULT NULL::text, IN p_severity character varying DEFAULT NULL::character varying, IN p_notes text DEFAULT NULL::text, IN p_motif_code character varying DEFAULT NULL::character varying, IN p_last_updated_by integer DEFAULT NULL::integer, IN p_last_updated_by_name character varying DEFAULT NULL::character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Note: La vérification du rôle (current_user_id) peut être délicate si le contexte n'est pas set.
    -- Si vous gérez les permissions via l'app Python, vous pouvez commenter ce IF.
    IF (SELECT postgres_role FROM users WHERE user_id = current_user_id()) != 'app_medical' THEN
        RAISE EXCEPTION 'Accès réservé au personnel médical';
    END IF;

    UPDATE medical_records SET
        marital_status = COALESCE(p_marital_status, marital_status),
        bp = COALESCE(p_bp, bp),
        temperature = COALESCE(p_temperature, temperature),
        weight = COALESCE(p_weight, weight),
        height = COALESCE(p_height, height),
        medical_history = COALESCE(p_medical_history, medical_history),
        allergies = COALESCE(p_allergies, allergies),
        symptoms = COALESCE(p_symptoms, symptoms),
        diagnosis = COALESCE(p_diagnosis, diagnosis),
        treatment = COALESCE(p_treatment, treatment),
        severity = COALESCE(p_severity, severity),
        notes = COALESCE(p_notes, notes),
        motif_code = COALESCE(p_motif_code, motif_code),
        last_updated_by = p_last_updated_by,
        last_updated_by_name = p_last_updated_by_name
    WHERE record_id = p_record_id;

    -- L'audit est géré par Python (Controller)
END;
$$;


ALTER PROCEDURE public.update_medical_record(IN p_record_id integer, IN p_marital_status character varying, IN p_bp character varying, IN p_temperature numeric, IN p_weight numeric, IN p_height numeric, IN p_medical_history text, IN p_allergies text, IN p_symptoms text, IN p_diagnosis text, IN p_treatment text, IN p_severity character varying, IN p_notes text, IN p_motif_code character varying, IN p_last_updated_by integer, IN p_last_updated_by_name character varying) OWNER TO postgres;

--
-- Name: update_patient(integer, character varying, character varying, date, character varying, character varying, character varying, character varying, text, character varying, character varying); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.update_patient(IN p_patient_id integer, IN p_first_name character varying DEFAULT NULL::character varying, IN p_last_name character varying DEFAULT NULL::character varying, IN p_birth_date date DEFAULT NULL::date, IN p_gender character varying DEFAULT NULL::character varying, IN p_national_id character varying DEFAULT NULL::character varying, IN p_contact_phone character varying DEFAULT NULL::character varying, IN p_assurance character varying DEFAULT NULL::character varying, IN p_residence text DEFAULT NULL::text, IN p_father_name character varying DEFAULT NULL::character varying, IN p_mother_name character varying DEFAULT NULL::character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Vérification de rôle
    IF (SELECT postgres_role FROM users WHERE user_id = current_user_id())
       NOT IN ('app_secretaire', 'app_medical') THEN
        RAISE EXCEPTION 'Accès refusé. Rôle non autorisé.';
    END IF;

    -- Mise à jour des champs (seuls ceux non-NULL écrasent les existants)
    UPDATE patients
    SET
        first_name    = COALESCE(p_first_name, first_name),
        last_name     = COALESCE(p_last_name, last_name),
        birth_date    = COALESCE(p_birth_date, birth_date),
        gender        = COALESCE(p_gender, gender),
        national_id   = COALESCE(p_national_id, national_id),
        contact_phone = COALESCE(p_contact_phone, contact_phone),
        assurance     = COALESCE(p_assurance, assurance),
        residence     = COALESCE(p_residence, residence),
        father_name   = COALESCE(p_father_name, father_name),
        mother_name   = COALESCE(p_mother_name, mother_name)
    WHERE patient_id = p_patient_id;

    -- Audit
    INSERT INTO audit_user_actions(user_name, action, patient_id)
    VALUES (current_user, 'UPDATE PATIENT', p_patient_id);
END;
$$;


ALTER PROCEDURE public.update_patient(IN p_patient_id integer, IN p_first_name character varying, IN p_last_name character varying, IN p_birth_date date, IN p_gender character varying, IN p_national_id character varying, IN p_contact_phone character varying, IN p_assurance character varying, IN p_residence text, IN p_father_name character varying, IN p_mother_name character varying) OWNER TO postgres;

--
-- Name: update_patient(integer, character varying, character varying, date, character varying, character varying, character varying, character varying, text, character varying, character varying, integer, character varying, boolean, boolean, boolean); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.update_patient(IN p_patient_id integer, IN p_first_name character varying DEFAULT NULL::character varying, IN p_last_name character varying DEFAULT NULL::character varying, IN p_birth_date date DEFAULT NULL::date, IN p_gender character varying DEFAULT NULL::character varying, IN p_national_id character varying DEFAULT NULL::character varying, IN p_contact_phone character varying DEFAULT NULL::character varying, IN p_assurance character varying DEFAULT NULL::character varying, IN p_residence text DEFAULT NULL::text, IN p_father_name character varying DEFAULT NULL::character varying, IN p_mother_name character varying DEFAULT NULL::character varying, IN p_last_updated_by integer DEFAULT NULL::integer, IN p_last_updated_by_name character varying DEFAULT NULL::character varying, IN p_is_clinical boolean DEFAULT NULL::boolean, IN p_is_toxicology boolean DEFAULT NULL::boolean, IN p_is_spiritual boolean DEFAULT NULL::boolean)
    LANGUAGE plpgsql
    AS $$
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
        $$;


ALTER PROCEDURE public.update_patient(IN p_patient_id integer, IN p_first_name character varying, IN p_last_name character varying, IN p_birth_date date, IN p_gender character varying, IN p_national_id character varying, IN p_contact_phone character varying, IN p_assurance character varying, IN p_residence text, IN p_father_name character varying, IN p_mother_name character varying, IN p_last_updated_by integer, IN p_last_updated_by_name character varying, IN p_is_clinical boolean, IN p_is_toxicology boolean, IN p_is_spiritual boolean) OWNER TO postgres;

--
-- Name: update_pharmacy_updated_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_pharmacy_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_pharmacy_updated_at() OWNER TO postgres;

--
-- Name: update_prescribed_names(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_prescribed_names() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
          IF NEW.prescribed_by IS NOT NULL THEN
            SELECT username INTO NEW.prescribed_by_name
              FROM users WHERE user_id = NEW.prescribed_by;
          END IF;
          RETURN NEW;
        END;
        $$;


ALTER FUNCTION public.update_prescribed_names() OWNER TO postgres;

--
-- Name: update_prescription(integer, integer, character varying, character varying, character varying, character varying, integer, date, date, text); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.update_prescription(IN p_prescription_id integer, IN p_patient_id integer, IN p_medication character varying, IN p_dosage character varying, IN p_frequency character varying, IN p_duration character varying, IN p_medical_record_id integer DEFAULT NULL::integer, IN p_start_date date DEFAULT CURRENT_DATE, IN p_end_date date DEFAULT NULL::date, IN p_notes text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Vérifier que la prescription existe
    IF NOT EXISTS (
        SELECT 1 FROM prescriptions WHERE prescription_id = p_prescription_id
    ) THEN
        RAISE EXCEPTION 'Aucune prescription avec l''ID % n''existe.', p_prescription_id;
    END IF;
    
    -- Vérifier l'existence du patient
    IF NOT EXISTS (
        SELECT 1 FROM patients WHERE patient_id = p_patient_id
    ) THEN
        RAISE EXCEPTION 'Aucun patient avec l''ID % n''existe.', p_patient_id;
    END IF;

    -- Vérifier l'existence du dossier médical (si fourni)
    IF p_medical_record_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM medical_records WHERE record_id = p_medical_record_id
        ) THEN
            RAISE EXCEPTION 'Aucun dossier médical avec l''ID % n''existe.', p_medical_record_id;
        END IF;
    END IF;

    -- Vérification de la cohérence des dates
    IF p_end_date IS NOT NULL AND p_end_date < p_start_date THEN
        RAISE EXCEPTION 'La date de fin (%) ne peut pas être antérieure à la date de début (%)',
            p_end_date, p_start_date;
    END IF;

    -- Mise à jour de la prescription
    UPDATE prescriptions
    SET patient_id = p_patient_id,
        medical_record_id = p_medical_record_id,
        medication = p_medication,
        dosage = p_dosage,
        frequency = p_frequency,
        duration = p_duration,
        start_date = p_start_date,
        end_date = p_end_date,
        notes = p_notes
    WHERE prescription_id = p_prescription_id;

    -- Enregistrement dans l'audit
    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'UPDATE PRESCRIPTION', p_patient_id);
END;
$$;


ALTER PROCEDURE public.update_prescription(IN p_prescription_id integer, IN p_patient_id integer, IN p_medication character varying, IN p_dosage character varying, IN p_frequency character varying, IN p_duration character varying, IN p_medical_record_id integer, IN p_start_date date, IN p_end_date date, IN p_notes text) OWNER TO postgres;

--
-- Name: update_prescription(integer, integer, character varying, character varying, character varying, character varying, integer, date, date, text, integer, character varying); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.update_prescription(IN p_prescription_id integer, IN p_patient_id integer, IN p_medication character varying, IN p_dosage character varying, IN p_frequency character varying, IN p_duration character varying, IN p_medical_record_id integer DEFAULT NULL::integer, IN p_start_date date DEFAULT CURRENT_DATE, IN p_end_date date DEFAULT NULL::date, IN p_notes text DEFAULT NULL::text, IN p_prescribed_by integer DEFAULT NULL::integer, IN p_prescribed_by_name character varying DEFAULT NULL::character varying)
    LANGUAGE plpgsql
    AS $$
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
        $$;


ALTER PROCEDURE public.update_prescription(IN p_prescription_id integer, IN p_patient_id integer, IN p_medication character varying, IN p_dosage character varying, IN p_frequency character varying, IN p_duration character varying, IN p_medical_record_id integer, IN p_start_date date, IN p_end_date date, IN p_notes text, IN p_prescribed_by integer, IN p_prescribed_by_name character varying) OWNER TO postgres;

--
-- Name: update_user(integer, character varying, text, character varying, character varying, integer, integer, boolean); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.update_user(IN p_user_id integer, IN p_username character varying DEFAULT NULL::character varying, IN p_password_hash text DEFAULT NULL::text, IN p_full_name character varying DEFAULT NULL::character varying, IN p_postgres_role character varying DEFAULT NULL::character varying, IN p_specialty_id integer DEFAULT NULL::integer, IN p_role_id integer DEFAULT NULL::integer, IN p_is_active boolean DEFAULT NULL::boolean)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_current_user_id INT;
    v_current_user_role TEXT;
BEGIN
    -- Récupérer l'ID et le rôle de l'utilisateur courant
    v_current_user_id := current_user_id();  -- Supposée fonction existante
    SELECT ar.role_name INTO v_current_user_role
    FROM users u
    JOIN application_roles ar ON ar.role_id = u.role_id
    WHERE u.user_id = v_current_user_id;

    -- Cas 1 : Admin → peut tout faire
    IF v_current_user_role = 'admin' THEN
        UPDATE users SET
            username = COALESCE(p_username, username),
            password_hash = COALESCE(p_password_hash, password_hash),
            full_name = COALESCE(p_full_name, full_name),
            postgres_role = COALESCE(p_postgres_role, postgres_role),
            specialty_id = COALESCE(p_specialty_id, specialty_id),
            role_id = COALESCE(p_role_id, role_id),
            is_active = COALESCE(p_is_active, is_active)
        WHERE user_id = p_user_id;

    -- Cas 2 : Utilisateur standard → ne peut modifier que son propre compte, et certains champs seulement
    ELSIF v_current_user_id = p_user_id THEN
        UPDATE users SET
            username = COALESCE(p_username, username),
            password_hash = COALESCE(p_password_hash, password_hash),
            full_name = COALESCE(p_full_name, full_name),
            specialty_id = COALESCE(p_specialty_id, specialty_id)
        WHERE user_id = p_user_id;

    -- Cas 3 : Interdiction
    ELSE
        RAISE EXCEPTION 'Vous n''avez pas les droits pour modifier ce compte.';
    END IF;

    -- (Optionnel) Historique d'action
    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'UPDATE USER', p_user_id);
END;
$$;


ALTER PROCEDURE public.update_user(IN p_user_id integer, IN p_username character varying, IN p_password_hash text, IN p_full_name character varying, IN p_postgres_role character varying, IN p_specialty_id integer, IN p_role_id integer, IN p_is_active boolean) OWNER TO postgres;

--
-- Name: update_user_names_cs(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_user_names_cs() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Lors d'un INSERT, si created_by est renseigné, on remplit created_by_name
    IF TG_OP = 'INSERT' THEN
        IF NEW.created_by IS NOT NULL THEN
            NEW.created_by_name := (
                SELECT full_name
                FROM public.users
                WHERE user_id = NEW.created_by
            );
        END IF;
    END IF;

    -- Il n'existe pas de colonne last_updated_by dans consultation_spirituel, donc on ne la gère pas ici.

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_user_names_cs() OWNER TO postgres;

--
-- Name: update_user_names_lab_results(integer); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.update_user_names_lab_results(IN p_lab_result_id integer)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Prescribed by -> prescribed_by_name
    UPDATE public.lab_results lr
    SET prescribed_by_name = sub.full_name
    FROM (
        SELECT user_id, COALESCE(full_name, concat_ws(' ', first_name, last_name)) AS full_name
        FROM public.users
    ) sub
    WHERE lr.prescribed_by = sub.user_id
      AND lr.lab_result_id = p_lab_result_id;

    -- Technician -> technician_name
    UPDATE public.lab_results lr
    SET technician_name = sub.full_name
    FROM (
        SELECT user_id, COALESCE(full_name, concat_ws(' ', first_name, last_name)) AS full_name
        FROM public.users
    ) sub
    WHERE lr.technician_id = sub.user_id
      AND lr.lab_result_id = p_lab_result_id;

    -- Ajouter d'autres colonnes (ex: filled_by) ici si nécessaire
END;
$$;


ALTER PROCEDURE public.update_user_names_lab_results(IN p_lab_result_id integer) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admin; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.admin (
    user_id integer NOT NULL,
    access_level smallint,
    last_login timestamp with time zone,
    permissions text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT admin_access_level_check CHECK (((access_level >= 1) AND (access_level <= 10)))
);


ALTER TABLE public.admin OWNER TO postgres;

--
-- Name: admissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.admissions (
    admission_id integer NOT NULL,
    patient_id integer NOT NULL,
    admission_date timestamp with time zone DEFAULT now(),
    discharge_date timestamp with time zone,
    status character varying(20) DEFAULT 'ACTIVE'::character varying,
    current_phase integer DEFAULT 1,
    notes_admission text,
    created_by integer,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    CONSTRAINT admissions_current_phase_check CHECK (((current_phase >= 1) AND (current_phase <= 4)))
);


ALTER TABLE public.admissions OWNER TO postgres;

--
-- Name: admissions_admission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.admissions_admission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admissions_admission_id_seq OWNER TO postgres;

--
-- Name: admissions_admission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.admissions_admission_id_seq OWNED BY public.admissions.admission_id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: application_roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.application_roles (
    role_id integer NOT NULL,
    role_name character varying(50) NOT NULL
);


ALTER TABLE public.application_roles OWNER TO postgres;

--
-- Name: application_roles_role_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.application_roles_role_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.application_roles_role_id_seq OWNER TO postgres;

--
-- Name: application_roles_role_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.application_roles_role_id_seq OWNED BY public.application_roles.role_id;


--
-- Name: appointments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.appointments (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    doctor_id integer NOT NULL,
    specialty character varying(100),
    appointment_date date NOT NULL,
    appointment_time time without time zone NOT NULL,
    reason text,
    status character varying(20) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL
);


ALTER TABLE public.appointments OWNER TO postgres;

--
-- Name: appointments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.appointments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.appointments_id_seq OWNER TO postgres;

--
-- Name: appointments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.appointments_id_seq OWNED BY public.appointments.id;


--
-- Name: audit_access; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_access (
    access_id integer NOT NULL,
    user_id integer,
    "timestamp" timestamp with time zone DEFAULT now(),
    action_type character varying(50) NOT NULL,
    ip_address character varying(45),
    user_agent text,
    details text
);


ALTER TABLE public.audit_access OWNER TO postgres;

--
-- Name: audit_access_access_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_access_access_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_access_access_id_seq OWNER TO postgres;

--
-- Name: audit_access_access_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_access_access_id_seq OWNED BY public.audit_access.access_id;


--
-- Name: audit_access_old; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_access_old (
    log_id integer NOT NULL,
    user_role character varying(50) NOT NULL,
    patient_id integer,
    action_time timestamp without time zone DEFAULT now()
);


ALTER TABLE public.audit_access_old OWNER TO postgres;

--
-- Name: audit_access_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_access_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_access_log_id_seq OWNER TO postgres;

--
-- Name: audit_access_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_access_log_id_seq OWNED BY public.audit_access_old.log_id;


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_logs (
    log_id integer NOT NULL,
    user_role character varying(50) NOT NULL,
    action text NOT NULL,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.audit_logs OWNER TO postgres;

--
-- Name: audit_logs_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_logs_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_logs_log_id_seq OWNER TO postgres;

--
-- Name: audit_logs_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_logs_log_id_seq OWNED BY public.audit_logs.log_id;


--
-- Name: audit_user_actions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_user_actions (
    action_id integer NOT NULL,
    user_id integer NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now(),
    resource_type character varying(50) NOT NULL,
    resource_id integer,
    action_performed character varying(50) NOT NULL,
    old_values jsonb,
    new_values jsonb,
    ip_address character varying(45),
    username character varying(100)
);


ALTER TABLE public.audit_user_actions OWNER TO postgres;

--
-- Name: audit_user_actions_old; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_user_actions_old (
    action_id integer NOT NULL,
    user_name character varying(100) NOT NULL,
    action text NOT NULL,
    patient_id integer,
    action_time timestamp without time zone DEFAULT now()
);


ALTER TABLE public.audit_user_actions_old OWNER TO postgres;

--
-- Name: audit_user_actions_action_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_user_actions_action_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_user_actions_action_id_seq OWNER TO postgres;

--
-- Name: audit_user_actions_action_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_user_actions_action_id_seq OWNED BY public.audit_user_actions_old.action_id;


--
-- Name: audit_user_actions_action_id_seq1; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_user_actions_action_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_user_actions_action_id_seq1 OWNER TO postgres;

--
-- Name: audit_user_actions_action_id_seq1; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_user_actions_action_id_seq1 OWNED BY public.audit_user_actions.action_id;


--
-- Name: caisse; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.caisse (
    transaction_id integer NOT NULL,
    patient_id integer,
    amount numeric(10,2) NOT NULL,
    paid_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by_name character varying(100) NOT NULL,
    handled_by integer NOT NULL,
    payment_method character varying(50) NOT NULL,
    transaction_type character varying(50) NOT NULL,
    note text,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    advance_amount numeric(10,2) DEFAULT 0 NOT NULL,
    patient_label character varying(100),
    cancelled_by integer,
    cancelled_at timestamp without time zone,
    cancel_justification text,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    upload_error text,
    CONSTRAINT ck_caisse_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'cancelled'::character varying, 'refunded'::character varying, 'pending_approval'::character varying])::text[])))
);


ALTER TABLE public.caisse OWNER TO postgres;

--
-- Name: caisse_item; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.caisse_item (
    item_id integer NOT NULL,
    transaction_id integer NOT NULL,
    item_type character varying(50) NOT NULL,
    item_ref_id integer NOT NULL,
    unit_price numeric(10,2) NOT NULL,
    quantity integer NOT NULL,
    line_total numeric(10,2) NOT NULL,
    note text,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL
);


ALTER TABLE public.caisse_item OWNER TO postgres;

--
-- Name: caisse_item_item_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.caisse_item_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.caisse_item_item_id_seq OWNER TO postgres;

--
-- Name: caisse_item_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.caisse_item_item_id_seq OWNED BY public.caisse_item.item_id;


--
-- Name: caisse_retrait; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.caisse_retrait (
    retrait_id integer NOT NULL,
    amount numeric(10,2) NOT NULL,
    justification text,
    retrait_at timestamp without time zone DEFAULT now() NOT NULL,
    handled_by integer NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    cancelled_by integer,
    cancelled_at timestamp without time zone,
    cancel_justification text,
    category character varying(50) DEFAULT NULL::character varying,
    payment_method character varying(50) DEFAULT NULL::character varying,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL
);


ALTER TABLE public.caisse_retrait OWNER TO postgres;

--
-- Name: caisse_retrait_retrait_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.caisse_retrait_retrait_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.caisse_retrait_retrait_id_seq OWNER TO postgres;

--
-- Name: caisse_retrait_retrait_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.caisse_retrait_retrait_id_seq OWNED BY public.caisse_retrait.retrait_id;


--
-- Name: caisse_transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.caisse_transaction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.caisse_transaction_id_seq OWNER TO postgres;

--
-- Name: caisse_transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.caisse_transaction_id_seq OWNED BY public.caisse.transaction_id;


--
-- Name: consultation_spirituel; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.consultation_spirituel (
    consultation_id integer NOT NULL,
    patient_id integer,
    consultation_date timestamp without time zone DEFAULT now(),
    created_by integer,
    created_by_name character varying(100),
    notes text,
    type_consultation character varying(30) NOT NULL,
    presc_generic text[],
    presc_med_spirituel text[],
    mp_type character varying(200),
    fr_registered_at timestamp without time zone,
    fr_appointment_at timestamp without time zone,
    fr_amount_paid numeric(10,2),
    fr_observation text,
    psaume text,
    CONSTRAINT ck_fr_only_for_family CHECK (((((type_consultation)::text = 'FamilyRestoration'::text) AND (fr_registered_at IS NOT NULL) AND (fr_appointment_at IS NOT NULL) AND (fr_amount_paid IS NOT NULL)) OR (((type_consultation)::text = 'Spiritual'::text) AND (fr_registered_at IS NULL) AND (fr_appointment_at IS NULL) AND (fr_amount_paid IS NULL) AND (fr_observation IS NULL)))),
    CONSTRAINT ck_presc_generic CHECK (((presc_generic IS NULL) OR (presc_generic <@ ARRAY['Hony'::text, 'Massage'::text, 'Prayer'::text]))),
    CONSTRAINT ck_presc_med_spirituel CHECK (((presc_med_spirituel IS NULL) OR (presc_med_spirituel <@ ARRAY['SE'::text, 'TIS'::text, 'AE'::text]))),
    CONSTRAINT ck_type_consultation CHECK (((type_consultation)::text = ANY (ARRAY[('Spiritual'::character varying)::text, ('FamilyRestoration'::character varying)::text])))
);


ALTER TABLE public.consultation_spirituel OWNER TO postgres;

--
-- Name: consultation_spirituel_consultation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.consultation_spirituel_consultation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.consultation_spirituel_consultation_id_seq OWNER TO postgres;

--
-- Name: consultation_spirituel_consultation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.consultation_spirituel_consultation_id_seq OWNED BY public.consultation_spirituel.consultation_id;


--
-- Name: discount_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.discount_requests (
    id integer NOT NULL,
    transaction_id integer NOT NULL,
    requested_by integer NOT NULL,
    requested_to integer NOT NULL,
    original_amount numeric(10,2) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    decision_percent integer,
    decision_echelonne_deadline date,
    decided_by integer,
    decided_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.discount_requests OWNER TO postgres;

--
-- Name: discount_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.discount_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.discount_requests_id_seq OWNER TO postgres;

--
-- Name: discount_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.discount_requests_id_seq OWNED BY public.discount_requests.id;


--
-- Name: doctor; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.doctor (
    user_id integer NOT NULL,
    license_number character varying(20),
    specialty_id integer,
    years_experience smallint,
    phone character varying(20),
    address character varying(200),
    birth_date date,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT doctor_years_experience_check CHECK ((years_experience >= 0))
);


ALTER TABLE public.doctor OWNER TO postgres;

--
-- Name: examens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.examens (
    id integer NOT NULL,
    code character varying(20) NOT NULL,
    nom text NOT NULL,
    categorie text NOT NULL,
    prix numeric(10,2)
);


ALTER TABLE public.examens OWNER TO postgres;

--
-- Name: examens_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.examens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.examens_id_seq OWNER TO postgres;

--
-- Name: examens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.examens_id_seq OWNED BY public.examens.id;


--
-- Name: lab_result_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lab_result_details (
    detail_id integer NOT NULL,
    result_id integer NOT NULL,
    parametre_id integer NOT NULL,
    valeur_text text NOT NULL,
    interpretation character varying(50),
    flagged boolean DEFAULT false,
    valeur_num numeric
);


ALTER TABLE public.lab_result_details OWNER TO postgres;

--
-- Name: lab_result_details_detail_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.lab_result_details_detail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.lab_result_details_detail_id_seq OWNER TO postgres;

--
-- Name: lab_result_details_detail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.lab_result_details_detail_id_seq OWNED BY public.lab_result_details.detail_id;


--
-- Name: lab_results; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lab_results (
    result_id integer NOT NULL,
    patient_id integer,
    test_type character varying(100) NOT NULL,
    test_date timestamp without time zone DEFAULT now(),
    prescribed_by integer,
    technician_id integer,
    technician_name character varying(100),
    status character varying(20) DEFAULT 'pending'::character varying,
    note text,
    examen_id integer,
    code_lab_patient character varying(20) NOT NULL,
    created_by integer,
    created_by_name text,
    last_updated_by integer,
    last_updated_by_name text,
    external_patient_info jsonb,
    origin_prescription_id integer,
    batch_id uuid,
    prescribed_by_name character varying(100),
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    batch_uuid character varying(36),
    CONSTRAINT chk_technician_role CHECK (public.check_technician_role(technician_id)),
    CONSTRAINT note_length_check CHECK ((length(note) <= 1000))
);


ALTER TABLE public.lab_results OWNER TO postgres;

--
-- Name: TABLE lab_results; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.lab_results IS 'Résultats de laboratoire liés aux dossiers médicaux';


--
-- Name: COLUMN lab_results.batch_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.lab_results.batch_id IS 'Identifiant unique de lot (UUID) pour grouper les examens créés simultanément';


--
-- Name: lab_results_audit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lab_results_audit (
    audit_id integer NOT NULL,
    result_id integer,
    operation character(1) NOT NULL,
    old_data jsonb,
    new_data jsonb,
    changed_by integer NOT NULL,
    changed_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.lab_results_audit OWNER TO postgres;

--
-- Name: lab_results_audit_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.lab_results_audit_audit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.lab_results_audit_audit_id_seq OWNER TO postgres;

--
-- Name: lab_results_audit_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.lab_results_audit_audit_id_seq OWNED BY public.lab_results_audit.audit_id;


--
-- Name: lab_results_result_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.lab_results_result_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.lab_results_result_id_seq OWNER TO postgres;

--
-- Name: lab_results_result_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.lab_results_result_id_seq OWNED BY public.lab_results.result_id;


--
-- Name: laborantin; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.laborantin (
    user_id integer NOT NULL,
    lab_section character varying(100) DEFAULT 'général'::character varying NOT NULL,
    certification_date date DEFAULT CURRENT_DATE,
    equipment_access text DEFAULT ''::text,
    hire_date date DEFAULT CURRENT_DATE
);


ALTER TABLE public.laborantin OWNER TO postgres;

--
-- Name: medical_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.medical_records (
    record_id integer NOT NULL,
    patient_id integer NOT NULL,
    consultation_date timestamp without time zone DEFAULT now(),
    marital_status character varying(20),
    bp character varying(10),
    temperature numeric(4,1),
    weight numeric(5,2),
    height numeric(5,2),
    medical_history text,
    allergies text,
    symptoms text,
    diagnosis text,
    treatment text,
    severity character varying(20),
    notes text,
    motif_code character varying(20) NOT NULL,
    created_by integer,
    created_by_name character varying(100),
    last_updated_by integer,
    last_updated_by_name character varying(100),
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    appointment_id integer,
    CONSTRAINT medical_records_motif_code_check CHECK (((motif_code)::text = ANY (ARRAY[('consultation'::character varying)::text, ('appointment'::character varying)::text, ('prenatal'::character varying)::text, ('hospitalization'::character varying)::text, ('emergency'::character varying)::text, ('free'::character varying)::text]))),
    CONSTRAINT medical_records_severity_check CHECK (((severity)::text = ANY (ARRAY[('low'::character varying)::text, ('medium'::character varying)::text, ('high'::character varying)::text])))
);


ALTER TABLE public.medical_records OWNER TO postgres;

--
-- Name: medical_records_record_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.medical_records_record_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.medical_records_record_id_seq OWNER TO postgres;

--
-- Name: medical_records_record_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.medical_records_record_id_seq OWNED BY public.medical_records.record_id;


--
-- Name: medical_specialties; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.medical_specialties (
    specialty_id integer NOT NULL,
    name character varying(100) NOT NULL
);


ALTER TABLE public.medical_specialties OWNER TO postgres;

--
-- Name: medical_specialties_specialty_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.medical_specialties_specialty_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.medical_specialties_specialty_id_seq OWNER TO postgres;

--
-- Name: medical_specialties_specialty_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.medical_specialties_specialty_id_seq OWNED BY public.medical_specialties.specialty_id;


--
-- Name: motif_translations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.motif_translations (
    code character varying(20) NOT NULL,
    label_fr character varying(50) NOT NULL,
    label_en character varying(50) NOT NULL
);


ALTER TABLE public.motif_translations OWNER TO postgres;

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    recipient_user_id integer NOT NULL,
    type character varying(50) NOT NULL,
    payload jsonb,
    status character varying(20) DEFAULT 'unread'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    read_at timestamp without time zone
);


ALTER TABLE public.notifications OWNER TO postgres;

--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notifications_id_seq OWNER TO postgres;

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: nurse; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.nurse (
    user_id integer NOT NULL,
    registration_number character varying(20),
    department character varying(100),
    shift character varying(50),
    phone character varying(20),
    hire_date date,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.nurse OWNER TO postgres;

--
-- Name: organization_config; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.organization_config (
    id integer NOT NULL,
    name character varying(255) DEFAULT 'AH2 CLINIC'::character varying NOT NULL,
    slogan character varying(255),
    logo_url character varying(255),
    address character varying(255),
    city character varying(100),
    po_box character varying(50),
    phone character varying(50),
    phone2 character varying(50),
    email character varying(100),
    website character varying(255),
    niu character varying(100),
    rccm character varying(100),
    legal_info text,
    ticket_logo_url character varying,
    ticket_print_token character varying
);


ALTER TABLE public.organization_config OWNER TO postgres;

--
-- Name: organization_config_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.organization_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.organization_config_id_seq OWNER TO postgres;

--
-- Name: organization_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.organization_config_id_seq OWNED BY public.organization_config.id;


--
-- Name: paiement_echelonne; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paiement_echelonne (
    payment_id integer NOT NULL,
    transaction_id integer NOT NULL,
    paid_amount numeric(10,2) NOT NULL,
    payment_date timestamp without time zone DEFAULT now() NOT NULL,
    payment_method character varying(50) NOT NULL,
    payment_type character varying(50) NOT NULL,
    handled_by integer NOT NULL,
    note text,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL
);


ALTER TABLE public.paiement_echelonne OWNER TO postgres;

--
-- Name: paiement_echelonne_payment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.paiement_echelonne_payment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.paiement_echelonne_payment_id_seq OWNER TO postgres;

--
-- Name: paiement_echelonne_payment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.paiement_echelonne_payment_id_seq OWNED BY public.paiement_echelonne.payment_id;


--
-- Name: parametres; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.parametres (
    id integer NOT NULL,
    examen_id integer NOT NULL,
    nom_parametre text NOT NULL,
    unite text NOT NULL,
    type_valeur text NOT NULL,
    input_type character varying(20) DEFAULT 'numeric'::character varying,
    options_list text
);


ALTER TABLE public.parametres OWNER TO postgres;

--
-- Name: parametres_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.parametres_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.parametres_id_seq OWNER TO postgres;

--
-- Name: parametres_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.parametres_id_seq OWNED BY public.parametres.id;


--
-- Name: patient_contacts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.patient_contacts (
    contact_id integer NOT NULL,
    patient_id integer NOT NULL,
    full_name character varying(150) NOT NULL,
    relationship character varying(50),
    phone_number character varying(50) NOT NULL,
    is_primary boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.patient_contacts OWNER TO postgres;

--
-- Name: patient_contacts_contact_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.patient_contacts_contact_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patient_contacts_contact_id_seq OWNER TO postgres;

--
-- Name: patient_contacts_contact_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.patient_contacts_contact_id_seq OWNED BY public.patient_contacts.contact_id;


--
-- Name: patients; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.patients (
    patient_id integer NOT NULL,
    first_name character varying(50) NOT NULL,
    last_name character varying(50) NOT NULL,
    birth_date date NOT NULL,
    gender character varying(10),
    national_id character varying(20),
    contact_phone character varying(20),
    assurance character varying(20),
    created_at timestamp without time zone DEFAULT now(),
    created_by integer,
    created_by_name character varying(100),
    last_updated_by integer,
    last_updated_by_name character varying(100),
    residence text,
    code_patient character varying(20),
    father_name character varying(100),
    mother_name character varying(100),
    last_updated_at timestamp without time zone DEFAULT now(),
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    is_toxicology boolean DEFAULT false,
    is_clinical boolean DEFAULT false,
    is_spiritual boolean DEFAULT false,
    is_deleted boolean DEFAULT false,
    deleted_at timestamp without time zone,
    deleted_by integer
);


ALTER TABLE public.patients OWNER TO postgres;

--
-- Name: patients_patient_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.patients_patient_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patients_patient_id_seq OWNER TO postgres;

--
-- Name: patients_patient_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.patients_patient_id_seq OWNED BY public.patients.patient_id;


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.permissions (
    permission_id integer NOT NULL,
    permission_name character varying(100) NOT NULL,
    procedure_name character varying(100) NOT NULL,
    description_procedure character varying(100)
);


ALTER TABLE public.permissions OWNER TO postgres;

--
-- Name: permissions_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.permissions_permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.permissions_permission_id_seq OWNER TO postgres;

--
-- Name: permissions_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.permissions_permission_id_seq OWNED BY public.permissions.permission_id;


--
-- Name: pharmacy; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pharmacy (
    medication_id integer NOT NULL,
    patient_id integer,
    drug_name character varying(100) NOT NULL,
    quantity integer DEFAULT 0 NOT NULL,
    threshold integer DEFAULT 0 NOT NULL,
    medication_type character varying(20) NOT NULL,
    dosage_mg numeric(10,2),
    expiry_date timestamp without time zone,
    stock_status character varying(20) DEFAULT 'normal'::character varying NOT NULL,
    prescribed_by integer,
    name_dr character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    forme character varying(50) DEFAULT 'Autre'::character varying NOT NULL,
    price numeric(10,2) DEFAULT 0.00 NOT NULL
);


ALTER TABLE public.pharmacy OWNER TO postgres;

--
-- Name: pharmacy_medication_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pharmacy_medication_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pharmacy_medication_id_seq OWNER TO postgres;

--
-- Name: pharmacy_medication_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.pharmacy_medication_id_seq OWNED BY public.pharmacy.medication_id;


--
-- Name: prayer_book_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.prayer_book_type (
    type_code character varying(10) NOT NULL,
    label character varying(100) NOT NULL
);


ALTER TABLE public.prayer_book_type OWNER TO postgres;

--
-- Name: prescriptions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.prescriptions (
    prescription_id integer NOT NULL,
    patient_id integer NOT NULL,
    medical_record_id integer,
    medication character varying(100) NOT NULL,
    dosage character varying(50) NOT NULL,
    frequency character varying(50) NOT NULL,
    duration character varying(50) NOT NULL,
    start_date date DEFAULT CURRENT_DATE,
    end_date date,
    status character varying(20) DEFAULT 'active'::character varying,
    prescribed_by integer,
    prescribed_by_name character varying(100),
    notes text,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    is_lab_order boolean DEFAULT false,
    lab_exams_list jsonb DEFAULT '[]'::jsonb,
    CONSTRAINT prescriptions_status_check CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('completed'::character varying)::text, ('cancelled'::character varying)::text])))
);


ALTER TABLE public.prescriptions OWNER TO postgres;

--
-- Name: TABLE prescriptions; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.prescriptions IS 'Prescriptions médicales liées aux dossiers médicaux';


--
-- Name: prescriptions_prescription_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.prescriptions_prescription_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.prescriptions_prescription_id_seq OWNER TO postgres;

--
-- Name: prescriptions_prescription_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.prescriptions_prescription_id_seq OWNED BY public.prescriptions.prescription_id;


--
-- Name: psych_evaluations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.psych_evaluations (
    eval_id integer NOT NULL,
    admission_id integer NOT NULL,
    doctor_id integer,
    eval_date timestamp with time zone DEFAULT now(),
    mood_score integer,
    observations text NOT NULL,
    recommendations text,
    phase_at_time integer,
    CONSTRAINT psych_evaluations_mood_score_check CHECK (((mood_score >= 1) AND (mood_score <= 10)))
);


ALTER TABLE public.psych_evaluations OWNER TO postgres;

--
-- Name: psych_evaluations_eval_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.psych_evaluations_eval_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.psych_evaluations_eval_id_seq OWNER TO postgres;

--
-- Name: psych_evaluations_eval_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.psych_evaluations_eval_id_seq OWNED BY public.psych_evaluations.eval_id;


--
-- Name: reference_ranges; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reference_ranges (
    id integer NOT NULL,
    parametre_id integer NOT NULL,
    sexe character(1) NOT NULL,
    age_min integer NOT NULL,
    age_max integer NOT NULL,
    valeur_min numeric NOT NULL,
    valeur_max numeric NOT NULL,
    CONSTRAINT reference_ranges_sexe_check CHECK ((sexe = ANY (ARRAY['M'::bpchar, 'F'::bpchar, 'X'::bpchar])))
);


ALTER TABLE public.reference_ranges OWNER TO postgres;

--
-- Name: reference_ranges_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.reference_ranges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reference_ranges_id_seq OWNER TO postgres;

--
-- Name: reference_ranges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.reference_ranges_id_seq OWNED BY public.reference_ranges.id;


--
-- Name: role_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.role_permissions (
    role_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.role_permissions OWNER TO postgres;

--
-- Name: secretaire; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.secretaire (
    user_id integer NOT NULL,
    office_number character varying(10),
    phone_ext character varying(10),
    fax_number character varying(20),
    hire_date date DEFAULT CURRENT_DATE
);


ALTER TABLE public.secretaire OWNER TO postgres;

--
-- Name: spiritual_attendance; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.spiritual_attendance (
    session_id integer NOT NULL,
    admission_id integer NOT NULL,
    status character varying(20) DEFAULT 'PRESENT'::character varying,
    notes text
);


ALTER TABLE public.spiritual_attendance OWNER TO postgres;

--
-- Name: spiritual_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.spiritual_sessions (
    session_id integer NOT NULL,
    session_date date NOT NULL,
    conductor_name character varying(100),
    topic character varying(200),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.spiritual_sessions OWNER TO postgres;

--
-- Name: spiritual_sessions_session_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.spiritual_sessions_session_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.spiritual_sessions_session_id_seq OWNER TO postgres;

--
-- Name: spiritual_sessions_session_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.spiritual_sessions_session_id_seq OWNED BY public.spiritual_sessions.session_id;


--
-- Name: stock_movement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stock_movement (
    movement_id integer NOT NULL,
    medication_id integer NOT NULL,
    change_qty integer NOT NULL,
    movement_type character varying(50) NOT NULL,
    note text,
    created_by character varying(100) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.stock_movement OWNER TO postgres;

--
-- Name: stock_movement_movement_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stock_movement_movement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stock_movement_movement_id_seq OWNER TO postgres;

--
-- Name: stock_movement_movement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stock_movement_movement_id_seq OWNED BY public.stock_movement.movement_id;


--
-- Name: toxico_dossiers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.toxico_dossiers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.toxico_dossiers_id_seq OWNER TO postgres;

--
-- Name: toxico_dossiers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.toxico_dossiers (
    id integer DEFAULT nextval('public.toxico_dossiers_id_seq'::regclass) NOT NULL,
    patient_id integer NOT NULL,
    psychologist_id integer,
    admission_date date DEFAULT CURRENT_DATE NOT NULL,
    substance character varying(100) NOT NULL,
    current_phase integer DEFAULT 1 NOT NULL,
    relapse_count integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    guardian_name character varying(150),
    guardian_contact character varying(50),
    consent_file character varying(255),
    notes_admission text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.toxico_dossiers OWNER TO postgres;

--
-- Name: toxico_evaluations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.toxico_evaluations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.toxico_evaluations_id_seq OWNER TO postgres;

--
-- Name: toxico_evaluations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.toxico_evaluations (
    id integer DEFAULT nextval('public.toxico_evaluations_id_seq'::regclass) NOT NULL,
    dossier_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    created_by integer,
    decision character varying(50) NOT NULL,
    observation text NOT NULL,
    recommendation text,
    phase_before integer NOT NULL,
    phase_after integer NOT NULL,
    is_relapse boolean DEFAULT false
);


ALTER TABLE public.toxico_evaluations OWNER TO postgres;

--
-- Name: toxico_phase_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.toxico_phase_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.toxico_phase_history_id_seq OWNER TO postgres;

--
-- Name: toxico_phase_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.toxico_phase_history (
    id integer DEFAULT nextval('public.toxico_phase_history_id_seq'::regclass) NOT NULL,
    dossier_id integer NOT NULL,
    phase integer NOT NULL,
    start_date date NOT NULL,
    end_date date,
    status character varying(50) DEFAULT 'En cours'::character varying NOT NULL,
    comments text
);


ALTER TABLE public.toxico_phase_history OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(50) NOT NULL,
    password_hash text NOT NULL,
    full_name character varying(100) NOT NULL,
    postgres_role character varying(20),
    is_active boolean DEFAULT true,
    specialty_id integer,
    role_id integer,
    email character varying(150),
    contact character varying(50),
    token_version integer DEFAULT 0 NOT NULL,
    CONSTRAINT chk_specialty CHECK ((((postgres_role)::text = 'app_medical'::text) OR (((postgres_role)::text <> 'app_medical'::text) AND (specialty_id IS NULL)))),
    CONSTRAINT users_postgres_role_check CHECK (((postgres_role)::text = ANY (ARRAY['app_secretaire'::text, 'app_medical'::text, 'app_laborantin'::text, 'app_admin'::text, 'app_toxico_web'::text])))
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: user_specialties; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.user_specialties AS
 SELECT u.user_id,
    u.full_name,
    u.postgres_role,
    COALESCE(ms.name, 'Généraliste'::character varying) AS specialty_name,
    COALESCE(ms.specialty_id, ( SELECT medical_specialties.specialty_id
           FROM public.medical_specialties
          WHERE ((medical_specialties.name)::text = 'Généraliste'::text))) AS effective_specialty_id
   FROM (public.users u
     LEFT JOIN public.medical_specialties ms ON ((u.specialty_id = ms.specialty_id)))
  WHERE ((u.postgres_role)::text = 'app_medical'::text);


ALTER VIEW public.user_specialties OWNER TO postgres;

--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_user_id_seq OWNER TO postgres;

--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: view_patient_summary; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.view_patient_summary AS
 SELECT p.patient_id,
    p.code_patient,
    mr.consultation_date AS last_consultation,
    mr.diagnosis AS last_diagnosis,
    mr.bp AS last_bp,
    mr.weight AS last_weight,
    mr.allergies
   FROM (public.patients p
     LEFT JOIN LATERAL ( SELECT medical_records.consultation_date,
            medical_records.diagnosis,
            medical_records.bp,
            medical_records.weight,
            medical_records.allergies
           FROM public.medical_records
          WHERE (medical_records.patient_id = p.patient_id)
          ORDER BY medical_records.consultation_date DESC
         LIMIT 1) mr ON (true));


ALTER VIEW public.view_patient_summary OWNER TO postgres;

--
-- Name: vue_appointment; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vue_appointment AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'appointment'::text);


ALTER VIEW public.vue_appointment OWNER TO postgres;

--
-- Name: vue_autre; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vue_autre AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text <> ALL (ARRAY[('consultation'::character varying)::text, ('appointment'::character varying)::text, ('prenatal'::character varying)::text, ('hospitalization'::character varying)::text, ('emergency'::character varying)::text, ('free'::character varying)::text]));


ALTER VIEW public.vue_autre OWNER TO postgres;

--
-- Name: vue_consultation; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vue_consultation AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'consultation'::text);


ALTER VIEW public.vue_consultation OWNER TO postgres;

--
-- Name: vue_emergency; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vue_emergency AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'emergency'::text);


ALTER VIEW public.vue_emergency OWNER TO postgres;

--
-- Name: vue_free; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vue_free AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'free'::text);


ALTER VIEW public.vue_free OWNER TO postgres;

--
-- Name: vue_hospitalization; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vue_hospitalization AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'hospitalization'::text);


ALTER VIEW public.vue_hospitalization OWNER TO postgres;

--
-- Name: vue_new_motif; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vue_new_motif AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'new_motif'::text);


ALTER VIEW public.vue_new_motif OWNER TO postgres;

--
-- Name: vue_prenatal; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vue_prenatal AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'prenatal'::text);


ALTER VIEW public.vue_prenatal OWNER TO postgres;

--
-- Name: admissions admission_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admissions ALTER COLUMN admission_id SET DEFAULT nextval('public.admissions_admission_id_seq'::regclass);


--
-- Name: application_roles role_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.application_roles ALTER COLUMN role_id SET DEFAULT nextval('public.application_roles_role_id_seq'::regclass);


--
-- Name: appointments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointments ALTER COLUMN id SET DEFAULT nextval('public.appointments_id_seq'::regclass);


--
-- Name: audit_access access_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_access ALTER COLUMN access_id SET DEFAULT nextval('public.audit_access_access_id_seq'::regclass);


--
-- Name: audit_access_old log_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_access_old ALTER COLUMN log_id SET DEFAULT nextval('public.audit_access_log_id_seq'::regclass);


--
-- Name: audit_logs log_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN log_id SET DEFAULT nextval('public.audit_logs_log_id_seq'::regclass);


--
-- Name: audit_user_actions action_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_user_actions ALTER COLUMN action_id SET DEFAULT nextval('public.audit_user_actions_action_id_seq1'::regclass);


--
-- Name: audit_user_actions_old action_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_user_actions_old ALTER COLUMN action_id SET DEFAULT nextval('public.audit_user_actions_action_id_seq'::regclass);


--
-- Name: caisse transaction_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.caisse ALTER COLUMN transaction_id SET DEFAULT nextval('public.caisse_transaction_id_seq'::regclass);


--
-- Name: caisse_item item_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.caisse_item ALTER COLUMN item_id SET DEFAULT nextval('public.caisse_item_item_id_seq'::regclass);


--
-- Name: caisse_retrait retrait_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.caisse_retrait ALTER COLUMN retrait_id SET DEFAULT nextval('public.caisse_retrait_retrait_id_seq'::regclass);


--
-- Name: consultation_spirituel consultation_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.consultation_spirituel ALTER COLUMN consultation_id SET DEFAULT nextval('public.consultation_spirituel_consultation_id_seq'::regclass);


--
-- Name: discount_requests id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discount_requests ALTER COLUMN id SET DEFAULT nextval('public.discount_requests_id_seq'::regclass);


--
-- Name: examens id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.examens ALTER COLUMN id SET DEFAULT nextval('public.examens_id_seq'::regclass);


--
-- Name: lab_result_details detail_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_result_details ALTER COLUMN detail_id SET DEFAULT nextval('public.lab_result_details_detail_id_seq'::regclass);


--
-- Name: lab_results result_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_results ALTER COLUMN result_id SET DEFAULT nextval('public.lab_results_result_id_seq'::regclass);


--
-- Name: lab_results_audit audit_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_results_audit ALTER COLUMN audit_id SET DEFAULT nextval('public.lab_results_audit_audit_id_seq'::regclass);


--
-- Name: medical_records record_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medical_records ALTER COLUMN record_id SET DEFAULT nextval('public.medical_records_record_id_seq'::regclass);


--
-- Name: medical_specialties specialty_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medical_specialties ALTER COLUMN specialty_id SET DEFAULT nextval('public.medical_specialties_specialty_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: organization_config id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organization_config ALTER COLUMN id SET DEFAULT nextval('public.organization_config_id_seq'::regclass);


--
-- Name: paiement_echelonne payment_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paiement_echelonne ALTER COLUMN payment_id SET DEFAULT nextval('public.paiement_echelonne_payment_id_seq'::regclass);


--
-- Name: parametres id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.parametres ALTER COLUMN id SET DEFAULT nextval('public.parametres_id_seq'::regclass);


--
-- Name: patient_contacts contact_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patient_contacts ALTER COLUMN contact_id SET DEFAULT nextval('public.patient_contacts_contact_id_seq'::regclass);


--
-- Name: patients patient_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patients ALTER COLUMN patient_id SET DEFAULT nextval('public.patients_patient_id_seq'::regclass);


--
-- Name: permissions permission_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions ALTER COLUMN permission_id SET DEFAULT nextval('public.permissions_permission_id_seq'::regclass);


--
-- Name: pharmacy medication_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pharmacy ALTER COLUMN medication_id SET DEFAULT nextval('public.pharmacy_medication_id_seq'::regclass);


--
-- Name: prescriptions prescription_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prescriptions ALTER COLUMN prescription_id SET DEFAULT nextval('public.prescriptions_prescription_id_seq'::regclass);


--
-- Name: psych_evaluations eval_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.psych_evaluations ALTER COLUMN eval_id SET DEFAULT nextval('public.psych_evaluations_eval_id_seq'::regclass);


--
-- Name: reference_ranges id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reference_ranges ALTER COLUMN id SET DEFAULT nextval('public.reference_ranges_id_seq'::regclass);


--
-- Name: spiritual_sessions session_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.spiritual_sessions ALTER COLUMN session_id SET DEFAULT nextval('public.spiritual_sessions_session_id_seq'::regclass);


--
-- Name: stock_movement movement_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_movement ALTER COLUMN movement_id SET DEFAULT nextval('public.stock_movement_movement_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: admin admin_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin
    ADD CONSTRAINT admin_pkey PRIMARY KEY (user_id);


--
-- Name: admissions admissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admissions
    ADD CONSTRAINT admissions_pkey PRIMARY KEY (admission_id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: application_roles application_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.application_roles
    ADD CONSTRAINT application_roles_pkey PRIMARY KEY (role_id);


--
-- Name: application_roles application_roles_role_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.application_roles
    ADD CONSTRAINT application_roles_role_name_key UNIQUE (role_name);


--
-- Name: appointments appointments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_pkey PRIMARY KEY (id);


--
-- Name: audit_access_old audit_access_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_access_old
    ADD CONSTRAINT audit_access_pkey PRIMARY KEY (log_id);


--
-- Name: audit_access audit_access_pkey1; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_access
    ADD CONSTRAINT audit_access_pkey1 PRIMARY KEY (access_id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (log_id);


--
-- Name: audit_user_actions_old audit_user_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_user_actions_old
    ADD CONSTRAINT audit_user_actions_pkey PRIMARY KEY (action_id);


--
-- Name: audit_user_actions audit_user_actions_pkey1; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_user_actions
    ADD CONSTRAINT audit_user_actions_pkey1 PRIMARY KEY (action_id);


--
-- Name: caisse_item caisse_item_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.caisse_item
    ADD CONSTRAINT caisse_item_pkey PRIMARY KEY (item_id);


--
-- Name: caisse caisse_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.caisse
    ADD CONSTRAINT caisse_pkey PRIMARY KEY (transaction_id);


--
-- Name: caisse_retrait caisse_retrait_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.caisse_retrait
    ADD CONSTRAINT caisse_retrait_pkey PRIMARY KEY (retrait_id);


--
-- Name: consultation_spirituel consultation_spirituel_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.consultation_spirituel
    ADD CONSTRAINT consultation_spirituel_pkey PRIMARY KEY (consultation_id);


--
-- Name: discount_requests discount_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discount_requests
    ADD CONSTRAINT discount_requests_pkey PRIMARY KEY (id);


--
-- Name: doctor doctor_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doctor
    ADD CONSTRAINT doctor_pkey PRIMARY KEY (user_id);


--
-- Name: examens examens_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.examens
    ADD CONSTRAINT examens_code_key UNIQUE (code);


--
-- Name: examens examens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.examens
    ADD CONSTRAINT examens_pkey PRIMARY KEY (id);


--
-- Name: lab_result_details lab_result_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_result_details
    ADD CONSTRAINT lab_result_details_pkey PRIMARY KEY (detail_id);


--
-- Name: lab_results_audit lab_results_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_results_audit
    ADD CONSTRAINT lab_results_audit_pkey PRIMARY KEY (audit_id);


--
-- Name: lab_results lab_results_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_pkey PRIMARY KEY (result_id);


--
-- Name: laborantin laborantin_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.laborantin
    ADD CONSTRAINT laborantin_pkey PRIMARY KEY (user_id);


--
-- Name: medical_records medical_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medical_records
    ADD CONSTRAINT medical_records_pkey PRIMARY KEY (record_id);


--
-- Name: medical_specialties medical_specialties_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medical_specialties
    ADD CONSTRAINT medical_specialties_name_key UNIQUE (name);


--
-- Name: medical_specialties medical_specialties_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medical_specialties
    ADD CONSTRAINT medical_specialties_pkey PRIMARY KEY (specialty_id);


--
-- Name: motif_translations motif_translations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.motif_translations
    ADD CONSTRAINT motif_translations_pkey PRIMARY KEY (code);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: nurse nurse_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.nurse
    ADD CONSTRAINT nurse_pkey PRIMARY KEY (user_id);


--
-- Name: organization_config organization_config_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organization_config
    ADD CONSTRAINT organization_config_pkey PRIMARY KEY (id);


--
-- Name: paiement_echelonne paiement_echelonne_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paiement_echelonne
    ADD CONSTRAINT paiement_echelonne_pkey PRIMARY KEY (payment_id);


--
-- Name: parametres parametres_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.parametres
    ADD CONSTRAINT parametres_pkey PRIMARY KEY (id);


--
-- Name: patient_contacts patient_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patient_contacts
    ADD CONSTRAINT patient_contacts_pkey PRIMARY KEY (contact_id);


--
-- Name: patients patients_code_patient_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_code_patient_key UNIQUE (code_patient);


--
-- Name: patients patients_national_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_national_id_key UNIQUE (national_id);


--
-- Name: patients patients_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_pkey PRIMARY KEY (patient_id);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (permission_id);


--
-- Name: pharmacy pharmacy_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pharmacy
    ADD CONSTRAINT pharmacy_pkey PRIMARY KEY (medication_id);


--
-- Name: prayer_book_type prayer_book_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prayer_book_type
    ADD CONSTRAINT prayer_book_type_pkey PRIMARY KEY (type_code);


--
-- Name: prescriptions prescriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_pkey PRIMARY KEY (prescription_id);


--
-- Name: psych_evaluations psych_evaluations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.psych_evaluations
    ADD CONSTRAINT psych_evaluations_pkey PRIMARY KEY (eval_id);


--
-- Name: reference_ranges reference_ranges_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reference_ranges
    ADD CONSTRAINT reference_ranges_pkey PRIMARY KEY (id);


--
-- Name: role_permissions role_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (role_id, permission_id);


--
-- Name: secretaire secretaire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.secretaire
    ADD CONSTRAINT secretaire_pkey PRIMARY KEY (user_id);


--
-- Name: spiritual_attendance spiritual_attendance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.spiritual_attendance
    ADD CONSTRAINT spiritual_attendance_pkey PRIMARY KEY (session_id, admission_id);


--
-- Name: spiritual_sessions spiritual_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.spiritual_sessions
    ADD CONSTRAINT spiritual_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: stock_movement stock_movement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_movement
    ADD CONSTRAINT stock_movement_pkey PRIMARY KEY (movement_id);


--
-- Name: toxico_dossiers toxico_dossiers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.toxico_dossiers
    ADD CONSTRAINT toxico_dossiers_pkey PRIMARY KEY (id);


--
-- Name: toxico_evaluations toxico_evaluations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.toxico_evaluations
    ADD CONSTRAINT toxico_evaluations_pkey PRIMARY KEY (id);


--
-- Name: toxico_phase_history toxico_phase_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.toxico_phase_history
    ADD CONSTRAINT toxico_phase_history_pkey PRIMARY KEY (id);


--
-- Name: toxico_dossiers uq_toxico_patient; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.toxico_dossiers
    ADD CONSTRAINT uq_toxico_patient UNIQUE (patient_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: appointments_uuid_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX appointments_uuid_key ON public.appointments USING btree (uuid);


--
-- Name: caisse_retrait_uuid_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX caisse_retrait_uuid_key ON public.caisse_retrait USING btree (uuid);


--
-- Name: caisse_uuid_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX caisse_uuid_key ON public.caisse USING btree (uuid);


--
-- Name: idx_admissions_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_admissions_active ON public.admissions USING btree (status) WHERE ((status)::text = 'ACTIVE'::text);


--
-- Name: idx_appointments_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_appointments_date ON public.appointments USING btree (appointment_date);


--
-- Name: idx_caisse_payment_method; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_caisse_payment_method ON public.caisse USING btree (payment_method);


--
-- Name: idx_caisse_retrait_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_caisse_retrait_category ON public.caisse_retrait USING btree (category);


--
-- Name: idx_caisse_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_caisse_status ON public.caisse USING btree (status);


--
-- Name: idx_code_lab_patient; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_code_lab_patient ON public.lab_results USING btree (code_lab_patient);


--
-- Name: idx_lab_details_parametre; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_lab_details_parametre ON public.lab_result_details USING btree (parametre_id);


--
-- Name: idx_lab_result_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_lab_result_code ON public.lab_results USING btree (code_lab_patient);


--
-- Name: idx_lab_results_batch_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_lab_results_batch_id ON public.lab_results USING btree (batch_id);


--
-- Name: idx_lab_results_patient_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_lab_results_patient_date ON public.lab_results USING btree (patient_id, test_date DESC);


--
-- Name: idx_medical_records_motif_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_medical_records_motif_code ON public.medical_records USING btree (motif_code);


--
-- Name: idx_medical_records_patient_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_medical_records_patient_date ON public.medical_records USING btree (patient_id, consultation_date DESC);


--
-- Name: idx_paiement_trans_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paiement_trans_id ON public.paiement_echelonne USING btree (transaction_id);


--
-- Name: idx_parametres_examen; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_parametres_examen ON public.parametres USING btree (examen_id);


--
-- Name: idx_patients_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_patients_active ON public.patients USING btree (is_deleted) WHERE (is_deleted = false);


--
-- Name: idx_patients_clinical; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_patients_clinical ON public.patients USING btree (is_clinical) WHERE (is_clinical = true);


--
-- Name: idx_patients_code_search; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_patients_code_search ON public.patients USING btree (code_patient);


--
-- Name: idx_patients_full_name_lower; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_patients_full_name_lower ON public.patients USING btree (lower((((last_name)::text || ' '::text) || (first_name)::text)));


--
-- Name: idx_patients_global_search; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_patients_global_search ON public.patients USING btree (code_patient, last_name, first_name) WHERE (is_deleted = false);


--
-- Name: idx_patients_name_rev_search; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_patients_name_rev_search ON public.patients USING btree (lower((((first_name)::text || ' '::text) || (last_name)::text)));


--
-- Name: idx_patients_spiritual; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_patients_spiritual ON public.patients USING btree (is_spiritual) WHERE (is_spiritual = true);


--
-- Name: idx_patients_toxico; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_patients_toxico ON public.patients USING btree (is_toxicology) WHERE (is_toxicology = true);


--
-- Name: idx_pharmacy_drug_name_lower; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pharmacy_drug_name_lower ON public.pharmacy USING btree (lower((drug_name)::text));


--
-- Name: idx_pharmacy_stock_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pharmacy_stock_status ON public.pharmacy USING btree (stock_status);


--
-- Name: idx_prescriptions_patient_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prescriptions_patient_status ON public.prescriptions USING btree (patient_id, status);


--
-- Name: idx_reference_ranges_parametre; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_reference_ranges_parametre ON public.reference_ranges USING btree (parametre_id);


--
-- Name: idx_toxico_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_toxico_active ON public.toxico_dossiers USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_toxico_psy; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_toxico_psy ON public.toxico_dossiers USING btree (psychologist_id);


--
-- Name: ix_discount_requests_requested_to_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_discount_requests_requested_to_status ON public.discount_requests USING btree (requested_to, status);


--
-- Name: ix_discount_requests_transaction; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_discount_requests_transaction ON public.discount_requests USING btree (transaction_id);


--
-- Name: ix_lab_results_batch_uuid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_lab_results_batch_uuid ON public.lab_results USING btree (batch_uuid);


--
-- Name: ix_lab_results_uuid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_lab_results_uuid ON public.lab_results USING btree (uuid);


--
-- Name: ix_notifications_recipient_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notifications_recipient_status ON public.notifications USING btree (recipient_user_id, status);


--
-- Name: medical_records_uuid_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX medical_records_uuid_key ON public.medical_records USING btree (uuid);


--
-- Name: paiement_echelonne_uuid_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX paiement_echelonne_uuid_key ON public.paiement_echelonne USING btree (uuid);


--
-- Name: patients_uuid_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX patients_uuid_key ON public.patients USING btree (uuid);


--
-- Name: caisse trg_caisse_protect_cancelled; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_caisse_protect_cancelled BEFORE UPDATE ON public.caisse FOR EACH ROW EXECUTE FUNCTION public.fn_caisse_protect_cancelled();


--
-- Name: users trg_default_specialty; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_default_specialty BEFORE INSERT ON public.users FOR EACH ROW EXECUTE FUNCTION public.set_default_specialty();


--
-- Name: lab_results trg_fix_lab_names_safe; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_fix_lab_names_safe BEFORE INSERT OR UPDATE ON public.lab_results FOR EACH ROW EXECUTE FUNCTION public.fix_lab_names();


--
-- Name: patients trg_patient_tracking; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_patient_tracking BEFORE INSERT OR UPDATE ON public.patients FOR EACH ROW EXECUTE FUNCTION public.track_patient_changes();


--
-- Name: prescriptions trg_prescription_names; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_prescription_names BEFORE INSERT OR UPDATE ON public.prescriptions FOR EACH ROW EXECUTE FUNCTION public.update_prescribed_names();


--
-- Name: appointments trg_refresh_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_refresh_updated_at BEFORE UPDATE ON public.appointments FOR EACH ROW EXECUTE FUNCTION public.refresh_updated_at();


--
-- Name: consultation_spirituel trg_spiritual_names; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_spiritual_names BEFORE INSERT OR UPDATE ON public.consultation_spirituel FOR EACH ROW EXECUTE FUNCTION public.update_user_names_cs();


--
-- Name: pharmacy trg_update_pharmacy_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_update_pharmacy_updated_at BEFORE UPDATE ON public.pharmacy FOR EACH ROW EXECUTE FUNCTION public.update_pharmacy_updated_at();


--
-- Name: users trg_user_after_insert; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_user_after_insert AFTER INSERT ON public.users FOR EACH ROW EXECUTE FUNCTION public.create_metier_profile();


--
-- Name: users trg_user_after_update_role; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_user_after_update_role AFTER UPDATE OF role_id ON public.users FOR EACH ROW WHEN ((old.role_id IS DISTINCT FROM new.role_id)) EXECUTE FUNCTION public.create_metier_profile();


--
-- Name: admin admin_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin
    ADD CONSTRAINT admin_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: admissions admissions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admissions
    ADD CONSTRAINT admissions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: admissions admissions_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admissions
    ADD CONSTRAINT admissions_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: appointments appointments_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: appointments appointments_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: audit_access audit_access_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_access
    ADD CONSTRAINT audit_access_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: audit_user_actions audit_user_actions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_user_actions
    ADD CONSTRAINT audit_user_actions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: caisse caisse_cancelled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.caisse
    ADD CONSTRAINT caisse_cancelled_by_fkey FOREIGN KEY (cancelled_by) REFERENCES public.users(user_id);


--
-- Name: caisse caisse_handled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.caisse
    ADD CONSTRAINT caisse_handled_by_fkey FOREIGN KEY (handled_by) REFERENCES public.users(user_id);


--
-- Name: caisse_item caisse_item_transaction_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.caisse_item
    ADD CONSTRAINT caisse_item_transaction_fkey FOREIGN KEY (transaction_id) REFERENCES public.caisse(transaction_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: caisse caisse_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.caisse
    ADD CONSTRAINT caisse_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: consultation_spirituel consultation_spirituel_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.consultation_spirituel
    ADD CONSTRAINT consultation_spirituel_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: consultation_spirituel consultation_spirituel_mp_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.consultation_spirituel
    ADD CONSTRAINT consultation_spirituel_mp_type_fkey FOREIGN KEY (mp_type) REFERENCES public.prayer_book_type(type_code) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: consultation_spirituel consultation_spirituel_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.consultation_spirituel
    ADD CONSTRAINT consultation_spirituel_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: discount_requests discount_requests_decided_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discount_requests
    ADD CONSTRAINT discount_requests_decided_by_fkey FOREIGN KEY (decided_by) REFERENCES public.users(user_id);


--
-- Name: discount_requests discount_requests_requested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discount_requests
    ADD CONSTRAINT discount_requests_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES public.users(user_id);


--
-- Name: discount_requests discount_requests_requested_to_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discount_requests
    ADD CONSTRAINT discount_requests_requested_to_fkey FOREIGN KEY (requested_to) REFERENCES public.users(user_id);


--
-- Name: discount_requests discount_requests_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discount_requests
    ADD CONSTRAINT discount_requests_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.caisse(transaction_id);


--
-- Name: doctor doctor_specialty_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doctor
    ADD CONSTRAINT doctor_specialty_id_fkey FOREIGN KEY (specialty_id) REFERENCES public.medical_specialties(specialty_id);


--
-- Name: doctor doctor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doctor
    ADD CONSTRAINT doctor_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: spiritual_attendance fk_att_admission; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.spiritual_attendance
    ADD CONSTRAINT fk_att_admission FOREIGN KEY (admission_id) REFERENCES public.admissions(admission_id);


--
-- Name: spiritual_attendance fk_att_session; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.spiritual_attendance
    ADD CONSTRAINT fk_att_session FOREIGN KEY (session_id) REFERENCES public.spiritual_sessions(session_id);


--
-- Name: caisse_retrait fk_caisse_retrait_cancelled_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.caisse_retrait
    ADD CONSTRAINT fk_caisse_retrait_cancelled_by FOREIGN KEY (cancelled_by) REFERENCES public.users(user_id);


--
-- Name: patient_contacts fk_contact_patient; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patient_contacts
    ADD CONSTRAINT fk_contact_patient FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: toxico_evaluations fk_eval_creator; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.toxico_evaluations
    ADD CONSTRAINT fk_eval_creator FOREIGN KEY (created_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: toxico_evaluations fk_eval_dossier; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.toxico_evaluations
    ADD CONSTRAINT fk_eval_dossier FOREIGN KEY (dossier_id) REFERENCES public.toxico_dossiers(id) ON DELETE CASCADE;


--
-- Name: toxico_phase_history fk_history_dossier; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.toxico_phase_history
    ADD CONSTRAINT fk_history_dossier FOREIGN KEY (dossier_id) REFERENCES public.toxico_dossiers(id) ON DELETE CASCADE;


--
-- Name: lab_results fk_origin_prescription; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT fk_origin_prescription FOREIGN KEY (origin_prescription_id) REFERENCES public.prescriptions(prescription_id);


--
-- Name: paiement_echelonne fk_paiement_caisse; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paiement_echelonne
    ADD CONSTRAINT fk_paiement_caisse FOREIGN KEY (transaction_id) REFERENCES public.caisse(transaction_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: caisse_retrait fk_retrait_user; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.caisse_retrait
    ADD CONSTRAINT fk_retrait_user FOREIGN KEY (handled_by) REFERENCES public.users(user_id);


--
-- Name: stock_movement fk_stockmed_pharmacy; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_movement
    ADD CONSTRAINT fk_stockmed_pharmacy FOREIGN KEY (medication_id) REFERENCES public.pharmacy(medication_id) ON DELETE CASCADE;


--
-- Name: toxico_dossiers fk_toxico_patient; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.toxico_dossiers
    ADD CONSTRAINT fk_toxico_patient FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: toxico_dossiers fk_toxico_psychologist; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.toxico_dossiers
    ADD CONSTRAINT fk_toxico_psychologist FOREIGN KEY (psychologist_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: users fk_user_specialty; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_user_specialty FOREIGN KEY (specialty_id) REFERENCES public.medical_specialties(specialty_id);


--
-- Name: users fk_users_role_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_users_role_id FOREIGN KEY (role_id) REFERENCES public.application_roles(role_id) ON DELETE SET NULL;


--
-- Name: lab_result_details lab_result_details_parametre_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_result_details
    ADD CONSTRAINT lab_result_details_parametre_id_fkey FOREIGN KEY (parametre_id) REFERENCES public.parametres(id) ON DELETE RESTRICT;


--
-- Name: lab_result_details lab_result_details_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_result_details
    ADD CONSTRAINT lab_result_details_result_id_fkey FOREIGN KEY (result_id) REFERENCES public.lab_results(result_id) ON DELETE CASCADE;


--
-- Name: lab_results_audit lab_results_audit_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_results_audit
    ADD CONSTRAINT lab_results_audit_result_id_fkey FOREIGN KEY (result_id) REFERENCES public.lab_results(result_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: lab_results lab_results_examen_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_examen_id_fkey FOREIGN KEY (examen_id) REFERENCES public.examens(id);


--
-- Name: lab_results lab_results_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: lab_results lab_results_prescribed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_prescribed_by_fkey FOREIGN KEY (prescribed_by) REFERENCES public.users(user_id);


--
-- Name: lab_results lab_results_technician_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_technician_id_fkey FOREIGN KEY (technician_id) REFERENCES public.users(user_id);


--
-- Name: laborantin laborantin_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.laborantin
    ADD CONSTRAINT laborantin_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: medical_records medical_records_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medical_records
    ADD CONSTRAINT medical_records_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.appointments(id) ON DELETE SET NULL;


--
-- Name: medical_records medical_records_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medical_records
    ADD CONSTRAINT medical_records_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: medical_records medical_records_last_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medical_records
    ADD CONSTRAINT medical_records_last_updated_by_fkey FOREIGN KEY (last_updated_by) REFERENCES public.users(user_id);


--
-- Name: medical_records medical_records_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medical_records
    ADD CONSTRAINT medical_records_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: notifications notifications_recipient_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_recipient_user_id_fkey FOREIGN KEY (recipient_user_id) REFERENCES public.users(user_id);


--
-- Name: nurse nurse_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.nurse
    ADD CONSTRAINT nurse_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: parametres parametres_examen_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.parametres
    ADD CONSTRAINT parametres_examen_id_fkey FOREIGN KEY (examen_id) REFERENCES public.examens(id) ON DELETE CASCADE;


--
-- Name: patients patients_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: patients patients_deleted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_deleted_by_fkey FOREIGN KEY (deleted_by) REFERENCES public.users(user_id);


--
-- Name: patients patients_last_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_last_updated_by_fkey FOREIGN KEY (last_updated_by) REFERENCES public.users(user_id);


--
-- Name: pharmacy pharmacy_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pharmacy
    ADD CONSTRAINT pharmacy_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: pharmacy pharmacy_prescribed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pharmacy
    ADD CONSTRAINT pharmacy_prescribed_by_fkey FOREIGN KEY (prescribed_by) REFERENCES public.users(user_id);


--
-- Name: prescriptions prescriptions_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: prescriptions prescriptions_prescribed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_prescribed_by_fkey FOREIGN KEY (prescribed_by) REFERENCES public.users(user_id);


--
-- Name: psych_evaluations psych_evaluations_admission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.psych_evaluations
    ADD CONSTRAINT psych_evaluations_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admissions(admission_id) ON DELETE CASCADE;


--
-- Name: psych_evaluations psych_evaluations_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.psych_evaluations
    ADD CONSTRAINT psych_evaluations_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.users(user_id);


--
-- Name: reference_ranges reference_ranges_parametre_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reference_ranges
    ADD CONSTRAINT reference_ranges_parametre_id_fkey FOREIGN KEY (parametre_id) REFERENCES public.parametres(id) ON DELETE CASCADE;


--
-- Name: role_permissions role_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(permission_id);


--
-- Name: role_permissions role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.application_roles(role_id);


--
-- Name: secretaire secretaire_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.secretaire
    ADD CONSTRAINT secretaire_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: patients medical_policy; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY medical_policy ON public.patients TO app_medical USING (true);


--
-- Name: powersync; Type: PUBLICATION; Schema: -; Owner: postgres
--

CREATE PUBLICATION powersync FOR ALL TABLES WITH (publish = 'insert, update, delete, truncate');


ALTER PUBLICATION powersync OWNER TO postgres;

--
-- Name: FUNCTION update_user_names_cs(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.update_user_names_cs() TO app_medical;


--
-- Name: TABLE audit_access_old; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.audit_access_old TO app_admin;


--
-- Name: TABLE audit_user_actions_old; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.audit_user_actions_old TO app_admin;


--
-- Name: TABLE caisse; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.caisse TO app_secretaire;


--
-- Name: TABLE caisse_item; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.caisse_item TO app_secretaire;


--
-- Name: SEQUENCE consultation_spirituel_consultation_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.consultation_spirituel_consultation_id_seq TO app_medical;


--
-- Name: TABLE lab_results; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.lab_results TO app_laborantin;


--
-- Name: COLUMN lab_results.status; Type: ACL; Schema: public; Owner: postgres
--

GRANT UPDATE(status) ON TABLE public.lab_results TO app_laborantin;


--
-- Name: COLUMN lab_results.note; Type: ACL; Schema: public; Owner: postgres
--

GRANT UPDATE(note) ON TABLE public.lab_results TO app_laborantin;


--
-- Name: SEQUENCE lab_results_result_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.lab_results_result_id_seq TO app_medical;


--
-- Name: TABLE medical_records; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.medical_records TO app_medical;


--
-- Name: TABLE patients; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.patients TO app_secretaire;
GRANT SELECT,INSERT,UPDATE ON TABLE public.patients TO app_medical;
GRANT SELECT ON TABLE public.patients TO app_admin;


--
-- Name: SEQUENCE patients_patient_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.patients_patient_id_seq TO app_medical;


--
-- Name: TABLE pharmacy; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.pharmacy TO app_secretaire;


--
-- Name: TABLE prescriptions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.prescriptions TO app_medical;


--
-- Name: SEQUENCE prescriptions_prescription_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.prescriptions_prescription_id_seq TO app_medical;


--
-- Name: TABLE role_permissions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.role_permissions TO app_admin;


--
-- Name: TABLE stock_movement; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.stock_movement TO app_secretaire;


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.users TO app_admin;


--
-- Name: SEQUENCE users_user_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.users_user_id_seq TO app_medical;


--
-- PostgreSQL database dump complete
--

